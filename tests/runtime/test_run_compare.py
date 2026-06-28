from __future__ import annotations

import json
from pathlib import Path

import zstandard as zstd

from tools.runtime.compare_runs import compare_run_dirs, main


def _write_zst_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    compressor = zstd.ZstdCompressor(level=1)
    with path.open("ab") as fh:
        for row in rows:
            payload = (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
            fh.write(compressor.compress(payload))


def test_compare_run_dirs_ignores_clock_fields(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _write_zst_jsonl(
        baseline / "events.jsonl.zst",
        [
            {
                "msg": "tick",
                "tick": 1,
                "wall_time_s": 10.0,
                "run_elapsed_s": 0.1,
                "sie_gate": 0.5,
            }
        ],
    )
    _write_zst_jsonl(
        candidate / "events.jsonl.zst",
        [
            {
                "msg": "tick",
                "tick": 1,
                "wall_time_s": 20.0,
                "run_elapsed_s": 0.2,
                "sie_gate": 0.5,
            }
        ],
    )

    comparison = compare_run_dirs(baseline, candidate, streams=("events.jsonl.zst",))

    stream = comparison.streams[0]
    assert stream.matched_records == 1
    assert stream.common_field_diff_count == 0
    assert not comparison.has_unexpected_changes()


def test_compare_run_dirs_reports_common_field_diffs(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _write_zst_jsonl(
        baseline / "events.jsonl.zst",
        [{"msg": "tick", "tick": 1, "sie_gate": 0.5}],
    )
    _write_zst_jsonl(
        candidate / "events.jsonl.zst",
        [{"msg": "tick", "tick": 1, "sie_gate": 0.7}],
    )

    comparison = compare_run_dirs(baseline, candidate, streams=("events.jsonl.zst",))

    stream = comparison.streams[0]
    assert stream.common_field_diff_count == 1
    assert stream.first_diffs[0].field == "sie_gate"
    assert comparison.has_unexpected_changes()


def test_compare_run_dirs_allows_expected_added_fields(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _write_zst_jsonl(
        baseline / "events.jsonl.zst",
        [{"msg": "tick", "tick": 1, "sie_gate": 0.5}],
    )
    _write_zst_jsonl(
        candidate / "events.jsonl.zst",
        [
            {
                "msg": "tick",
                "tick": 1,
                "sie_gate": 0.5,
                "sie_runtime_valence_01": 0.4,
            }
        ],
    )

    comparison = compare_run_dirs(baseline, candidate, streams=("events.jsonl.zst",))

    assert comparison.streams[0].added_fields == ["sie_runtime_valence_01"]
    assert comparison.has_unexpected_changes()
    assert not comparison.has_unexpected_changes(
        allowed_added_fields={"sie_runtime_valence_01"}
    )


def test_compare_run_dirs_keys_repeated_motor_trace_rows_by_tick_kind_and_ordinal(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    rows = [
        {"tick": 2, "trace_kind": "efferent_dynamics", "obs_count": 1},
        {"tick": 2, "trace_kind": "efferent_dynamics", "obs_count": 2},
    ]
    _write_zst_jsonl(baseline / "motor_traces.jsonl.zst", rows)
    _write_zst_jsonl(candidate / "motor_traces.jsonl.zst", rows)

    comparison = compare_run_dirs(
        baseline,
        candidate,
        streams=("motor_traces.jsonl.zst",),
    )

    assert comparison.streams[0].matched_records == 2
    assert not comparison.has_unexpected_changes()


def test_main_returns_nonzero_on_unexpected_diff(tmp_path: Path, capsys) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _write_zst_jsonl(
        baseline / "events.jsonl.zst",
        [{"msg": "tick", "tick": 1, "sie_gate": 0.5}],
    )
    _write_zst_jsonl(
        candidate / "events.jsonl.zst",
        [{"msg": "tick", "tick": 1, "sie_gate": 0.7}],
    )

    code = main(
        [
            str(baseline),
            str(candidate),
            "--stream",
            "events.jsonl.zst",
            "--max-diffs",
            "1",
        ]
    )

    assert code == 1
    assert "common_field_diff_count: 1" in capsys.readouterr().out
