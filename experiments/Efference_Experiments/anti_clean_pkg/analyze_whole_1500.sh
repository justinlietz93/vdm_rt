#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-venv/bin/python}"
"$PY" tools/run_whole_anti_reafference_suite.py --analyze \
  --suite-dir runs/anti_reafference_whole_1500
