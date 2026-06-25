# Loop Scan Reduction TODO

Status: active draft.
Source report: `reports/20260622/vdm_rt_void_bus_adc_loop_analysis.md`.

The runtime repeatedly walks the same active graph through density, connectome step metrics, compute metrics, and `CoreEngine.snapshot()`. This roadmap moves toward cached sparse snapshots and reducer-fed metrics.

## Phase 0 — Measure Current Scan Pressure

### Task 0.1 — Static scan inventory

- [ ] Step 0.1.1 — Inventory calls to `active_edge_count()` in the tick path.
- [ ] Step 0.1.2 — Inventory calls to `connected_components()` in the tick path.
- [ ] Step 0.1.3 — Inventory calls to `cyclomatic_complexity()` in the tick path.
- [ ] Step 0.1.4 — Inventory calls to `connectome_entropy()` in the tick path.
- [ ] Step 0.1.5 — Inventory full adjacency/weight vector loops inside `runtime/loop/main.py`.

### Task 0.2 — Dynamic scan counters

- [ ] Step 0.2.1 — Add temporary counters around expensive graph metric functions.
- [ ] Step 0.2.2 — Run 32-neuron and 256-neuron smoke tests.
- [ ] Step 0.2.3 — Record calls per tick for each scan-heavy metric.
- [ ] Step 0.2.4 — Store baseline in `docs/generated/scan-baselines/`.

## Phase 1 — Add Sparse Metrics Snapshot

### Task 1.1 — Define snapshot contract

- [ ] Step 1.1.1 — Add `SparseConnectome.metrics_snapshot()`.
- [ ] Step 1.1.2 — Include cached `_edges_active`.
- [ ] Step 1.1.3 — Include cached `_vertices_active`.
- [ ] Step 1.1.4 — Include `components_lb`.
- [ ] Step 1.1.5 — Include `cycles_est`.
- [ ] Step 1.1.6 — Include traversal-derived counters and current event-spine counters.

### Task 1.2 — Replace repeated metric readers

- [ ] Step 1.2.1 — Make `compute_metrics()` prefer `metrics_snapshot()` when present.
- [ ] Step 1.2.2 — Make `CoreEngine.snapshot()` accept canonical metrics from the runtime loop.
- [ ] Step 1.2.3 — Remove duplicate scan call inside `CoreEngine.snapshot()` after parity tests pass.
- [ ] Step 1.2.4 — Add tests proving snapshot fields match scan-based fields on small synthetic graphs.

## Phase 2 — Move Full Audits Behind Explicit Cadence

### Task 2.1 — Add audit cadence controls

- [ ] Step 2.1.1 — Add `audit_every` config for expensive full scans.
- [ ] Step 2.1.2 — Default full audits off or low-cadence for runtime.
- [ ] Step 2.1.3 — Keep exact full scans available for diagnostics.
- [ ] Step 2.1.4 — Add telemetry field indicating whether a tick used cached metrics or full audit metrics.

### Task 2.2 — Add parity audit mode

- [ ] Step 2.2.1 — Add diagnostic run that computes both cached and full metrics.
- [ ] Step 2.2.2 — Record absolute/relative differences.
- [ ] Step 2.2.3 — Fail parity test when cached metrics drift outside declared tolerance.

## Phase 3 — Keep SIE Fed Without Rescanning

### Task 3.1 — Clarify SIE inputs

- [ ] Step 3.1.1 — Document which SIE version consumes density, vector-local `W`/`dW`, or event-fed signals.
- [ ] Step 3.1.2 — Replace any full-graph density scan used only for SIE with cached density.
- [ ] Step 3.1.3 — Add event-spine inputs for SIE where available.
- [ ] Step 3.1.4 — Add test proving SIE can run from cached sparse snapshot on diagnostic graph.

### Task 3.2 — Runtime shell cleanup

- [ ] Step 3.2.1 — Split `runtime/loop/main.py` into producer, reducer, metrics, and actuator modules.
- [ ] Step 3.2.2 — Keep main loop as orchestration shell only.
- [ ] Step 3.2.3 — Add file-size or complexity guard for the main loop.
- [ ] Step 3.2.4 — Add test proving staged tick order remains intact after split.
