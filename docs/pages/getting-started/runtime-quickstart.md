---
title: Runtime Quickstart
status: active
owner: runtime-core
source_authority: README.md
summary: Minimal commands for running the headless runtime.
---


# Runtime Quickstart

From the parent directory of this repository:

```bash
pip install -r vdm_rt/requirements.txt
PYTHONPATH=. python -m vdm_rt.run_nexus --neurons 800 --hz 10 --duration 10
```

Small smoke run:

```bash
PYTHONPATH=. python -m vdm_rt.run_nexus   --neurons 32   --k 4   --hz 5   --duration 1   --run-dir /tmp/vdm_rt_smoke
```

Run retained tests:

```bash
PYTHONPATH=. pytest -q vdm_rt/tests
```

## Expected outputs

A run directory contains structured runtime artifacts such as:

```text
events.jsonl
utd_events.jsonl
phase.json
state_<step>.h5
```

These artifacts are the present headless control surface. A future frontend should read stable status/run artifacts or a control API. It should not own runtime launch, filesystem mutation, log tailing, or engine control.
