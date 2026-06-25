# Runtime Event Spine TODO

Status: active draft.
Source report: `reports/20260622/vdm_rt_void_bus_adc_loop_analysis.md`.

The runtime currently has parallel signal paths: `AnnounceBus`, `Observation`, `BaseEvent`, ADC, `TerritoryUF`, EventDrivenMetrics, maps, memory/trail reducers, and scout events. This roadmap makes the spine explicit.

## Phase 0 — Inventory Existing Event Systems

### Task 0.1 — List producers

- [ ] Step 0.1.1 — Inventory `SparseConnectome._void_traverse()` observation producers.
- [ ] Step 0.1.2 — Inventory runtime scout producers under `core/cortex/void_walkers/`.
- [ ] Step 0.1.3 — Inventory map producers under `core/cortex/maps/`.
- [ ] Step 0.1.4 — Inventory GDSP/REVGSP and SIE outputs that should become spine-visible.
- [ ] Step 0.1.5 — Inventory future motor-learning event needs.

### Task 0.2 — List reducers

- [ ] Step 0.2.1 — Inventory ADC observation consumers.
- [ ] Step 0.2.2 — Inventory `TerritoryUF` consumers.
- [ ] Step 0.2.3 — Inventory EventDrivenMetrics reducers.
- [ ] Step 0.2.4 — Inventory memory/trail/map reducers.
- [ ] Step 0.2.5 — Inventory telemetry/status writers.

## Phase 1 — Define the Spine Contract

### Task 1.1 — Add typed spine module

- [ ] Step 1.1.1 — Add `runtime/loop/event_spine.py`.
- [ ] Step 1.1.2 — Define observation channel for ADC/cartography inputs.
- [ ] Step 1.1.3 — Define event channel for `BaseEvent` and map/motor reducers.
- [ ] Step 1.1.4 — Define counter channel for per-kind published, drained, and dropped counts.
- [ ] Step 1.1.5 — Ensure channels are bounded and deterministic.

### Task 1.2 — Add minimal API

- [ ] Step 1.2.1 — Implement `publish_observation(obs)`.
- [ ] Step 1.2.2 — Implement `publish_event(event)`.
- [ ] Step 1.2.3 — Implement `drain_observations(max_items)`.
- [ ] Step 1.2.4 — Implement `drain_events(max_items)`.
- [ ] Step 1.2.5 — Implement `metrics()` returning per-kind counters.
- [ ] Step 1.2.6 — Add drop accounting for bounded channel overflow.

## Phase 2 — Route Producers Through the Spine

### Task 2.1 — Connect sparse traversal observations

- [ ] Step 2.1.1 — Route `cycle_hit` through the spine observation channel.
- [ ] Step 2.1.2 — Route `region_stat` through the spine observation channel.
- [ ] Step 2.1.3 — Route future `boundary_probe` through the spine observation channel.
- [ ] Step 2.1.4 — Route future `novel_frontier` through the spine observation channel.
- [ ] Step 2.1.5 — Preserve `AnnounceBus` only as a compatibility façade or remove it after parity tests.

### Task 2.2 — Connect scout outputs

- [ ] Step 2.2.1 — Keep void walkers returning `BaseEvent` objects.
- [ ] Step 2.2.2 — Publish scout `BaseEvent` objects to the event channel.
- [ ] Step 2.2.3 — Add `base_events_to_observations()` for ADC summaries.
- [ ] Step 2.2.4 — Normalize scout-derived frontier/boundary summaries to ADC observation kinds.
- [ ] Step 2.2.5 — Add tests proving scout output can reach both maps and ADC through the spine.

### Task 2.3 — Connect memory, map, and motor-ready events

- [ ] Step 2.3.1 — Publish memory/trail events through the event channel.
- [ ] Step 2.3.2 — Publish territory update events through the event channel.
- [ ] Step 2.3.3 — Reserve motor-event kinds for actuator trace and reafference.
- [ ] Step 2.3.4 — Verify event kinds are not silently dropped by reducers.

## Phase 3 — Fold Producers Before Reducers

### Task 3.1 — Reorder tick staging

- [ ] Step 3.1.1 — Ingest input and stimulation.
- [ ] Step 3.1.2 — Advance connectome.
- [ ] Step 3.1.3 — Collect connectome observations.
- [ ] Step 3.1.4 — Run bounded scouts using current seeds and map heads.
- [ ] Step 3.1.5 — Normalize scout summaries for ADC.
- [ ] Step 3.1.6 — Fold ADC, TerritoryUF, EventDrivenMetrics, maps, memory, and trail.
- [ ] Step 3.1.7 — Build metrics only after reducers fold.
- [ ] Step 3.1.8 — Run optional actuator/plasticity systems with current territory data or explicitly schedule them for next tick.

### Task 3.2 — Remove stale batch hazards

- [ ] Step 3.2.1 — Clear `_last_obs_batch` at the start of each tick fold.
- [ ] Step 3.2.2 — Clear `_last_adc_metrics` at the start of each tick fold.
- [ ] Step 3.2.3 — Add test where a tick drains zero observations and stale observations cannot be reused.
- [ ] Step 3.2.4 — Add telemetry field for `spine_drained_observations_total`.

## Phase 4 — Add Event Coverage Tests

### Task 4.1 — Producer/consumer parity

- [ ] Step 4.1.1 — Add test that every produced observation kind has a consumer or explicit ignore policy.
- [ ] Step 4.1.2 — Add test that every consumed observation kind has a producer or explicit future marker.
- [ ] Step 4.1.3 — Add test that every produced `BaseEvent` kind has at least one reducer or explicit archive policy.
- [ ] Step 4.1.4 — Add test that unknown event kinds are counted, not silently discarded.

### Task 4.2 — Runtime smoke evidence

- [ ] Step 4.2.1 — Add smoke test with bus/spine counters enabled.
- [ ] Step 4.2.2 — Verify `region_stat`, `cycle_hit`, and scout events are published.
- [ ] Step 4.2.3 — Verify ADC receives at least one non-cycle observation kind.
- [ ] Step 4.2.4 — Verify maps receive scout events through the spine.
