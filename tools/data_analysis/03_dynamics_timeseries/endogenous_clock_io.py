"""Input/output helpers for endogenous-clock evidence regeneration."""

from __future__ import annotations

import csv
import gzip
import io
import json
import math
import zipfile
from pathlib import Path
from typing import Any, Iterable, Iterator


SIE_DIR_NAME = "sie_v2"
DEFAULT_PREFIX = "F8_02"
DEFAULT_EPOCH_BOUNDARIES = (10500, 11600)


def float_value(row: dict[str, Any], key: str, default: float = math.nan) -> float:
    value = row.get(key)
    if value in ("", None, "nan", "None", "null"):
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def int_value(row: dict[str, Any], key: str, default: int | None = None) -> int | None:
    value = row.get(key)
    if value in ("", None, "nan", "None", "null"):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def time_value(row: dict[str, Any]) -> float:
    for key in ("ts", "wall_time_s", "run_elapsed_s"):
        value = float_value(row, key)
        if not math.isnan(value):
            return value
    return math.nan


def tick_value(row: dict[str, Any]) -> int | None:
    for key in ("tick", "t", "evt_t"):
        value = int_value(row, key)
        if value is not None:
            return value
    return None


def normalize_tick_row(row: dict[str, Any]) -> dict[str, Any] | None:
    if row.get("msg") not in (None, "", "tick"):
        return None
    if isinstance(row.get("extra"), dict):
        merged = dict(row)
        merged.update(row["extra"])
        row = merged
    tick = tick_value(row)
    if tick is None:
        return None
    out = dict(row)
    out["t"] = tick
    out["tick"] = tick
    return out


def _open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    if path.suffix == ".zst":
        import zstandard as zstd

        fh = path.open("rb")
        dctx = zstd.ZstdDecompressor()
        try:
            reader = dctx.stream_reader(fh, read_across_frames=True)
        except TypeError:
            reader = dctx.stream_reader(fh)
        return io.TextIOWrapper(reader, encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with _open_text(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                row = normalize_tick_row(obj)
                if row is not None:
                    yield row


def _iter_csv(path: Path) -> Iterator[dict[str, Any]]:
    with _open_text(path) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            normalized = normalize_tick_row(dict(row))
            if normalized is not None:
                yield normalized


def _iter_zip(path: Path) -> Iterator[dict[str, Any]]:
    with zipfile.ZipFile(path) as zf:
        names = sorted(zf.namelist())
        for name in names:
            lower = name.lower()
            if lower.endswith(".jsonl"):
                with zf.open(name) as raw:
                    text = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
                    for line in text:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(obj, dict):
                            row = normalize_tick_row(obj)
                            if row is not None:
                                yield row
            elif lower.endswith(".csv"):
                with zf.open(name) as raw:
                    text = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
                    for row in csv.DictReader(text):
                        normalized = normalize_tick_row(dict(row))
                        if normalized is not None:
                            yield normalized


def _input_file(path: Path) -> Path:
    if path.is_dir():
        for name in (
            "events.jsonl.zst",
            "events.jsonl",
            "tick_table_full.csv.gz",
            "tick_table_full.csv",
        ):
            candidate = path / name
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"No supported tick artifact found under {path}")
    return path


def load_tick_rows(source: Path) -> list[dict[str, Any]]:
    path = _input_file(source)
    lower = path.name.lower()
    if lower.endswith(".zip"):
        rows = list(_iter_zip(path))
    elif lower.endswith(".jsonl") or lower.endswith(".jsonl.zst"):
        rows = list(_iter_jsonl(path))
    elif lower.endswith(".csv") or lower.endswith(".csv.gz"):
        rows = list(_iter_csv(path))
    else:
        raise ValueError(f"Unsupported input type: {path}")
    rows.sort(key=lambda row: int(row["t"]))
    deduped: dict[int, dict[str, Any]] = {}
    for row in rows:
        deduped[int(row["t"])] = row
    return [deduped[t] for t in sorted(deduped)]


def _format_cell(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return repr(float(value))
    return value


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _format_cell(row.get(key, "")) for key in fieldnames})
