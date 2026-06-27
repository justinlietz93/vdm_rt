#!/usr/bin/env bash
set -euo pipefail
python tools/run_clean_anti_reafference_suite.py \
  --suite-dir runs/anti_reafference_clean_1500 \
  --repo codebase/vdm_rt-main \
  --intent-index-dir index \
  --next-burst
