---
title: VDM RT Documentation
status: active
owner: runtime-core
source_authority: docs/README.md
summary: Current documentation map for the independent headless VDM runtime.
---


# VDM RT Documentation

VDM RT is now a clean, independent, headless runtime repository. The old frontend, visualization adapter, physics harness, and generated scan clutter have been removed so the runtime can receive the neurobiology/motor-learning upgrade without fighting the old UI shape.

## Current purpose

```text
preserve the runtime engine
remove live decoder authorship
replace output with actuator-manifold control
return action consequences through receptor feedback
measure skill development without ML training
```

## Reader route

| Need | Go to |
|---|---|
| Run the repo | [Runtime quickstart](getting-started/runtime-quickstart.md) |
| Understand preserved boundaries | [Runtime boundaries](architecture/runtime-boundaries.md) |
| Understand why the upgrade is urgent | [Neurobiology upgrade](architecture/neurobiology-upgrade.md) |
| Understand the target motor-learning system | [Motor-learning system](architecture/motor-learning-system.md) |
| Follow build phases | [Motor-learning roadmap](roadmap/motor-learning-roadmap.md) |
| Inspect hard rules | [Runtime invariants](reference/runtime-invariants.md) |
| Read evidence summary | [Aura distinction summary](evidence/aura-distinction-summary.md) |

## Current repo stance

The repo is not trying to improve the old decoder. The old decoder is treated as the wrong class of solution for live output. The target is a motor-learning path where output is formed as actuator trace, released through endogenous dynamics, rendered as witness, and sensed back through UTE.
