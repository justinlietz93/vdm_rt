#!/usr/bin/env bash
set -euo pipefail
SUITE_DIR="${1:-runs/trace_conditioned_bot_3000}"
venv/bin/python tools/run_trace_conditioned_bot_suite.py \
  --analyze \
  --suite-dir "$SUITE_DIR"
