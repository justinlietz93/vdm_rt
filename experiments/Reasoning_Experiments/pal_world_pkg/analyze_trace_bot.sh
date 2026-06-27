#!/usr/bin/env bash
set -euo pipefail
SUITE_DIR="${1:-runs/trace_bot_graph_1500}"
venv/bin/python tools/run_trace_conditioned_bot_suite.py \
  --analyze \
  --suite-dir "$SUITE_DIR"
