#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-venv/bin/python}"
if [[ ! -x "$PY" ]]; then
  echo "Missing $PY. Run ./setup_env.sh first, or set PYTHON=/path/to/python." >&2
  exit 2
fi
"$PY" tools/run_whole_anti_reafference_suite.py --reset --run \
  --suite-dir runs/anti_reafference_whole_1500 \
  --ticks-total 1500 \
  --switch-tick 1000
