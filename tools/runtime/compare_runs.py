"""
Compare two VDM runtime run directories.

This is a smoke/parity aid, not a model-quality validator. It compares emitted
runtime artifacts while ignoring external clock fields by default.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

try:
    from vdm_rt.io.logging.jsonl_reader import iter_jsonl_rows
except ModuleNotFoundError:
    for parent in Path(__file__).resolve().parents:
        if (parent / "io" / "logging" / "jsonl_reader.py").exists():
            sys.path.insert(0, str(parent.parent))
            break
    from vdm_rt.io.logging.jsonl_reader import iter_jsonl_rows


DEFAULT_STREAMS = ("events.jsonl.zst", "motor_traces.jsonl.zst")
DEFAULT_IGNORE_FIELDS = frozenset({"wall_time_s", "ts", "run_elapsed_s"})

RecordKey = Tuple[Any, ...]


@dataclass(frozen=True)
class FieldDiff:
    record_key: RecordKey
    field: str
    baseline: Any
    candidate: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_key": list(self.record_key),
            "field": self.field,
            "baseline": self.baseline,
            "candidate": self.candidate,
        }


@dataclass
class StreamComparison:
    stream: str
    baseline_rows: int
    candidate_rows: int
    matched_records: int
    baseline_only_records: List[RecordKey] = field(default_factory=list)
    candidate_only_records: List[RecordKey] = field(default_factory=list)
    added_fields: List[str] = field(default_factory=list)
    removed_fields: List[str] = field(default_factory=list)
    common_field_diff_count: int = 0
    first_diffs: List[FieldDiff] = field(default_factory=list)
    baseline_tick_range: Tuple[int, int] | None = None
    candidate_tick_range: Tuple[int, int] | None = None
    missing_baseline_stream: bool = False
    missing_candidate_stream: bool = False

    def has_unexpected_changes(
        self,
        *,
        allowed_added_fields: Iterable[str] = (),
        allowed_removed_fields: Iterable[str] = (),
    ) -> bool:
        allowed_added = set(allowed_added_fields)
        allowed_removed = set(allowed_removed_fields)
        if self.baseline_only_records or self.candidate_only_records:
            return True
        if set(self.added_fields) - allowed_added:
            return True
        if set(self.removed_fields) - allowed_removed:
            return True
        return self.common_field_diff_count > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stream": self.stream,
            "baseline_rows": self.baseline_rows,
            "candidate_rows": self.candidate_rows,
            "matched_records": self.matched_records,
            "baseline_only_records": [list(k) for k in self.baseline_only_records],
            "candidate_only_records": [list(k) for k in self.candidate_only_records],
            "added_fields": self.added_fields,
            "removed_fields": self.removed_fields,
            "common_field_diff_count": self.common_field_diff_count,
            "first_diffs": [diff.to_dict() for diff in self.first_diffs],
            "baseline_tick_range": list(self.baseline_tick_range) if self.baseline_tick_range else None,
            "candidate_tick_range": list(self.candidate_tick_range) if self.candidate_tick_range else None,
            "missing_baseline_stream": self.missing_baseline_stream,
            "missing_candidate_stream": self.missing_candidate_stream,
        }


@dataclass
class RunComparison:
    baseline_dir: str
    candidate_dir: str
    streams: List[StreamComparison]

    def has_unexpected_changes(
        self,
        *,
        allowed_added_fields: Iterable[str] = (),
        allowed_removed_fields: Iterable[str] = (),
    ) -> bool:
        return any(
            stream.has_unexpected_changes(
                allowed_added_fields=allowed_added_fields,
                allowed_removed_fields=allowed_removed_fields,
            )
            for stream in self.streams
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_dir": self.baseline_dir,
            "candidate_dir": self.candidate_dir,
            "streams": [stream.to_dict() for stream in self.streams],
        }


def read_jsonl_zst(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return list(iter_jsonl_rows(path))


def _base_record_key(stream: str, row: Dict[str, Any], index: int) -> RecordKey:
    if row.get("msg") == "tick" and "tick" in row:
        try:
            return ("tick", int(row["tick"]))
        except Exception:
            pass
    if "tick" in row:
        try:
            tick = int(row["tick"])
        except Exception:
            tick = row["tick"]
        kind = row.get("trace_kind", row.get("msg", "row"))
        return ("tick-kind", tick, str(kind))
    return ("row", stream, index)


def keyed_rows(stream: str, rows: Sequence[Dict[str, Any]]) -> Dict[RecordKey, Dict[str, Any]]:
    counts: Dict[RecordKey, int] = {}
    keyed: Dict[RecordKey, Dict[str, Any]] = {}
    for index, row in enumerate(rows):
        base = _base_record_key(stream, row, index)
        ordinal = counts.get(base, 0)
        counts[base] = ordinal + 1
        keyed[base + (ordinal,)] = row
    return keyed


def tick_range(rows: Sequence[Dict[str, Any]]) -> Tuple[int, int] | None:
    ticks: List[int] = []
    for row in rows:
        if "tick" not in row:
            continue
        try:
            ticks.append(int(row["tick"]))
        except Exception:
            continue
    if not ticks:
        return None
    return (min(ticks), max(ticks))


def _values_equal(left: Any, right: Any, *, abs_tol: float) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right
    if isinstance(left, (int, float)) or isinstance(right, (int, float)):
        try:
            return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=float(abs_tol))
        except Exception:
            return left == right
    return left == right


def compare_rows(
    stream: str,
    baseline_rows: Sequence[Dict[str, Any]],
    candidate_rows: Sequence[Dict[str, Any]],
    *,
    ignore_fields: Iterable[str] = DEFAULT_IGNORE_FIELDS,
    abs_tol: float = 1e-12,
    max_diffs: int = 20,
    missing_baseline_stream: bool = False,
    missing_candidate_stream: bool = False,
) -> StreamComparison:
    ignored = set(ignore_fields)
    baseline_keyed = keyed_rows(stream, baseline_rows)
    candidate_keyed = keyed_rows(stream, candidate_rows)
    baseline_keys = set(baseline_keyed)
    candidate_keys = set(candidate_keyed)
    common_keys = sorted(baseline_keys & candidate_keys)
    added_fields: set[str] = set()
    removed_fields: set[str] = set()
    diff_count = 0
    first_diffs: List[FieldDiff] = []

    for key in common_keys:
        baseline = {k: v for k, v in baseline_keyed[key].items() if k not in ignored}
        candidate = {k: v for k, v in candidate_keyed[key].items() if k not in ignored}
        baseline_fields = set(baseline)
        candidate_fields = set(candidate)
        added_fields.update(candidate_fields - baseline_fields)
        removed_fields.update(baseline_fields - candidate_fields)
        for field_name in sorted(baseline_fields & candidate_fields):
            left = baseline[field_name]
            right = candidate[field_name]
            if _values_equal(left, right, abs_tol=abs_tol):
                continue
            diff_count += 1
            if len(first_diffs) < int(max(0, max_diffs)):
                first_diffs.append(
                    FieldDiff(
                        record_key=key,
                        field=field_name,
                        baseline=left,
                        candidate=right,
                    )
                )

    return StreamComparison(
        stream=stream,
        baseline_rows=len(baseline_rows),
        candidate_rows=len(candidate_rows),
        matched_records=len(common_keys),
        baseline_only_records=sorted(baseline_keys - candidate_keys),
        candidate_only_records=sorted(candidate_keys - baseline_keys),
        added_fields=sorted(added_fields),
        removed_fields=sorted(removed_fields),
        common_field_diff_count=diff_count,
        first_diffs=first_diffs,
        baseline_tick_range=tick_range(baseline_rows),
        candidate_tick_range=tick_range(candidate_rows),
        missing_baseline_stream=missing_baseline_stream,
        missing_candidate_stream=missing_candidate_stream,
    )


def compare_run_dirs(
    baseline_dir: Path | str,
    candidate_dir: Path | str,
    *,
    streams: Sequence[str] = DEFAULT_STREAMS,
    ignore_fields: Iterable[str] = DEFAULT_IGNORE_FIELDS,
    abs_tol: float = 1e-12,
    max_diffs: int = 20,
) -> RunComparison:
    baseline = Path(baseline_dir)
    candidate = Path(candidate_dir)
    comparisons: List[StreamComparison] = []
    for stream in streams:
        baseline_path = baseline / stream
        candidate_path = candidate / stream
        baseline_rows = read_jsonl_zst(baseline_path)
        candidate_rows = read_jsonl_zst(candidate_path)
        comparisons.append(
            compare_rows(
                stream,
                baseline_rows,
                candidate_rows,
                ignore_fields=ignore_fields,
                abs_tol=abs_tol,
                max_diffs=max_diffs,
                missing_baseline_stream=not baseline_path.exists(),
                missing_candidate_stream=not candidate_path.exists(),
            )
        )
    return RunComparison(
        baseline_dir=str(baseline),
        candidate_dir=str(candidate),
        streams=comparisons,
    )


def format_text_report(
    comparison: RunComparison,
    *,
    allowed_added_fields: Iterable[str] = (),
    allowed_removed_fields: Iterable[str] = (),
) -> str:
    lines = [
        f"baseline: {comparison.baseline_dir}",
        f"candidate: {comparison.candidate_dir}",
    ]
    for stream in comparison.streams:
        unexpected = stream.has_unexpected_changes(
            allowed_added_fields=allowed_added_fields,
            allowed_removed_fields=allowed_removed_fields,
        )
        lines.append("")
        lines.append(f"[{stream.stream}] {'DIFF' if unexpected else 'OK'}")
        lines.append(f"rows: baseline={stream.baseline_rows} candidate={stream.candidate_rows}")
        lines.append(f"matched_records: {stream.matched_records}")
        lines.append(
            f"tick_range: baseline={stream.baseline_tick_range} candidate={stream.candidate_tick_range}"
        )
        if stream.baseline_only_records:
            lines.append(f"baseline_only_records: {len(stream.baseline_only_records)}")
        if stream.candidate_only_records:
            lines.append(f"candidate_only_records: {len(stream.candidate_only_records)}")
        if stream.added_fields:
            lines.append(f"added_fields: {', '.join(stream.added_fields)}")
        if stream.removed_fields:
            lines.append(f"removed_fields: {', '.join(stream.removed_fields)}")
        lines.append(f"common_field_diff_count: {stream.common_field_diff_count}")
        for diff in stream.first_diffs:
            lines.append(
                "diff "
                f"{diff.record_key} {diff.field}: "
                f"baseline={diff.baseline!r} candidate={diff.candidate!r}"
            )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare VDM runtime run artifacts.")
    parser.add_argument("baseline_dir", type=Path)
    parser.add_argument("candidate_dir", type=Path)
    parser.add_argument("--stream", action="append", dest="streams", default=None)
    parser.add_argument("--ignore-field", action="append", default=[])
    parser.add_argument("--allow-added-field", action="append", default=[])
    parser.add_argument("--allow-removed-field", action="append", default=[])
    parser.add_argument("--abs-tol", type=float, default=1e-12)
    parser.add_argument("--max-diffs", type=int, default=20)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--no-fail", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ignore_fields = set(DEFAULT_IGNORE_FIELDS)
    ignore_fields.update(args.ignore_field or [])
    comparison = compare_run_dirs(
        args.baseline_dir,
        args.candidate_dir,
        streams=tuple(args.streams or DEFAULT_STREAMS),
        ignore_fields=ignore_fields,
        abs_tol=float(args.abs_tol),
        max_diffs=int(args.max_diffs),
    )
    if args.json_output:
        print(json.dumps(comparison.to_dict(), indent=2, sort_keys=True))
    else:
        print(
            format_text_report(
                comparison,
                allowed_added_fields=args.allow_added_field,
                allowed_removed_fields=args.allow_removed_field,
            )
        )
    if args.no_fail:
        return 0
    return 1 if comparison.has_unexpected_changes(
        allowed_added_fields=args.allow_added_field,
        allowed_removed_fields=args.allow_removed_field,
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())
