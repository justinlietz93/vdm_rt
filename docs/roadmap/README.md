# VDM RT Roadmap Index

Status: active draft.

This folder contains implementation checklists for the independent `vdm_rt` reboot. Each roadmap uses the same structure:

```text
Phase
  Task
    Step
```

The source report for the current runtime cleanup wave is:

```text
reports/20260622/vdm_rt_void_bus_adc_loop_analysis.md
```

## Roadmap order

1. `runtime-cleanup-guardrails/TODO.md` — protect the fresh repo identity.
2. `runtime-event-spine/TODO.md` — unify observations, BaseEvents, ADC, maps, memory, and motor events.
3. `adc-territory-richness/TODO.md` — make ADC territory and boundary production meaningful.
4. `scout-map-ownership/TODO.md` — make void walkers/maps first-class producers and remove duplicate ownership.
5. `loop-scan-reduction/TODO.md` — replace repeated graph scans with cached sparse snapshots and reducer-fed metrics.
6. `memory-gdsp-territory/TODO.md` — fix memory ownership, GDSP timing, stale observations, territory availability, and engram resume integrity.
7. `sparse-neurogenesis/TODO.md` — preserve legacy growth/pruning intent while removing dense/GPU substrate code.
8. `repo-scan-upgrades/TODO.md` — improve Arachnid/repo-scan tooling for runtime dataflow analysis.
9. `motor-learning-system/TODO.md` — motor-learning / decoder-removal upgrade path.

## Policy

The roadmap is not a wishlist. Every item must either:

- preserve a live runtime invariant,
- remove contamination from the reboot repo,
- route a real signal into the event spine,
- replace dense scanning with bounded sparse/event-fed behavior,
- recover an important dormant capability as sparse-native runtime code,
- or create a gate that prevents regression.
