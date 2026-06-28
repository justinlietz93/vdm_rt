"""Guards for the local SIE v2 endogenous-clock reference evidence."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SIE_V2_TABLES = ROOT / "dev-references" / "aura-run" / "tables" / "sie_v2"
TICK_DURATION_JSON = (
    ROOT / "dev-references" / "aura-run" / "json" / "F8_02_tick_duration_analysis.json"
)


def _require_local_evidence() -> None:
    required = [
        SIE_V2_TABLES / "sie_v2_scan_summary.csv",
        SIE_V2_TABLES / "sie_v2_cycle_metrics.csv",
        SIE_V2_TABLES / "sie_v2_window_metrics.csv",
        TICK_DURATION_JSON,
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        pytest.skip("local endogenous-clock evidence is absent: " + ", ".join(missing))


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def test_sie_v2_reference_keeps_endogenous_cycle_shape() -> None:
    _require_local_evidence()

    summary = _rows(SIE_V2_TABLES / "sie_v2_scan_summary.csv")
    cycles = _rows(SIE_V2_TABLES / "sie_v2_cycle_metrics.csv")
    windows = _rows(SIE_V2_TABLES / "sie_v2_window_metrics.csv")

    assert len(summary) == 1
    scan = summary[0]
    assert int(scan["t_max"]) - int(scan["t_min"]) + 1 == int(scan["n"])
    assert int(scan["n"]) >= 1500

    assert _f(scan, "v2_std") > 0.01
    assert _f(scan, "fit_amp") > 0.01
    assert _f(scan, "fit_r2_time") > 0.70
    assert _f(scan, "fit_r2_tick") < 0.20
    assert abs(_f(scan, "corr_v2_omega")) > 0.75
    assert abs(_f(scan, "corr_v2_a_mean")) > 0.75

    periods = [int(float(row["period_ticks"])) for row in cycles]
    amplitudes = [float(row["amplitude"]) for row in cycles]
    assert len(cycles) >= 50
    assert min(periods) >= 10
    assert max(periods) <= 60
    assert len(set(periods)) >= 10
    assert all(amp > 0.0 for amp in amplitudes)
    for row in cycles:
        assert int(row["t_next_peak"]) - int(row["t_peak"]) == int(float(row["period_ticks"]))

    assert len(windows) >= 10
    assert all(float(row["dom_period"]) > 0.0 for row in windows)
    assert all(0.0 <= float(row["spec_entropy"]) <= 1.0 for row in windows)


def test_tick_duration_reference_keeps_variable_processing_depth() -> None:
    _require_local_evidence()

    with TICK_DURATION_JSON.open(encoding="utf-8") as fh:
        report = json.load(fh)

    assert report["description"] == "Tick-duration (endogenous clock) analysis"
    overall = report["overall"]
    assert overall["n"] >= 90
    assert overall["cv"] > 0.10
    assert overall["p95"] > overall["median"]
    assert overall["max"] > overall["p95"]

    correlations = report["correlations_with_state"]
    assert abs(correlations["dt_vs_entropy"]) > 0.05
    assert abs(correlations["dt_vs_b1_z"]) > 0.05
