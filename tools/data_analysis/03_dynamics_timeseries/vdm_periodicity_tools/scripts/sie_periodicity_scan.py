#!/usr/bin/env python3
"""
SIE / endogenous-clock periodicity scan for VDM runtime logs.

Reads events.jsonl or CSV, normalizes tick/time/signal fields, and writes:
  - summary.json
  - normalized_tick_table.csv
  - peaks.csv
  - cycles.csv
  - PNG figures matching the Aura periodicity audit style

No runtime patching. No runtime imports. Analysis only.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

try:
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover
    raise SystemExit("matplotlib is required for plotting") from exc


DEFAULT_SIGNAL_CANDIDATES = (
    "sie_v2_valence_01",
    "sie2_valence_01",
    "sie_v2",
    "v2",
    "evt_sie_v2_valence_01",
)
DEFAULT_TICK_CANDIDATES = ("t", "tick", "step", "time_step")
DEFAULT_TS_CANDIDATES = ("ts", "timestamp", "wall_ts", "wall_time", "datetime")
DEFAULT_WALL_ELAPSED_CANDIDATES = ("wall_elapsed_s", "elapsed_s", "wall_s", "seconds")

NUMERIC_FIELDS = (
    "sie_v2_valence_01",
    "sie_valence_01",
    "sie_total_reward",
    "omega_mean",
    "a_mean",
    "connectome_entropy",
    "active_edges",
    "active_synapses",
    "b1_z",
    "vt_coverage",
    "vt_entropy",
    "firing_var",
)


def _open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def _parse_timestamp(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        # If epoch-like, return as-is; if already elapsed-like, still usable.
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        pass
    # Common ISO variants, including trailing Z.
    s2 = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s2).timestamp()
    except ValueError:
        pass
    # Last ditch: strip subsecond/timezone decorations badly emitted by logs.
    try:
        if "+" in s2:
            s2 = s2.split("+")[0]
        if s2.endswith(" UTC"):
            s2 = s2[:-4]
        return datetime.fromisoformat(s2).replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return None


def _dig_numeric(obj: Dict[str, Any], key: str) -> Optional[float]:
    """Read numeric fields from flat dicts or one-level nested metric dicts."""
    if key in obj:
        try:
            v = float(obj[key])
            return v if math.isfinite(v) else None
        except Exception:
            return None
    for parent in ("metrics", "why", "state", "connectome", "telemetry"):
        sub = obj.get(parent)
        if isinstance(sub, dict) and key in sub:
            try:
                v = float(sub[key])
                return v if math.isfinite(v) else None
            except Exception:
                return None
    return None


def _dig_any(obj: Dict[str, Any], keys: Sequence[str]) -> Optional[Any]:
    for key in keys:
        if key in obj:
            return obj[key]
    for parent in ("metrics", "why", "state", "connectome", "telemetry"):
        sub = obj.get(parent)
        if isinstance(sub, dict):
            for key in keys:
                if key in sub:
                    return sub[key]
    return None


def read_jsonl(path: Path, signal: Optional[str] = None) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    signal_candidates = (signal,) if signal else DEFAULT_SIGNAL_CANDIDATES
    with _open_text(path) as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            tick_raw = _dig_any(obj, DEFAULT_TICK_CANDIDATES)
            try:
                tick = int(tick_raw) if tick_raw is not None else len(rows)
            except Exception:
                tick = len(rows)

            wall_elapsed = _dig_any(obj, DEFAULT_WALL_ELAPSED_CANDIDATES)
            wall_elapsed_s = None
            if wall_elapsed is not None:
                try:
                    wall_elapsed_s = float(wall_elapsed)
                    if not math.isfinite(wall_elapsed_s):
                        wall_elapsed_s = None
                except Exception:
                    wall_elapsed_s = None

            ts_raw = _dig_any(obj, DEFAULT_TS_CANDIDATES)
            ts_epoch = _parse_timestamp(ts_raw)

            sig_val = None
            sig_name = None
            for cand in signal_candidates:
                if cand is None:
                    continue
                sig_val = _dig_numeric(obj, cand)
                if sig_val is not None:
                    sig_name = cand
                    break
            if sig_val is None:
                continue

            out = {
                "tick": float(tick),
                "signal": float(sig_val),
                "line_no": float(line_no),
            }
            if wall_elapsed_s is not None:
                out["wall_elapsed_s"] = wall_elapsed_s
            if ts_epoch is not None:
                out["ts_epoch"] = ts_epoch
            for key in NUMERIC_FIELDS:
                val = _dig_numeric(obj, key)
                if val is not None:
                    out[key] = val
            rows.append(out)
    return rows


def read_csv_any(path: Path, signal: Optional[str] = None) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    with _open_text(path) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        sig = signal
        if sig is None:
            for cand in DEFAULT_SIGNAL_CANDIDATES:
                if cand in fieldnames:
                    sig = cand
                    break
        if sig is None or sig not in fieldnames:
            raise SystemExit(f"No signal field found. Available fields: {fieldnames[:40]}")
        tick_key = next((k for k in DEFAULT_TICK_CANDIDATES if k in fieldnames), None)
        wall_key = next((k for k in DEFAULT_WALL_ELAPSED_CANDIDATES if k in fieldnames), None)
        ts_key = next((k for k in DEFAULT_TS_CANDIDATES if k in fieldnames), None)
        for i, row in enumerate(reader):
            try:
                val = float(row[sig])
                if not math.isfinite(val):
                    continue
            except Exception:
                continue
            tick = i
            if tick_key:
                try:
                    tick = int(float(row[tick_key]))
                except Exception:
                    pass
            out = {"tick": float(tick), "signal": val, "line_no": float(i + 2)}
            if wall_key and row.get(wall_key, "") != "":
                try:
                    out["wall_elapsed_s"] = float(row[wall_key])
                except Exception:
                    pass
            if ts_key:
                parsed = _parse_timestamp(row.get(ts_key))
                if parsed is not None:
                    out["ts_epoch"] = parsed
            for key in NUMERIC_FIELDS:
                if key in row and row.get(key, "") != "":
                    try:
                        vv = float(row[key])
                        if math.isfinite(vv):
                            out[key] = vv
                    except Exception:
                        pass
            rows.append(out)
    return rows


def read_table(path: Path, signal: Optional[str]) -> List[Dict[str, float]]:
    suffixes = ''.join(path.suffixes)
    if path.suffix in (".jsonl", ".ndjson") or suffixes.endswith(".jsonl.gz"):
        return read_jsonl(path, signal)
    return read_csv_any(path, signal)


def rows_to_arrays(rows: List[Dict[str, float]], hz: Optional[float]) -> Dict[str, np.ndarray]:
    if not rows:
        raise SystemExit("No rows with usable signal were found.")
    rows = sorted(rows, key=lambda r: (r.get("tick", 0), r.get("line_no", 0)))
    tick = np.array([r["tick"] for r in rows], dtype=float)
    signal = np.array([r["signal"] for r in rows], dtype=float)

    wall = None
    if all("wall_elapsed_s" in r for r in rows):
        wall = np.array([r["wall_elapsed_s"] for r in rows], dtype=float)
    elif all("ts_epoch" in r for r in rows):
        ts = np.array([r["ts_epoch"] for r in rows], dtype=float)
        wall = ts - np.nanmin(ts)
    elif hz and hz > 0:
        wall = (tick - np.nanmin(tick)) / hz
    else:
        wall = tick - np.nanmin(tick)

    arrays = {"tick": tick, "wall_s": wall, "signal": signal}
    for key in NUMERIC_FIELDS:
        vals = []
        ok = False
        for r in rows:
            if key in r:
                vals.append(r[key])
                ok = True
            else:
                vals.append(float("nan"))
        if ok:
            arrays[key] = np.array(vals, dtype=float)
    return arrays


def local_maxima(x: np.ndarray, y: np.ndarray, min_distance: int, min_prominence: float) -> np.ndarray:
    """Small dependency-free local peak finder."""
    n = len(y)
    if n < 3:
        return np.array([], dtype=int)
    candidates = []
    for i in range(1, n - 1):
        if not (np.isfinite(y[i - 1]) and np.isfinite(y[i]) and np.isfinite(y[i + 1])):
            continue
        if y[i] >= y[i - 1] and y[i] > y[i + 1]:
            left_min = np.nanmin(y[max(0, i - min_distance):i + 1])
            right_min = np.nanmin(y[i:min(n, i + min_distance + 1)])
            prom = y[i] - max(left_min, right_min)
            if prom >= min_prominence:
                candidates.append((i, y[i], prom))
    if not candidates:
        return np.array([], dtype=int)
    # Greedy distance filter by height.
    candidates.sort(key=lambda z: z[1], reverse=True)
    kept: List[int] = []
    for idx, _, _ in candidates:
        if all(abs(idx - j) >= min_distance for j in kept):
            kept.append(idx)
    kept.sort()
    return np.array(kept, dtype=int)


def sine_fit_grid(x: np.ndarray, y: np.ndarray, min_period: float, max_period: float, grid: int = 800) -> Dict[str, float]:
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) < 10:
        return {"r2": float("nan"), "period": float("nan"), "amplitude": float("nan"), "phase": float("nan"), "offset": float("nan")}
    y0 = y - np.mean(y)
    periods = np.linspace(min_period, max_period, grid)
    best = None
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    if ss_tot <= 0:
        ss_tot = 1e-12
    for period in periods:
        w = 2 * math.pi / period
        X = np.column_stack([np.ones_like(x), np.sin(w * x), np.cos(w * x)])
        try:
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        except np.linalg.LinAlgError:
            continue
        yhat = X @ beta
        ss_res = float(np.sum((y - yhat) ** 2))
        r2 = 1.0 - ss_res / ss_tot
        amp = float(math.sqrt(beta[1] ** 2 + beta[2] ** 2))
        phase = float(math.atan2(beta[2], beta[1]))
        rec = (r2, period, amp, phase, float(beta[0]), beta, yhat)
        if best is None or rec[0] > best[0]:
            best = rec
    if best is None:
        return {"r2": float("nan"), "period": float("nan"), "amplitude": float("nan"), "phase": float("nan"), "offset": float("nan")}
    return {"r2": float(best[0]), "period": float(best[1]), "amplitude": float(best[2]), "phase": float(best[3]), "offset": float(best[4])}


def cycle_table(tick: np.ndarray, wall: np.ndarray, y: np.ndarray, peaks: np.ndarray) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    for j in range(len(peaks) - 1):
        i0 = int(peaks[j])
        i1 = int(peaks[j + 1])
        if i1 <= i0:
            continue
        seg = y[i0:i1 + 1]
        rows.append({
            "cycle": float(j),
            "peak0_index": float(i0),
            "peak1_index": float(i1),
            "peak0_tick": float(tick[i0]),
            "peak1_tick": float(tick[i1]),
            "period_ticks": float(tick[i1] - tick[i0]),
            "peak0_wall_s": float(wall[i0]),
            "peak1_wall_s": float(wall[i1]),
            "period_wall_s": float(wall[i1] - wall[i0]),
            "amplitude": float(np.nanmax(seg) - np.nanmin(seg)),
            "mean_dt_s": float((wall[i1] - wall[i0]) / max(1.0, tick[i1] - tick[i0])),
        })
    return rows


def write_csv(path: Path, rows: List[Dict[str, float]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def write_normalized_csv(path: Path, arrays: Dict[str, np.ndarray]) -> None:
    keys = ["tick", "wall_s", "signal"] + [k for k in NUMERIC_FIELDS if k in arrays]
    n = len(arrays["tick"])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(keys)
        for i in range(n):
            w.writerow([arrays[k][i] if k in arrays else "" for k in keys])


def corr(x: np.ndarray, y: np.ndarray) -> float:
    mask = np.isfinite(x) & np.isfinite(y)
    if np.sum(mask) < 3:
        return float("nan")
    return float(np.corrcoef(x[mask], y[mask])[0, 1])


def save_plot(path: Path, fig) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def make_plots(out: Path, arrays: Dict[str, np.ndarray], peaks: np.ndarray, cycles: List[Dict[str, float]], wall_fit: Dict[str, float], tick_fit: Dict[str, float], signal_name: str) -> None:
    tick = arrays["tick"]
    wall = arrays["wall_s"]
    y = arrays["signal"]

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(tick, y, linewidth=1)
    if len(peaks):
        ax.scatter(tick[peaks], y[peaks], s=12)
    ax.set_xlabel("tick")
    ax.set_ylabel(signal_name)
    ax.set_title(f"{signal_name} vs tick")
    save_plot(out / f"{signal_name}_vs_tick.png", fig)

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(wall, y, linewidth=1, label="signal")
    if np.isfinite(wall_fit.get("period", float("nan"))):
        p = wall_fit["period"]
        amp = wall_fit["amplitude"]
        phase = wall_fit["phase"]
        off = wall_fit["offset"]
        yhat = off + amp * np.sin(2 * np.pi * wall / p + phase)
        ax.plot(wall, yhat, linewidth=1, label=f"sine fit period={p:.3g}s R2={wall_fit['r2']:.3f}")
    ax.set_xlabel("wall elapsed seconds")
    ax.set_ylabel(signal_name)
    ax.legend(loc="best")
    ax.set_title(f"{signal_name} vs wall time fit")
    save_plot(out / f"{signal_name}_vs_wall_time_fit.png", fig)

    fig, ax = plt.subplots(figsize=(12, 4))
    mask = wall <= min(np.nanmin(wall) + 900, np.nanmax(wall))
    ax.plot(wall[mask], y[mask], linewidth=1)
    ax.set_xlabel("wall elapsed seconds")
    ax.set_ylabel(signal_name)
    ax.set_title(f"{signal_name} first 15 minutes")
    save_plot(out / f"{signal_name}_vs_time_zoom_0_15min.png", fig)

    dt = np.diff(wall)
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(tick[1:], dt, linewidth=1)
    ax.set_xlabel("tick")
    ax.set_ylabel("dt wall seconds")
    ax.set_title("wall-time interval between samples")
    save_plot(out / "tick_dt_vs_tick.png", fig)

    if cycles:
        c_tick = np.array([r["peak1_tick"] for r in cycles])
        periods = np.array([r["period_ticks"] for r in cycles])
        amp = np.array([r["amplitude"] for r in cycles])
        mean_dt = np.array([r["mean_dt_s"] for r in cycles])
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(c_tick, periods, marker="o", linewidth=1)
        ax.set_xlabel("tick at cycle end")
        ax.set_ylabel("inter-peak period ticks")
        ax.set_title("period over time")
        save_plot(out / f"{signal_name}_period_over_time.png", fig)

        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(c_tick, amp, marker="o", linewidth=1)
        ax.set_xlabel("tick at cycle end")
        ax.set_ylabel("cycle max-min amplitude")
        ax.set_title("amplitude over time")
        save_plot(out / f"{signal_name}_amplitude_over_time.png", fig)

        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(mean_dt, periods, s=20)
        ax.set_xlabel("mean seconds per tick in cycle")
        ax.set_ylabel("inter-peak period ticks")
        ax.set_title("period-in-ticks vs mean dt")
        save_plot(out / f"{signal_name}_period_ticks_vs_mean_dt.png", fig)

    if "omega_mean" in arrays:
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(arrays["omega_mean"], y, s=8, alpha=0.75)
        ax.set_xlabel("omega_mean")
        ax.set_ylabel(signal_name)
        ax.set_title(f"{signal_name} vs omega_mean")
        save_plot(out / f"{signal_name}_vs_omega_scatter.png", fig)

    if "a_mean" in arrays:
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(arrays["a_mean"], y, s=8, alpha=0.75)
        ax.set_xlabel("a_mean")
        ax.set_ylabel(signal_name)
        ax.set_title(f"{signal_name} vs a_mean")
        save_plot(out / f"{signal_name}_vs_a_scatter.png", fig)

    for other in ("connectome_entropy", "active_edges", "b1_z", "sie_valence_01"):
        if other in arrays:
            fig, ax = plt.subplots(figsize=(6, 5))
            ax.scatter(arrays[other], y, s=8, alpha=0.75)
            ax.set_xlabel(other)
            ax.set_ylabel(signal_name)
            ax.set_title(f"{signal_name} vs {other}")
            save_plot(out / f"{signal_name}_vs_{other}.png", fig)


def main() -> None:
    ap = argparse.ArgumentParser(description="Scan VDM events for SIE/endogenous periodicity.")
    ap.add_argument("input", type=Path, help="events.jsonl(.gz) or CSV")
    ap.add_argument("--signal", default=None, help="signal field, default: auto SIE-v2 candidate")
    ap.add_argument("--signal-name", default=None, help="name used in output figure filenames")
    ap.add_argument("--hz", type=float, default=None, help="nominal hz only used when no wall timestamps exist")
    ap.add_argument("--out-dir", type=Path, default=Path("periodicity_out"))
    ap.add_argument("--min-distance", type=int, default=5, help="minimum peak distance in samples")
    ap.add_argument("--min-prominence", type=float, default=None, help="peak prominence; default 0.25*std(signal)")
    ap.add_argument("--wall-period-min", type=float, default=10.0)
    ap.add_argument("--wall-period-max", type=float, default=180.0)
    ap.add_argument("--tick-period-min", type=float, default=5.0)
    ap.add_argument("--tick-period-max", type=float, default=120.0)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_table(args.input, args.signal)
    arrays = rows_to_arrays(rows, args.hz)
    signal_name = args.signal_name or args.signal or "sie_v2_valence_01"

    y = arrays["signal"]
    prom = args.min_prominence
    if prom is None:
        prom = max(1e-12, 0.25 * float(np.nanstd(y)))
    peaks = local_maxima(arrays["tick"], y, args.min_distance, prom)
    cycles = cycle_table(arrays["tick"], arrays["wall_s"], y, peaks)

    wall_fit = sine_fit_grid(arrays["wall_s"], y, args.wall_period_min, args.wall_period_max)
    tick_fit = sine_fit_grid(arrays["tick"], y, args.tick_period_min, args.tick_period_max)

    peak_rows = [
        {"peak_index": float(i), "tick": float(arrays["tick"][i]), "wall_s": float(arrays["wall_s"][i]), "signal": float(y[i])}
        for i in peaks
    ]

    write_normalized_csv(args.out_dir / "normalized_tick_table.csv", arrays)
    write_csv(args.out_dir / "peaks.csv", peak_rows)
    write_csv(args.out_dir / "cycles.csv", cycles)
    make_plots(args.out_dir, arrays, peaks, cycles, wall_fit, tick_fit, signal_name)

    dt = np.diff(arrays["wall_s"])
    finite_dt = dt[np.isfinite(dt)]
    summary: Dict[str, Any] = {
        "input": str(args.input),
        "rows": int(len(y)),
        "tick_min": float(np.nanmin(arrays["tick"])),
        "tick_max": float(np.nanmax(arrays["tick"])),
        "wall_s_min": float(np.nanmin(arrays["wall_s"])),
        "wall_s_max": float(np.nanmax(arrays["wall_s"])),
        "signal_name": signal_name,
        "signal_mean": float(np.nanmean(y)),
        "signal_std": float(np.nanstd(y)),
        "signal_min": float(np.nanmin(y)),
        "signal_max": float(np.nanmax(y)),
        "peak_count": int(len(peaks)),
        "wall_sine_fit": wall_fit,
        "tick_sine_fit": tick_fit,
        "dt_summary": {
            "mean": float(np.nanmean(finite_dt)) if len(finite_dt) else float("nan"),
            "median": float(np.nanmedian(finite_dt)) if len(finite_dt) else float("nan"),
            "p95": float(np.nanpercentile(finite_dt, 95)) if len(finite_dt) else float("nan"),
            "p99": float(np.nanpercentile(finite_dt, 99)) if len(finite_dt) else float("nan"),
            "max": float(np.nanmax(finite_dt)) if len(finite_dt) else float("nan"),
            "n_gt_10s": int(np.sum(finite_dt > 10.0)) if len(finite_dt) else 0,
        },
        "cycle_summary": {},
        "correlations": {},
    }
    if cycles:
        for key in ("period_ticks", "period_wall_s", "amplitude", "mean_dt_s"):
            v = np.array([r[key] for r in cycles], dtype=float)
            summary["cycle_summary"][key] = {
                "mean": float(np.nanmean(v)),
                "median": float(np.nanmedian(v)),
                "min": float(np.nanmin(v)),
                "max": float(np.nanmax(v)),
            }
        summary["correlations"]["period_ticks_vs_mean_dt_s"] = corr(
            np.array([r["period_ticks"] for r in cycles], dtype=float),
            np.array([r["mean_dt_s"] for r in cycles], dtype=float),
        )
    for other in ("omega_mean", "a_mean", "connectome_entropy", "active_edges", "b1_z", "sie_valence_01"):
        if other in arrays:
            summary["correlations"][f"{signal_name}_vs_{other}"] = corr(y, arrays[other])

    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
