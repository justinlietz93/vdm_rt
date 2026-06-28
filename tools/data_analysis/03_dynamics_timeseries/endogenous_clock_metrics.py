"""Metrics for offline endogenous-clock evidence regeneration."""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any

try:
    from .endogenous_clock_io import SIE_DIR_NAME, float_value, time_value, write_csv
except ImportError:
    from endogenous_clock_io import SIE_DIR_NAME, float_value, time_value, write_csv


def _percentile(sorted_vals: list[float], frac: float) -> float:
    if not sorted_vals:
        return math.nan
    idx = min(len(sorted_vals) - 1, max(0, int(frac * len(sorted_vals))))
    return sorted_vals[idx]


def basic_stats(vals: list[float]) -> dict[str, Any]:
    if not vals:
        return {"n": 0, "error": "too few"}
    sorted_vals = sorted(vals)
    mean = statistics.mean(vals)
    std = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return {
        "n": len(vals),
        "mean": round(mean, 4),
        "std": round(std, 4),
        "median": round(statistics.median(vals), 4),
        "cv": round(std / mean, 4) if mean > 0 else 0.0,
        "min": round(sorted_vals[0], 4),
        "max": round(sorted_vals[-1], 4),
        "p5": round(_percentile(sorted_vals, 0.05), 4),
        "p25": round(_percentile(sorted_vals, 0.25), 4),
        "p75": round(_percentile(sorted_vals, 0.75), 4),
        "p95": round(_percentile(sorted_vals, 0.95), 4),
        "p99": round(_percentile(sorted_vals, 0.99), 4),
    }


def pearson(x_vals: list[float], y_vals: list[float]) -> float | None:
    pairs = [(x, y) for x, y in zip(x_vals, y_vals) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 3:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in pairs)
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return None if dx * dy == 0.0 else num / (dx * dy)


def autocorr_lag(vals: list[float], lag: int) -> float | None:
    if len(vals) <= lag or len(vals) < 3:
        return None
    mean = statistics.mean(vals)
    var = statistics.variance(vals)
    if var == 0.0:
        return None
    num = sum((vals[i] - mean) * (vals[i + lag] - mean) for i in range(len(vals) - lag))
    return num / ((len(vals) - lag) * var)


def epoch_of(tick: int, boundaries: tuple[int, int]) -> str:
    if tick < boundaries[0]:
        return "E1"
    if tick < boundaries[1]:
        return "E2"
    return "E3"


