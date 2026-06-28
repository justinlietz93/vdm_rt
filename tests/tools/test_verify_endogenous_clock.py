from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import zstandard as zstd


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "data_analysis" / "03_dynamics_timeseries" / "verify_endogenous_clock.py"


def _write_zst_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    compressor = zstd.ZstdCompressor(level=1)
    with path.open("ab") as fh:
        for row in rows:
            payload = (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
            fh.write(compressor.compress(payload))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_verify_endogenous_clock_generates_duration_and_sie_tables(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    rows = []
    ts = 1000.0
    for tick in range(80):
        phase = 2.0 * math.pi * tick / 10.0
        valence = 0.5 + 0.1 * math.sin(phase)
        rows.append(
            {
                "msg": "tick",
                "tick": tick,
                "t": tick,
                "ts": ts,
                "wall_time_s": ts,
                "sie_v2_valence_01": valence,
                "omega_mean": valence * 2.0,
                "a_mean": -valence,
                "connectome_entropy": 1.0 + 0.01 * tick,
                "active_edges": 100 + tick,
                "b1_z": math.sin(phase / 2.0),
            }
        )
        ts += 1.0 + 0.1 * math.sin(2.0 * math.pi * tick / 7.0)
    _write_zst_jsonl(run_dir / "events.jsonl.zst", rows)

    out_dir = tmp_path / "out"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(run_dir),
            "--out-dir",
            str(out_dir),
            "--window-size",
            "32",
            "--window-step",
            "16",
            "--min-period-ticks",
            "6",
            "--max-period-ticks",
            "20",
        ],
        check=True,
        cwd=ROOT,
    )

    duration = json.loads((out_dir / "F8_02_tick_duration_analysis.json").read_text())
    assert duration["overall"]["n"] == 79
    assert duration["description"] == "Tick-duration (endogenous clock) analysis"

    scan = _read_csv(out_dir / "sie_v2" / "sie_v2_scan_summary.csv")
    assert len(scan) == 1
    assert int(scan[0]["n"]) == 80
    assert float(scan[0]["v2_std"]) > 0.05

    cycles = _read_csv(out_dir / "sie_v2" / "sie_v2_cycle_metrics.csv")
    assert len(cycles) >= 5
    periods = [int(float(row["period_ticks"])) for row in cycles]
    assert statistics_median(periods) == 10

    windows = _read_csv(out_dir / "sie_v2" / "sie_v2_window_metrics.csv")
    assert windows
    assert all(float(row["dom_period"]) > 0.0 for row in windows)


def statistics_median(vals: list[int]) -> int:
    vals = sorted(vals)
    return vals[len(vals) // 2]
