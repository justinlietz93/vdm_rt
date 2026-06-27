# VDM RT working repo + Orthad sensorimotor runner

This package contains the working VDM repo copy used for the Orthad sensorimotor tests in this chat, plus the logged runner.

## Contents

- `vdm_rt-main/` — working VDM runtime repo copy used by the test harness.
- `orthad_tools/run_orthad_sensorimotor_logged.py` — logged Orthad sensorimotor runner.

## Run from inside the repo

```bash
cd vdm_rt-main
python ../orthad_tools/run_orthad_sensorimotor_logged.py \
  --repo . \
  --run-dir runs/orthad_sensorimotor_logged_v3_1k \
  --neurons 1000 \
  --walkers 1200 \
  --ticks 260 \
  --threshold 40 \
  --mode sensorimotor
```

## External-only comparison

```bash
cd vdm_rt-main
python ../orthad_tools/run_orthad_sensorimotor_logged.py \
  --repo . \
  --run-dir runs/orthad_external_only_logged_v3_1k \
  --neurons 1000 \
  --walkers 1200 \
  --ticks 260 \
  --threshold 40 \
  --mode external_only
```

## Stricter motor mouth

```bash
cd vdm_rt-main
python ../orthad_tools/run_orthad_sensorimotor_logged.py \
  --repo . \
  --run-dir runs/orthad_sensorimotor_logged_v3_1k_thr80 \
  --neurons 1000 \
  --walkers 1200 \
  --ticks 260 \
  --threshold 80 \
  --mode sensorimotor
```

## Main output files

Each run folder writes:

- `tick_rows.csv`
- `io_timeline_slim.csv`
- `ute_input_stream.jsonl`
- `utd_motor_events.jsonl`
- `bin50_summary.csv`
- `category_summary.csv`
- `source_summary.csv`
- `run_summary.json`
- `state_<tick>.h5` checkpoints

