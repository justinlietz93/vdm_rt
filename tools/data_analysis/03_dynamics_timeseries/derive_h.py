#!/usr/bin/env python3
"""Derive H-like scalar diagnostics from VDM tick tables.

This is offline analysis only. It accepts CSV or CSV.GZ tick tables and streams
rows without loading the full file.

Example:
    python tools/data_analysis/03_dynamics_timeseries/derive_h.py \
        --input tables/tick_table_full.csv.gz \
        --output tables/derived_h.csv

Output columns:
    source_file, t, ts
    H              total synaptic energy proxy: avg_weight * active_synapses
    H_topo         H with topology correction: H + b1 * topo_scale
    S              connectome entropy
    F              free-energy proxy: H - S
    vt_S           virtual-territory entropy
    omega          mean dissipative rate proxy
    a              mean activation proxy
    diss_frac      abs(omega) / (abs(omega) + abs(a))
    b1, b1_z       topology signal and streaming z score
    td_signal      temporal-difference signal
    sie_reward     SIE reward, preferring SIE v2 when present
    sie_valence    SIE v2 valence when present
    active_synapses, active_edges, vt_coverage
    ute_in_count, ute_text_count

The legacy ``did_say`` field is intentionally not derived here. Current live
runtime output is a motor-trace boundary, not a text/say decoder path.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import math
import sys
import time
from pathlib import Path
from typing import Iterator, Optional


# Column definitions

REQUIRED = {'avg_weight', 'active_synapses', 'connectome_entropy'}
OPTIONAL = {
    'b1_value', 'b1_z', 'omega_mean', 'a_mean',
    'vt_entropy', 'vt_coverage',
    'active_edges', 'td_signal',
    'sie_total_reward', 'sie_v2_reward_mean', 'sie_v2_valence_01',
    'ute_in_count', 'ute_text_count',
    'complexity_cycles',
}

OUTPUT_COLS = [
    'source_file', 't', 'ts',
    'H', 'H_topo', 'S', 'F', 'vt_S',
    'omega', 'a', 'diss_frac',
    'b1', 'b1_z', 'td_signal',
    'sie_reward', 'sie_valence',
    'active_synapses', 'active_edges', 'vt_coverage',
    'ute_in_count', 'ute_text_count',
]

TOPO_SCALE = 0.01


# Helpers

def _f(row: dict, col: str, default: float = float('nan')) -> float:
    v = row.get(col, '')
    if v in ('', 'nan', 'None', 'null', None):
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _open(path: Path):
    """Open plain or gzipped file."""
    if path.suffix == '.gz':
        return gzip.open(path, 'rt', encoding='utf-8', errors='replace')
    return open(path, 'r', encoding='utf-8', errors='replace')


def derive_row(row: dict, source: str) -> Optional[dict]:
    """
    Compute H and thermodynamic quantities for one tick row.
    Returns None if the row is not a tick (e.g. header, log lines).
    """
    # Accept rows that have at minimum avg_weight + active_synapses
    w = _f(row, 'avg_weight')
    N = _f(row, 'active_synapses')
    if math.isnan(w) or math.isnan(N) or N <= 0:
        return None

    S     = _f(row, 'connectome_entropy')
    b1    = _f(row, 'b1_value',  _f(row, 'complexity_cycles', 0.0))
    b1_z  = _f(row, 'b1_z',     float('nan'))
    omega = _f(row, 'omega_mean', float('nan'))
    a     = _f(row, 'a_mean',    float('nan'))
    vt_S  = _f(row, 'vt_entropy', float('nan'))
    E     = _f(row, 'active_edges', N)   # fallback to active_synapses

    H      = w * N
    H_topo = H + (b1 * TOPO_SCALE if not math.isnan(b1) else 0.0)
    F      = (H - S) if not math.isnan(S) else float('nan')

    # Dissipative fraction: how much of the scalar dynamics is omega-dominant.
    if not (math.isnan(omega) or math.isnan(a)):
        diss_frac = abs(omega) / (abs(omega) + abs(a) + 1e-30)
    else:
        diss_frac = float('nan')

    ute_in   = int(_f(row, 'ute_in_count',   0))
    ute_text = int(_f(row, 'ute_text_count',  0))

    return {
        'source_file':    source,
        't':              row.get('t', ''),
        'ts':             row.get('ts', ''),
        'H':              round(H, 6),
        'H_topo':         round(H_topo, 6),
        'S':              round(S, 6) if not math.isnan(S) else '',
        'F':              round(F, 6) if not math.isnan(F) else '',
        'vt_S':           round(vt_S, 6) if not math.isnan(vt_S) else '',
        'omega':          round(omega, 6) if not math.isnan(omega) else '',
        'a':              round(a, 6) if not math.isnan(a) else '',
        'diss_frac':      round(diss_frac, 6) if not math.isnan(diss_frac) else '',
        'b1':             int(b1) if not math.isnan(b1) else '',
        'b1_z':           round(b1_z, 4) if not math.isnan(b1_z) else '',
        'td_signal':      round(_f(row,'td_signal'), 6),
        'sie_reward':     round(_f(row,'sie_v2_reward_mean',
                                  _f(row,'sie_total_reward')), 6),
        'sie_valence':    round(_f(row,'sie_v2_valence_01'), 6),
        'active_synapses':int(N),
        'active_edges':   int(E),
        'vt_coverage':    round(_f(row,'vt_coverage'), 4),
        'ute_in_count':   ute_in,
        'ute_text_count': ute_text,
    }


def stream_csv(path: Path) -> Iterator[dict]:
    """Stream rows from a CSV (or gzipped CSV). Skip non-tick rows."""
    with _open(path) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # Accept tick rows only (filter out log preamble lines)
            if row.get('msg', '').strip() not in ('', 'tick'):
                # some files have msg='tick'; others just have numeric rows
                if not any(row.get(c, '') not in ('', None)
                           for c in ('avg_weight', 'active_synapses')):
                    continue
            yield row


def process_file(
    path: Path,
    writer: csv.DictWriter,
    verbose: bool = True,
) -> tuple[int, int]:
    """Process a single log file. Returns (rows_read, rows_written)."""
    source = path.name
    n_read = n_written = 0
    for row in stream_csv(path):
        n_read += 1
        out = derive_row(row, source)
        if out is not None:
            writer.writerow(out)
            n_written += 1
    if verbose:
        print(f"  {source}: {n_read} rows read -> {n_written} ticks written")
    return n_read, n_written


def run(
    inputs: list[Path],
    output: Path,
    verbose: bool = True,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    total_read = total_written = 0

    with open(output, 'w', newline='', encoding='utf-8') as fout:
        writer = csv.DictWriter(fout, fieldnames=OUTPUT_COLS, extrasaction='ignore')
        writer.writeheader()

        for path in inputs:
            if not path.exists():
                print(f"  SKIP (not found): {path}", file=sys.stderr)
                continue
            nr, nw = process_file(path, writer, verbose=verbose)
            total_read   += nr
            total_written += nw

    elapsed = time.time() - t0
    size_mb = output.stat().st_size / 1e6
    print(f"\nDone: {total_read} rows read -> {total_written} ticks")
    print(f"Output: {output}  ({size_mb:.1f} MB)")
    print(f"Time: {elapsed:.1f}s  ({total_read/max(elapsed,0.1):.0f} rows/s)")


# CLI

def main():
    ap = argparse.ArgumentParser(description="Derive H-like scalars from VDM tick tables")
    ap.add_argument('--input', nargs='+', required=True,
                    help="Input CSV/TSV/gz files or glob patterns")
    ap.add_argument('--output', default='derived_H.csv',
                    help="Output CSV path (default: derived_H.csv)")
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    # Expand globs
    import glob as _glob
    paths: list[Path] = []
    for pattern in args.input:
        expanded = _glob.glob(pattern, recursive=True)
        if expanded:
            paths.extend(Path(p) for p in sorted(expanded))
        else:
            paths.append(Path(pattern))

    if not paths:
        print("No input files found.", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(paths)} file(s) -> {args.output}")
    run(paths, Path(args.output), verbose=not args.quiet)


if __name__ == '__main__':
    main()
