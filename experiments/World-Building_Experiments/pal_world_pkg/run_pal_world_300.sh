#!/usr/bin/env bash
set -euo pipefail
REPO="${1:-${VDM_REPO:-codebase/vdm_rt-main}}"
OUT="${2:-runs/pal_world_300}"
python tools/run_trace_conditioned_bot_suite_core.py --suite-dir "$OUT" --repo "$REPO" --intent-index-dir index --reset --init --ticks-total 300 --burst-ticks 300 --tick-print-stride 10
python tools/run_trace_conditioned_bot_suite_core.py --suite-dir "$OUT" --run-all
