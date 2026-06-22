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
io        receptor/effector adapters, cognition adapters, lexicon storage, logging
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

The repo intentionally retains multiple SIE/substrate-adjacent systems because they have different roles:

- `core/fum_sie.py`
- `core/sie_v2.py`
- `core/fum_growth_arbiter.py`
- `core/fum_structural_homeostasis.py`
- `core/substrate/`
- `core/neuroplasticity/`
- `core/cortex/void_walkers/`
- `core/cortex/maps/`

Do not delete a module only because it looks orphaned in a static graph. The runtime has feature-gated seams, reference implementations, and domain-specific variants that may not show as direct imports in a short run.

## Future boundary checks

The next guard layer should test:

- no frontend package exists,
- no `dash` dependency exists,
- no live decoder path imports phrase/lexicon authoring,
- no renderer can complete or repair content,
- no input-history-grown actuator basis,
- no hidden wall-clock cognitive driver.
