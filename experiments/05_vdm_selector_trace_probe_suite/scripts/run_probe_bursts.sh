#!/usr/bin/env bash
set -euo pipefail
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN="$BASE/runs/semantic_probe_1k_1400_thr05"
mkdir -p "$RUN"
REPO="$BASE/codebase/vdm_rt-main"
TOOLS="$BASE/codebase/orthad_tools/run_orthad_selector_trace.py"
SCHED="$BASE/data/probe_schedule.jsonl"
SCRIPT="$BASE/scripts/run_selector_probe_burst_once.py"
# 100-tick bursts through 1100, then 20-tick bursts. This avoids long-process slowdown.
for start in 0 100 200 300 400 500 600 700 800 900 1000; do
  end=$((start+100))
  if [[ "$start" == 0 ]]; then
    python3 "$SCRIPT" --repo "$REPO" --tools "$TOOLS" --schedule "$SCHED" --run-dir "$RUN" --start-tick "$start" --end-tick "$end" --neurons 1000 --walkers 1200 --hops 2 --threshold 0.05 --release-threshold 0.5 --seed 20260627
  else
    python3 "$SCRIPT" --repo "$REPO" --tools "$TOOLS" --schedule "$SCHED" --run-dir "$RUN" --start-tick "$start" --end-tick "$end" --resume-h5 "$RUN/state_${start}.h5" --neurons 1000 --walkers 1200 --hops 2 --threshold 0.05 --release-threshold 0.5 --seed 20260627
  fi
done
for start in 1100 1120 1140 1160 1180 1200 1220 1240 1260 1280 1300 1320 1340 1360 1380; do
  end=$((start+20))
  python3 "$SCRIPT" --repo "$REPO" --tools "$TOOLS" --schedule "$SCHED" --run-dir "$RUN" --start-tick "$start" --end-tick "$end" --resume-h5 "$RUN/state_${start}.h5" --neurons 1000 --walkers 1200 --hops 2 --threshold 0.05 --release-threshold 0.5 --seed 20260627
done
