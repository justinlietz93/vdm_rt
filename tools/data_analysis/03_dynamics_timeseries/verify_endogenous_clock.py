#!/usr/bin/env python3
"""Regenerate endogenous-clock evidence tables from runtime tick artifacts.

Inputs may be a run directory, an events JSONL/JSONL.ZST file, or a CSV/CSV.GZ
tick table. This is offline analysis only; it does not change runtime timing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from endogenous_clock_io import DEFAULT_EPOCH_BOUNDARIES, DEFAULT_PREFIX, load_tick_rows
from endogenous_clock_metrics import write_outputs


def parse_epoch_boundaries(value: str) -> tuple[int, int]:
    parts = [p.strip() for p in value.split(",") if p.strip()]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("expected two comma-separated ticks, e.g. 10500,11600")
    left, right = int(parts[0]), int(parts[1])
    if right <= left:
        raise argparse.ArgumentTypeError("second epoch boundary must be greater than first")
    return left, right


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Run directory, events JSONL(.zst), or tick CSV(.gz)")
    parser.add_argument("--out-dir", required=True, type=Path, help="Output directory for regenerated evidence")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--dt-max-s", type=float, default=120.0)
    parser.add_argument("--epoch-boundaries", type=parse_epoch_boundaries, default=DEFAULT_EPOCH_BOUNDARIES)
    parser.add_argument("--min-period-s", type=float, default=5.0)
    parser.add_argument("--max-period-s", type=float, default=300.0)
    parser.add_argument("--min-period-ticks", type=float, default=5.0)
    parser.add_argument("--max-period-ticks", type=float, default=200.0)
    parser.add_argument("--min-peak-distance", type=int, default=3)
    parser.add_argument("--window-size", type=int, default=128)
    parser.add_argument("--window-step", type=int, default=64)
    args = parser.parse_args(argv)

    rows = load_tick_rows(args.input)
    if len(rows) < 3:
        raise RuntimeError(f"Need at least 3 tick rows, got {len(rows)}")
    paths = write_outputs(
        rows,
        args.out_dir,
        prefix=args.prefix,
        dt_max_s=args.dt_max_s,
        epoch_boundaries=args.epoch_boundaries,
        min_period_s=args.min_period_s,
        max_period_s=args.max_period_s,
        min_period_ticks=args.min_period_ticks,
        max_period_ticks=args.max_period_ticks,
        min_peak_distance=max(1, args.min_peak_distance),
        window_size=max(8, args.window_size),
        window_step=max(1, args.window_step),
    )
    print(f"Loaded {len(rows)} tick rows")
    for path in paths.values():
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
