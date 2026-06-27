#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-/mnt/data/vdm_sentence_shift_bursted_1k}"
OUT="${2:-$ROOT/runs/sentence_shift_bursted_1k_1200_isolated}"
BURST="${BURST:-20}"
TOTAL="${TOTAL:-1200}"
TIMEOUT="${TIMEOUT:-40}"
REPO="$ROOT/codebase/vdm_rt-main"
TOOLS="$ROOT/codebase/orthad_tools/run_orthad_selector_trace.py"
SCHEDULE="$ROOT/data/sentence_schedule.jsonl"
WORK="$OUT/bursts"
mkdir -p "$WORK"
resume=""
for start in $(seq 0 "$BURST" $((TOTAL-BURST))); do
  end=$((start + BURST)); [ "$end" -gt "$TOTAL" ] && end="$TOTAL"
  ok=0
  for attempt in 1 2 3; do
    D="$WORK/burst_${start}_${end}_a${attempt}"
    rm -rf "$D"; mkdir -p "$D"
    args=(python "$ROOT/scripts/run_sentence_shift_burst_once.py" --repo "$REPO" --tools "$TOOLS" --schedule "$SCHEDULE" --run-dir "$D" --start-tick "$start" --end-tick "$end" --neurons 1000 --walkers 1200 --hops 2 --threshold 0.05 --stim-amp 0.05 --release-threshold 1.15)
    if [ -n "$resume" ]; then args+=(--resume-h5 "$resume"); fi
    echo "== burst $start -> $end attempt $attempt ==" | tee -a "$OUT/driver.log"
    if timeout "$TIMEOUT" "${args[@]}" >> "$OUT/driver.log" 2>> "$OUT/driver.err"; then
      if [ -f "$D/state_${end}.h5" ]; then
        resume="$D/state_${end}.h5"; ok=1; break
      fi
    fi
  done
  if [ "$ok" != "1" ]; then echo "FAILED burst $start $end" >&2; exit 1; fi
done
python "$ROOT/scripts/collate_bursts.py" "$WORK" "$OUT"