def compute_tick_durations(
    rows: list[dict[str, Any]],
    *,
    dt_max_s: float,
    epoch_boundaries: tuple[int, int],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    durations: list[dict[str, Any]] = []
    for prev, cur in zip(rows[:-1], rows[1:]):
        t_prev = int(prev["t"])
        t_cur = int(cur["t"])
        ts_prev = time_value(prev)
        ts_cur = time_value(cur)
        dt_sec = ts_cur - ts_prev
        if t_cur - t_prev == 1 and 0.0 < dt_sec < dt_max_s:
            durations.append(
                {
                    "t": t_cur,
                    "dt_sec": dt_sec,
                    "entropy": float_value(cur, "connectome_entropy"),
                    "active_edges": float_value(cur, "active_edges"),
                    "b1_z": float_value(cur, "b1_z"),
                    "firing_var": float_value(cur, "firing_var"),
                    "epoch": epoch_of(t_cur, epoch_boundaries),
                }
            )
    dt_vals = [d["dt_sec"] for d in durations]
    epoch_stats: dict[str, Any] = {}
    for ep in ("E1", "E2", "E3"):
        vals = [d["dt_sec"] for d in durations if d["epoch"] == ep]
        epoch_stats[ep] = basic_stats(vals) if len(vals) >= 10 else {"n": len(vals), "error": "too few"}

    correlations: dict[str, float] = {}
    for field in ("entropy", "active_edges", "b1_z"):
        corr = pearson(dt_vals, [d[field] for d in durations])
        if corr is not None:
            correlations[f"dt_vs_{field}"] = round(corr, 4)

    dt_autocorr: dict[str, float] = {}
    for lag in (1, 2, 3, 5, 10, 20, 50):
        ac = autocorr_lag(dt_vals, lag)
        if ac is not None:
            dt_autocorr[f"lag_{lag}"] = round(ac, 4)

    result = {
        "description": "Tick-duration (endogenous clock) analysis",
        "overall": basic_stats(dt_vals),
        "by_epoch": epoch_stats,
        "correlations_with_state": correlations,
        "dt_autocorrelation": dt_autocorr,
        "interpretation": {
            "cv_meaning": "CV >> 0 means tick durations are highly variable = processing depth varies.",
            "autocorr_meaning": "Positive autocorr at lag 1 = slow ticks cluster together (sustained deep processing).",
            "correlation_meaning": "Nonzero r(dt, entropy) = the clock speed depends on internal disorder level.",
        },
    }
    return result, durations


def _solve3(mat: list[list[float]], vec: list[float]) -> list[float] | None:
    aug = [row[:] + [rhs] for row, rhs in zip(mat, vec)]
    n = 3
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        div = aug[col][col]
        for j in range(col, n + 1):
            aug[col][j] /= div
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            for j in range(col, n + 1):
                aug[r][j] -= factor * aug[col][j]
    return [aug[i][n] for i in range(n)]


def _fit_sine(xs: list[float], ys: list[float], period: float) -> dict[str, float] | None:
    if len(xs) < 6 or period <= 0.0:
        return None
    w = 2.0 * math.pi / period
    cols = [(1.0, math.sin(w * x), math.cos(w * x)) for x in xs]
    mat = [[0.0] * 3 for _ in range(3)]
    vec = [0.0, 0.0, 0.0]
    for col_vals, y in zip(cols, ys):
        for i in range(3):
            vec[i] += col_vals[i] * y
            for j in range(3):
                mat[i][j] += col_vals[i] * col_vals[j]
    beta = _solve3(mat, vec)
    if beta is None:
        return None
    y_mean = statistics.mean(ys)
    sst = sum((y - y_mean) ** 2 for y in ys)
    if sst <= 0.0:
        return None
    preds = [beta[0] + beta[1] * s + beta[2] * c for s, c in ((v[1], v[2]) for v in cols)]
    sse = sum((y - p) ** 2 for y, p in zip(ys, preds))
    return {
        "period": period,
        "r2": 1.0 - (sse / sst),
        "amp": math.sqrt(beta[1] ** 2 + beta[2] ** 2),
        "mean": beta[0],
        "sin_coeff": beta[1],
        "cos_coeff": beta[2],
    }


def _best_sine_fit(
    xs: list[float],
    ys: list[float],
    min_period: float,
    max_period: float,
    candidates: int = 240,
    period_hints: list[float] | None = None,
) -> dict[str, float] | None:
    if len(xs) < 6:
        return None
    span = max(xs) - min(xs)
    hi = min(max_period, max(min_period, span * 0.95))
    lo = min(min_period, hi)
    if hi <= 0.0 or hi <= lo:
        return None

    def in_bounds(period: float) -> bool:
        return math.isfinite(period) and lo <= period <= hi

    def refine(center: float, width: float, steps: int) -> dict[str, float] | None:
        if not in_bounds(center):
            return None
        left = max(lo, center - width)
        right = min(hi, center + width)
        if right <= left:
            return _fit_sine(xs, ys, center)
        local_best: dict[str, float] | None = None
        for j in range(max(3, steps)):
            period = left + (right - left) * j / max(1, steps - 1)
            fit = _fit_sine(xs, ys, period)
            if fit is not None and (local_best is None or fit["r2"] > local_best["r2"]):
                local_best = fit
        return local_best

    best: dict[str, float] | None = None
    for i in range(max(8, candidates)):
        period = lo + (hi - lo) * i / max(1, candidates - 1)
        fit = _fit_sine(xs, ys, period)
        if fit is not None and (best is None or fit["r2"] > best["r2"]):
            best = fit
    hints = [h for h in (period_hints or []) if in_bounds(h)]
    for hint in hints:
        fit = refine(hint, width=max(0.25, hint * 0.08), steps=161)
        if fit is not None and (best is None or fit["r2"] > best["r2"]):
            best = fit
    if best is not None:
        for width in (max(0.1, best["period"] * 0.02), max(0.01, best["period"] * 0.002)):
            fit = refine(best["period"], width=width, steps=121)
            if fit is not None and fit["r2"] > best["r2"]:
                best = fit
    return best


def _find_peak_indices(vals: list[float], min_distance: int) -> list[int]:
    candidates = [
        i
        for i in range(1, len(vals) - 1)
        if vals[i] >= vals[i - 1] and vals[i] > vals[i + 1]
    ]
    peaks: list[int] = []
    for idx in candidates:
        if peaks and idx - peaks[-1] < min_distance:
            if vals[idx] > vals[peaks[-1]]:
                peaks[-1] = idx
            continue
        peaks.append(idx)
    return peaks


def _period_hints_from_peaks(
    xs: list[float],
    vals: list[float],
    *,
    min_period: float,
    max_period: float,
) -> list[float]:
    hints: list[float] = []
    for min_distance in (3, 5, 8, 12, 15, 20, 24):
        peaks = _find_peak_indices(vals, min_distance=min_distance)
        deltas = [xs[right] - xs[left] for left, right in zip(peaks[:-1], peaks[1:])]
        deltas = [d for d in deltas if math.isfinite(d) and d > 0.0]
        if not deltas:
            continue
        for base in (statistics.median(deltas), statistics.mean(deltas)):
            for scale in (0.5, 1.0, 2.0):
                candidate = base * scale
                if min_period <= candidate <= max_period:
                    hints.append(candidate)
    deduped: list[float] = []
    for candidate in hints:
        if not any(abs(candidate - existing) < 1e-6 for existing in deduped):
            deduped.append(candidate)
    return deduped


def compute_cycle_metrics(ticks: list[int], vals: list[float], min_peak_distance: int) -> list[dict[str, Any]]:
    peaks = _find_peak_indices(vals, min_distance=min_peak_distance)
    rows: list[dict[str, Any]] = []
    for left, right in zip(peaks[:-1], peaks[1:]):
        if right <= left:
            continue
        segment = vals[left : right + 1]
        trough_rel = min(range(len(segment)), key=lambda i: segment[i])
        trough_idx = left + trough_rel
        rows.append(
            {
                "t_peak": ticks[left],
                "t_next_peak": ticks[right],
                "period_ticks": ticks[right] - ticks[left],
                "peak_val": vals[left],
                "trough_t": ticks[trough_idx],
                "trough_val": vals[trough_idx],
                "amplitude": vals[left] - vals[trough_idx],
            }
        )
    return rows


def compute_window_metrics(
    ticks: list[int],
    vals: list[float],
    *,
    window_size: int,
    window_step: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    n = len(vals)
    if n < max(8, window_size):
        return rows
    for start in range(0, n - window_size + 1, max(1, window_step)):
        chunk = vals[start : start + window_size]
        mean = statistics.mean(chunk)
        centered = [v - mean for v in chunk]
        powers: list[float] = []
        for k in range(1, window_size // 2 + 1):
            re = 0.0
            im = 0.0
            for idx, val in enumerate(centered):
                angle = 2.0 * math.pi * k * idx / window_size
                re += val * math.cos(angle)
                im -= val * math.sin(angle)
            powers.append(re * re + im * im)
        total = sum(powers)
        if total <= 0.0:
            continue
        dom_idx = max(range(len(powers)), key=lambda i: powers[i])
        probs = [p / total for p in powers if p > 0.0]
        entropy = -sum(p * math.log(p) for p in probs) / math.log(len(probs)) if len(probs) > 1 else 0.0
        rows.append(
            {
                "t_center": ticks[start + window_size // 2],
                "dom_period": window_size / float(dom_idx + 1),
                "dom_power_frac": powers[dom_idx] / total,
                "spec_entropy": entropy,
            }
        )
    return rows


def compute_sie_v2_summary(
    rows: list[dict[str, Any]],
    durations: list[dict[str, Any]],
    *,
    min_period_s: float,
    max_period_s: float,
    min_period_ticks: float,
    max_period_ticks: float,
    min_peak_distance: int,
    window_size: int,
    window_step: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    series: list[tuple[int, float, float, float, float]] = []
    for row in rows:
        val = float_value(row, "sie_v2_valence_01")
        if math.isnan(val):
            continue
        ts = time_value(row)
        series.append((int(row["t"]), ts, val, float_value(row, "omega_mean"), float_value(row, "a_mean")))
    if not series:
        raise RuntimeError("No sie_v2_valence_01 values found in input rows")
    ticks = [s[0] for s in series]
    times = [s[1] for s in series]
    vals = [s[2] for s in series]
    omegas = [s[3] for s in series]
    a_means = [s[4] for s in series]

    tick_x = [float(t - ticks[0]) for t in ticks]
    time_ok = [math.isfinite(t) for t in times]
    time_fit = None
    if all(time_ok):
        t0 = times[0]
        time_x = [t - t0 for t in times]
        time_fit = _best_sine_fit(
            time_x,
            vals,
            min_period_s,
            max_period_s,
            period_hints=_period_hints_from_peaks(time_x, vals, min_period=min_period_s, max_period=max_period_s),
        )
    tick_fit = _best_sine_fit(
        tick_x,
        vals,
        min_period_ticks,
        max_period_ticks,
        period_hints=_period_hints_from_peaks(
            tick_x,
            vals,
            min_period=min_period_ticks,
            max_period=max_period_ticks,
        ),
    )

    dt_by_tick = {int(d["t"]): float(d["dt_sec"]) for d in durations}
    corr_absres_dt = math.nan
    if time_fit is not None and all(time_ok):
        fit = _fit_sine([t - times[0] for t in times], vals, time_fit["period"])
        if fit is not None:
            w = 2.0 * math.pi / fit["period"]
            residuals: list[float] = []
            dts: list[float] = []
            for tick, ts, y, _, _ in series:
                x = ts - times[0]
                pred = fit["mean"] + fit["sin_coeff"] * math.sin(w * x) + fit["cos_coeff"] * math.cos(w * x)
                if tick in dt_by_tick:
                    residuals.append(abs(y - pred))
                    dts.append(dt_by_tick[tick])
            corr = pearson(residuals, dts)
            if corr is not None:
                corr_absres_dt = corr

    summary = {
        "t_min": min(ticks),
        "t_max": max(ticks),
        "n": len(vals),
        "v2_mean": statistics.mean(vals),
        "v2_std": statistics.stdev(vals) if len(vals) > 1 else 0.0,
        "v2_min": min(vals),
        "v2_max": max(vals),
        "fit_period_s": math.nan if time_fit is None else time_fit["period"],
        "fit_r2_time": math.nan if time_fit is None else time_fit["r2"],
        "fit_amp": math.nan if time_fit is None else time_fit["amp"],
        "fit_mean": math.nan if time_fit is None else time_fit["mean"],
        "fit_r2_tick": math.nan if tick_fit is None else tick_fit["r2"],
        "fit_period_ticks": math.nan if tick_fit is None else tick_fit["period"],
        "corr_v2_omega": pearson(vals, omegas) or math.nan,
        "corr_v2_a_mean": pearson(vals, a_means) or math.nan,
        "corr_absres_dt": corr_absres_dt,
    }
    dt_vals = [float(d["dt_sec"]) for d in durations]
    sorted_dt = sorted(dt_vals)
    summary.update(
        {
            "dt_median_s": statistics.median(dt_vals) if dt_vals else math.nan,
            "dt_p95_s": _percentile(sorted_dt, 0.95) if sorted_dt else math.nan,
            "dt_p99_s": _percentile(sorted_dt, 0.99) if sorted_dt else math.nan,
            "dt_max_s": max(dt_vals) if dt_vals else math.nan,
            "dt_count_gt_10_s": sum(1 for dt in dt_vals if dt > 10.0),
        }
    )
    cycles = compute_cycle_metrics(ticks, vals, min_peak_distance=min_peak_distance)
    windows = compute_window_metrics(ticks, vals, window_size=window_size, window_step=window_step)
    return summary, cycles, windows


def write_outputs(
    rows: list[dict[str, Any]],
    out_dir: Path,
    *,
    prefix: str,
    dt_max_s: float,
    epoch_boundaries: tuple[int, int],
    min_period_s: float,
    max_period_s: float,
    min_period_ticks: float,
    max_period_ticks: float,
    min_peak_distance: int,
    window_size: int,
    window_step: int,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    duration_report, durations = compute_tick_durations(
        rows,
        dt_max_s=dt_max_s,
        epoch_boundaries=epoch_boundaries,
    )
    duration_json = out_dir / f"{prefix}_tick_duration_analysis.json"
    duration_csv = out_dir / f"{prefix}_tick_durations.csv"
    duration_json.write_text(json.dumps(duration_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(
        duration_csv,
        durations,
        ["t", "dt_sec", "entropy", "active_edges", "b1_z", "epoch"],
    )

    summary, cycles, windows = compute_sie_v2_summary(
        rows,
        durations,
        min_period_s=min_period_s,
        max_period_s=max_period_s,
        min_period_ticks=min_period_ticks,
        max_period_ticks=max_period_ticks,
        min_peak_distance=min_peak_distance,
        window_size=window_size,
        window_step=window_step,
    )
    sie_dir = out_dir / SIE_DIR_NAME
    scan_csv = sie_dir / "sie_v2_scan_summary.csv"
    cycle_csv = sie_dir / "sie_v2_cycle_metrics.csv"
    window_csv = sie_dir / "sie_v2_window_metrics.csv"
    write_csv(scan_csv, [summary], list(summary.keys()))
    write_csv(
        cycle_csv,
        cycles,
        ["t_peak", "t_next_peak", "period_ticks", "peak_val", "trough_t", "trough_val", "amplitude"],
    )
    write_csv(
        window_csv,
        windows,
        ["t_center", "dom_period", "dom_power_frac", "spec_entropy"],
    )
    return {
        "duration_json": duration_json,
        "duration_csv": duration_csv,
        "scan_csv": scan_csv,
        "cycle_csv": cycle_csv,
        "window_csv": window_csv,
    }
