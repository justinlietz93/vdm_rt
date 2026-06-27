#!/usr/bin/env bash
set -euo pipefail
REPO="${1:-$HOME/git/vdm_rt}"
venv/bin/python tools/run_trace_conditioned_bot_suite.py \
  --reset \
  --run \
  --repo "$REPO" \
  --suite-dir runs/trace_bot_social_3000 \
  --ticks-total 3000 \
  --switch-tick 2000 \
  --tick-print-stride 50 \
  --live-topn 2
