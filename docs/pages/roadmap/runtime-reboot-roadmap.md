---
title: Runtime Reboot Roadmap
status: active
owner: runtime-core
source_authority: reports/20260622/vdm_rt_void_bus_adc_loop_analysis.md
summary: Implementation roadmap for the event spine, ADC territory richness, scan reduction, cleanup guardrails, and sparse neurogenesis work.
---

# Runtime Reboot Roadmap

This roadmap translates `reports/20260622/vdm_rt_void_bus_adc_loop_analysis.md` into buildable implementation tracks.

The current runtime is halfway through a good migration: from scan-heavy global metrics toward event-fed local reducers. The next work is to make that migration explicit.

## Build order

| Order | Roadmap | Purpose |
|---:|---|---|
| 1 | `docs/roadmap/runtime-cleanup-guardrails/TODO.md` | Protect the fresh repo from frontend, visualization, torch, GPU, dense-substrate, and ML-training contamination. |
| 2 | `docs/roadmap/runtime-event-spine/TODO.md` | Unify `Observation`, `BaseEvent`, ADC, maps, memory, and future motor events behind one typed event spine. |
| 3 | `docs/roadmap/adc-territory-richness/TODO.md` | Feed ADC more than `region_stat` and `cycle_hit`; produce `boundary_probe` and `novel_frontier`. |
| 4 | `docs/roadmap/scout-map-ownership/TODO.md` | Keep void walkers/maps as core systems, remove duplicate scout ownership, and route scout products globally. |
| 5 | `docs/roadmap/memory-gdsp-territory/TODO.md` | Fix memory ownership, stale observation reuse, GDSP one-tick territory lag, dead `bias_hint` shape, and engram resume integrity. |
| 6 | `docs/roadmap/loop-scan-reduction/TODO.md` | Replace repeated full graph scans with sparse cached snapshots and reducer-fed metrics. |
| 7 | `docs/roadmap/sparse-neurogenesis/TODO.md` | Recover dynamic node growth/culling as sparse-native runtime code without torch or dense substrate ownership. |
| 8 | `docs/roadmap/repo-scan-upgrades/TODO.md` | Add scanners for bus schema, hot loops, state ownership, tick order, and contamination policies. |
| 9 | `docs/roadmap/motor-learning-system/TODO.md` | Build motor-learning only after the event spine and territory systems are coherent. |

## Hard dependencies

Motor-learning work depends on three runtime tracks:

1. The event spine must exist before actuator trace, release, and reafference events can be globally routed.
2. ADC territory richness must improve before motor skill can use territory/correction feedback with useful locality.
3. Engram resume integrity must be proven before long-run motor learning claims can rely on stopped/reloaded state.
4. Dense-scan reduction must begin before new motor systems add more per-tick load.

## Runtime stance

```text
Keep:
  SparseConnectome
  void walkers
  void maps
  ADC
  SIE
  GDSP/REVGSP
  headless runtime
  event spine

Port:
  legacy dynamic neuron growth/culling intent

Archive:
  old dense/GPU substrate implementation as design source

Delete:
  frontend/UI/visualization/GPU/dense/research-output residue
```

## Exit condition

This roadmap is complete when:

- the headless runtime has a typed event spine,
- ADC receives rich territory-producing events,
- void walkers/maps are globally visible and not duplicate-owned,
- GDSP reads current territory data or explicitly declares next-tick scheduling,
- engram resume restores real state history or fails loudly instead of silently loading config-only state,
- repeated scan-heavy metrics are replaced by cached sparse snapshots where safe,
- torch/dense substrate paths are gone from live runtime,
- sparse neurogenesis has an implementation plan and first bounded policy tests,
- and motor-learning work has a stable runtime substrate to build on.
