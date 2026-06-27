#!/usr/bin/env bash
set -euo pipefail
REPO="${1:-$(pwd)}"
venv/bin/python tools/run_trace_conditioned_bot_suite.py \
  --reset \
  --run \
  --repo "$REPO" \
  --suite-dir runs/trace_conditioned_bot_5000 \
  --ticks-total 5000 \
  --switch-tick 3500 \
  --tick-print-stride 10 \
  --live-topn 5
