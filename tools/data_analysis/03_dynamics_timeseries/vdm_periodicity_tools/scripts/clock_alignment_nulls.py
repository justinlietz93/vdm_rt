#!/usr/bin/env python3
"""
Clock-alignment null tests for a VDM signal.

This does not patch the runtime. It attacks the interpretation of a periodic trace by
comparing wall-time fit, tick/model-time fit, constant-dt reconstruction, shuffled-dt
reconstruction, and phase-sector concentration.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict

import numpy as np

from sie_periodicity_scan import read_table, rows_to_arrays, sine_fit_grid, local_maxima, cycle_table, corr


def rayleigh_r(phases: np.ndarray) -> float:
    phases = phases[np.isfinite(phases)]
    if len(phases) == 0:
        return float("nan")
    z = np.mean(np.exp(1j * phases))
    return float(abs(z))


def phase_sector_stats(times: np.ndarray, event_mask: np.ndarray, period: float, phase: float = 0.0) -> Dict[str, float]:
    if period <= 0 or not np.isfinite(period):
        return {"n_events": 0, "rayleigh_r": float("nan"), "mean_phase_rad": float("nan")}
    event_times = times[event_mask]
    phases = (2.0 * np.pi * event_times / period + phase) % (2.0 * np.pi)
    if len(phases) == 0:
        return {"n_events": 0, "rayleigh_r": float("nan"), "mean_phase_rad": float("nan")}
    mean = np.angle(np.mean(np.exp(1j * phases))) % (2.0 * np.pi)
    return {"n_events": int(len(phases)), "rayleigh_r": rayleigh_r(phases), "mean_phase_rad": float(mean)}


def shuffled_dt_time(wall: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    dt = np.diff(wall)
    dt = dt[np.isfinite(dt)]
    if len(dt) == 0:
        return wall.copy()
    shuffled = rng.permutation(dt)
    out = np.zeros(len(wall), dtype=float)
    out[1:len(shuffled)+1] = np.cumsum(shuffled)
    if len(out) > len(shuffled) + 1:
        out[len(shuffled)+1:] = out[len(shuffled)]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="VDM wall-clock vs endogenous/tick-clock null analysis.")
    ap.add_argument("input", type=Path, help="events.jsonl(.gz) or CSV")
    ap.add_argument("--signal", default=None)
    ap.add_argument("--hz", type=float, default=10.0)
    ap.add_argument("--out", type=Path, default=Path("clock_nulls_summary.json"))
    ap.add_argument("--wall-period-min", type=float, default=10.0)
    ap.add_argument("--wall-period-max", type=float, default=180.0)
    ap.add_argument("--tick-period-min", type=float, default=5.0)
    ap.add_argument("--tick-period-max", type=float, default=120.0)
    ap.add_argument("--shuffle-count", type=int, default=256)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    rows = read_table(args.input, args.signal)
    arrays = rows_to_arrays(rows, args.hz)
    tick = arrays["tick"]
    wall = arrays["wall_s"]
    y = arrays["signal"]
    model_time = (tick - np.nanmin(tick)) / args.hz
    const_dt_time = np.arange(len(y), dtype=float) * (np.nanmedian(np.diff(wall)) if len(wall) > 1 else 1.0 / args.hz)

    wall_fit = sine_fit_grid(wall, y, args.wall_period_min, args.wall_period_max)
    model_fit = sine_fit_grid(model_time, y, args.wall_period_min, args.wall_period_max)
    tick_fit = sine_fit_grid(tick, y, args.tick_period_min, args.tick_period_max)
    const_fit = sine_fit_grid(const_dt_time, y, args.wall_period_min, args.wall_period_max)

    shuffle_r2 = []
    shuffle_periods = []
    for j in range(args.shuffle_count):
        st = shuffled_dt_time(wall, args.seed + j)
        fit = sine_fit_grid(st, y, args.wall_period_min, args.wall_period_max, grid=300)
        shuffle_r2.append(fit["r2"])
        shuffle_periods.append(fit["period"])
    shuffle_r2_a = np.array(shuffle_r2, dtype=float)

    prom = max(1e-12, 0.25 * float(np.nanstd(y)))
    peaks = local_maxima(tick, y, min_distance=5, min_prominence=prom)
    peak_mask = np.zeros(len(y), dtype=bool)
    peak_mask[peaks] = True

    summary: Dict[str, Any] = {
        "input": str(args.input),
        "rows": int(len(y)),
        "wall_fit": wall_fit,
        "model_time_fit": model_fit,
        "tick_index_fit": tick_fit,
        "constant_dt_fit": const_fit,
        "r2_advantage_wall_minus_model_time": float(wall_fit["r2"] - model_fit["r2"]),
        "r2_advantage_wall_minus_constant_dt": float(wall_fit["r2"] - const_fit["r2"]),
        "shuffle_dt_null": {
            "count": int(args.shuffle_count),
            "r2_mean": float(np.nanmean(shuffle_r2_a)),
            "r2_median": float(np.nanmedian(shuffle_r2_a)),
            "r2_p95": float(np.nanpercentile(shuffle_r2_a, 95)),
            "r2_p99": float(np.nanpercentile(shuffle_r2_a, 99)),
            "actual_wall_r2": float(wall_fit["r2"]),
            "empirical_p_ge_actual": float((np.sum(shuffle_r2_a >= wall_fit["r2"]) + 1) / (len(shuffle_r2_a) + 1)),
        },
        "peak_phase_concentration_against_wall_fit": phase_sector_stats(wall, peak_mask, wall_fit["period"], wall_fit.get("phase", 0.0)),
        "peak_phase_concentration_against_model_fit": phase_sector_stats(model_time, peak_mask, model_fit["period"], model_fit.get("phase", 0.0)),
        "interpretation_flags": {
            "wall_fit_stronger_than_model_time": bool(wall_fit["r2"] > model_fit["r2"]),
            "wall_fit_beats_shuffled_dt_p99": bool(wall_fit["r2"] > np.nanpercentile(shuffle_r2_a, 99)),
            "peaks_phase_cluster_on_wall_fit": bool(phase_sector_stats(wall, peak_mask, wall_fit["period"], wall_fit.get("phase", 0.0))["rayleigh_r"] > 0.5),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
