#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-/mnt/data/vdm_sentence_shift_bursted_1k}"
RUN_DIR="${2:-$ROOT/runs/sentence_shift_bursted_1k_1200}"
BURST="${BURST:-100}"
TOTAL="${TOTAL:-1200}"
REPO="$ROOT/codebase/vdm_rt-main"
TOOLS="$ROOT/codebase/orthad_tools/run_orthad_selector_trace.py"
SCHEDULE="$ROOT/data/sentence_schedule.jsonl"
mkdir -p "$RUN_DIR"
resume=""
start=0
while [ "$start" -lt "$TOTAL" ]; do
  end=$((start + BURST))
  if [ "$end" -gt "$TOTAL" ]; then end="$TOTAL"; fi
  echo "== burst $start -> $end =="
  args=(python "$ROOT/scripts/run_sentence_shift_burst_once.py" --repo "$REPO" --tools "$TOOLS" --schedule "$SCHEDULE" --run-dir "$RUN_DIR" --start-tick "$start" --end-tick "$end" --neurons 1000 --walkers 1200 --hops 2 --threshold 0.05 --stim-amp 0.05 --release-threshold 1.15)
  if [ -n "$resume" ]; then args+=(--resume-h5 "$resume"); fi
  "${args[@]}"
  resume="$RUN_DIR/state_${end}.h5"
  start="$end"
done
