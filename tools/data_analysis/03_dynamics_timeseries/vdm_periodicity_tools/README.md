# VDM Periodicity / Endogenous-vs-Wall Clock Analysis Scripts

These are analysis-only scripts. They do **not** patch the runtime.

They reconstruct the scripts used for the periodicity investigation:

- SIE-v2 amplitude and period over time
- SIE-v2 vs tick
- SIE-v2 vs wall time fit
- SIE-v2 vs omega/a phase portrait
- tick `dt` vs tick
- wall-time vs model-time/tick-time null tests
- static timing touchpoint audit

## 1. Periodicity scan

```bash
python scripts/sie_periodicity_scan.py /path/to/events.jsonl.zst \
  --signal sie_v2_valence_01 \
  --out-dir analysis/sie_periodicity
```

If your log has no wall timestamp/elapsed field, pass the nominal rate:

```bash
python scripts/sie_periodicity_scan.py /path/to/events.jsonl.zst \
  --signal sie_v2_valence_01 \
  --hz 10 \
  --out-dir analysis/sie_periodicity
```

Outputs:

- `summary.json`
- `normalized_tick_table.csv`
- `peaks.csv`
- `cycles.csv`
- `sie_v2_valence_01_vs_tick.png`
- `sie_v2_valence_01_vs_wall_time_fit.png`
- `sie_v2_valence_01_vs_time_zoom_0_15min.png`
- `sie_v2_valence_01_period_over_time.png`
- `sie_v2_valence_01_amplitude_over_time.png`
- `sie_v2_valence_01_vs_omega_scatter.png` if `omega_mean` exists
- `tick_dt_vs_tick.png`

## 2. Wall-clock / endogenous-clock nulls

```bash
PYTHONPATH=scripts python scripts/clock_alignment_nulls.py /path/to/events.jsonl.zst \
  --signal sie_v2_valence_01 \
  --hz 10 \
  --out analysis/clock_nulls_summary.json
```

This compares:

- fit against actual wall time
- fit against model time, `tick / hz`
- fit against tick index
- fit against constant-dt reconstruction
- shuffled-dt null distribution
- peak phase concentration against wall/model fits

## 3. Static timing touchpoint audit

```bash
python scripts/runtime_timing_audit.py /path/to/VDM_Runtime_Legacy \
  --json analysis/timing_audit.json \
  --markdown analysis/timing_audit.md
```

This does not declare guilt. It lists every timing touchpoint so you can inspect whether anything in the cognitive update path is consuming wall time.

## Notes

- These scripts are deliberately dependency-light: Python 3, NumPy, Matplotlib, and zstandard for `.zst` inputs.
- They accept `.jsonl`, `.jsonl.gz`, `.jsonl.zst`, `.csv`, and `.csv.gz`.
- They are robust to flat event rows and simple nested rows like `metrics`, `why`, `state`, `connectome`, or `telemetry`.
- They do not import the runtime.
- They do not change runtime behavior.
