---
title: Runtime Boundaries
status: active
owner: runtime-core
source_authority: docs/contracts/runtime-boundary-policy.yml
summary: Preserved runtime layers and forbidden contamination paths.
---


# Runtime Boundaries

## Current retained layers

```text
core      numeric/state machinery, SIE, sparse connectome, maps, scouts, memory, signals
runtime   loop orchestration, per-tick helpers, telemetry, checkpoint/status emission
io        receptor/effector boundary ports and logging
control   headless process boundary for future clients
frontend  removed
```

## Hard boundary

External stays external. Internal stays internal. Everything crosses only through the corresponding interface.

That means:

- `core` must not import frontend, Dash, visualization, hardware transport, or direct UI code.
- `runtime` may orchestrate core and io, but should not become a renderer, phrase composer, or frontend.
- `io` may transduce between runtime and external media, but must not hide persistence pockets or author cognition.
- `control` may launch and manage runtime processes, but must not decide model cognition.

## Removed contamination paths

```text
old Dash frontend
old visualization/WebSocket path
old physics/cosmology harness
old generated scan reports
old data/corpus clutter
old no-op viz flags
```

## Preserved unobvious systems

The following systems have current runtime execution:

- `core/sie.py`
- `core/sie_v2.py`
- `core/cortex/void_walkers/`
- `core/cortex/maps/`

`SparseConnectome` is the sole live runtime substrate. The former
`core/substrate/` package has moved to
`docs/sources/legacy-substrate-neurogenesis/`; it is not a second runtime
substrate. Its dynamic-population requirements are preserved for the
sparse-neurogenesis port, not by retaining its implementation.

`core/growth_arbiter.py` and `core/structural_homeostasis.py` are retained as
capability sources, not attested as active default-runtime behavior.
`core/void_b1.py` owns the live `StreamingZEMA` B1Z detector and also preserves
the planned Void B1 topology-packet surface; that packet is not default-runtime
telemetry until its sparse behavior and bounded cost are tested. The old CSR
plasticity adapters and dense diagnostics were removed; future structural
plasticity and diagnostics must be SparseConnectome-native. Exact status and
required ports are in `docs/contracts/runtime-capability-coverage.yml`.

Do not delete a module only because it appears orphaned in a static graph.
Record the static evidence, identify the capability owner, and classify the
source as `keep`, `port`, `archive`, or `delete` first. Static disconnection
does not authorize deletion: every carried goal must also be classified as
covered, partial, unwired, unmet, or intentionally retired. The current
classification is `docs/contracts/runtime-cleanup-classification.yml`; the
coverage contract is `docs/contracts/runtime-capability-coverage.yml`.

## Future boundary checks

The next guard layer should test:

- no frontend package exists,
- no `dash` dependency exists,
- no live decoder path imports phrase/lexicon authoring,
- no renderer can complete or repair content,
- no input-history-grown actuator basis,
- no hidden wall-clock cognitive driver.
