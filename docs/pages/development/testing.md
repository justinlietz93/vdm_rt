---
title: Testing
status: active
owner: runtime-core
source_authority: tests/
summary: Current and future tests for runtime and docs quality.
---


# Testing

## Runtime tests

Run from the parent directory:

```bash
PYTHONPATH=. pytest -q vdm_rt/tests
```

## Smoke run

```bash
PYTHONPATH=. python -m vdm_rt.run_nexus   --neurons 32   --k 4   --hz 5   --duration 1   --run-dir /tmp/vdm_rt_smoke
```

## Runtime before/after comparison

For runtime-affecting edits, keep the launch command fixed, write two run
directories, then compare compressed artifacts:

```bash
PYTHONPATH=. python -m tools.runtime.compare_runs /tmp/vdm_rt_before /tmp/vdm_rt_after
```

The comparator ignores external clock fields by default and reports row counts,
matched tick records, field additions/removals, and metric differences. Treat
this as smoke/parity evidence, not final model-quality validation.

## Docs tests

```bash
python vdm_rt/docs/governance/tools/check_docs_front_matter.py
```

## Test additions required for motor-learning upgrade

- live output path cannot import lexical authoring,
- basis unchanged after novel input,
- renderer does not repair partial traces,
- gate changes timing only,
- action consequence returns through receptor feedback,
- multiple actuator traces may render the same witness without trace identity collapse.
