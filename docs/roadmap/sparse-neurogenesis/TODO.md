# Sparse Neurogenesis TODO

Status: planned and intentionally deferred.
Source report: `reports/20260622/vdm_rt_void_bus_adc_loop_analysis.md`.

The legacy substrate files encode a real missing capability: dynamic self-managing neuron population. The live implementation must be sparse-native and must not preserve torch/dense substrate behavior.

## Deferral Boundary

Phase 0 is complete: it preserves the source material and extracts the required
invariants. It does **not** create a live neurogenesis subsystem. There is no
`core/neurogenesis/` package or `config/neurogenesis.toml` file in the runtime
while this roadmap is deferred.

When work resumes, `population_policy.py` and its named TOML configuration are
only the initial policy layer. They must not be represented as completion of
dynamic population change: that capability remains unmet until sparse growth
and retirement safely update all affected runtime state and lifecycle events
are visible on the event spine. Defer implementation until it is selected over
more immediate runtime work.

## Phase 0 — Extract the Capability From Legacy Substrate

### Task 0.1 — Archive design source

- [x] Step 0.1.1 — Move old `core/substrate/` files out of live runtime path.
- [x] Step 0.1.2 — Preserve them under `docs/sources/legacy-substrate-neurogenesis/`.
- [x] Step 0.1.3 — Add archive README explaining that these files are not runtime code and must not be deleted before capability closure.
- [x] Step 0.1.4 — Add guard test proving live runtime no longer imports the archived substrate path.

### Task 0.2 — Extract requirements

- [x] Step 0.2.1 — Document dynamic neuron population growth.
- [x] Step 0.2.2 — Document node-count management between configured minimum and maximum bounds.
- [x] Step 0.2.3 — Document growth debt and stability arbitration.
- [x] Step 0.2.4 — Document new-neuron seeding requirements.
- [x] Step 0.2.5 — Document culling/pruning requirements.
- [x] Step 0.2.6 — Document bridge growth and cluster repair requirements.

## Phase 1 — Define Sparse Population Policy

### Task 1.1 — Add policy model

- [ ] Step 1.1.0 — When implementation is reprioritized, add the named policy configuration and policy module as an initial, non-executing layer; do not mark dynamic population change complete.
- [ ] Step 1.1.1 — Add `core/neurogenesis/population_policy.py`.
- [ ] Step 1.1.2 — Define `min_neurons`.
- [ ] Step 1.1.3 — Define `max_neurons`.
- [ ] Step 1.1.4 — Define `growth_enabled`.
- [ ] Step 1.1.5 — Define `culling_enabled`.
- [ ] Step 1.1.6 — Define `grow_budget_per_tick`.
- [ ] Step 1.1.7 — Define `cull_budget_per_tick`.
- [ ] Step 1.1.8 — Define growth/cull pressure thresholds.

### Task 1.2 — Add policy invariants

- [ ] Step 1.2.1 — Test population cannot grow above `max_neurons`.
- [ ] Step 1.2.2 — Test population cannot cull below `min_neurons`.
- [ ] Step 1.2.3 — Test disabled growth produces no node-growth events.
- [ ] Step 1.2.4 — Test disabled culling produces no node-cull events.

## Phase 2 — Build Sparse Node Growth

### Task 2.1 — Add sparse growth executor

- [ ] Step 2.1.1 — Add `core/neurogenesis/sparse_node_growth.py`.
- [ ] Step 2.1.2 — Implement append-only node allocation for `SparseConnectome`.
- [ ] Step 2.1.3 — Expand sparse adjacency slots.
- [ ] Step 2.1.4 — Expand weights/stimulus arrays without dense matrix allocation.
- [ ] Step 2.1.5 — Expand DSU/territory-compatible structures safely.
- [ ] Step 2.1.6 — Add tests proving growth does not allocate dense `N x N` matrices.

### Task 2.2 — Seed new nodes from runtime signals

- [ ] Step 2.2.1 — Seed from ADC territory pressure.
- [ ] Step 2.2.2 — Seed from SIE/growth arbiter pressure.
- [ ] Step 2.2.3 — Seed from void-map frontier pressure.
- [ ] Step 2.2.4 — Seed sparse edges from local territory neighborhoods.
- [ ] Step 2.2.5 — Publish `node_growth`, `node_reseed`, and `territory_expanded` events.

## Phase 3 — Build Sparse Node Pruning/Culling

### Task 3.1 — Add sparse pruning executor

- [ ] Step 3.1.1 — Add `core/neurogenesis/sparse_node_pruning.py`.
- [ ] Step 3.1.2 — Define cold/low-value/isolated/stale node candidates.
- [ ] Step 3.1.3 — Support safe node retirement before physical compaction.
- [ ] Step 3.1.4 — Update adjacency and territory structures after retirement.
- [ ] Step 3.1.5 — Publish `node_cull`, `node_retire`, and `territory_contracted` events.

### Task 3.2 — Add cull safety gates

- [ ] Step 3.2.1 — Refuse to cull protected or newly grown nodes inside cooldown window.
- [ ] Step 3.2.2 — Refuse to cull nodes needed for current bridges unless bridge replacement exists.
- [ ] Step 3.2.3 — Add test where cull pressure is high but `min_neurons` prevents removal.
- [ ] Step 3.2.4 — Add test where a retired node no longer appears in traversal seeds.

## Phase 4 — Connect to Event Spine

### Task 4.1 — Add lifecycle event model

- [ ] Step 4.1.1 — Add `core/neurogenesis/node_lifecycle_events.py`.
- [ ] Step 4.1.2 — Define `node_growth` event payload.
- [ ] Step 4.1.3 — Define `node_cull` event payload.
- [ ] Step 4.1.4 — Define `node_retire` event payload.
- [ ] Step 4.1.5 — Define `node_reseed` event payload.
- [ ] Step 4.1.6 — Define `population_pressure` and `population_stability` events.

### Task 4.2 — Make structural changes globally visible

- [ ] Step 4.2.1 — Publish node lifecycle events through runtime event spine.
- [ ] Step 4.2.2 — Feed lifecycle events to ADC.
- [ ] Step 4.2.3 — Feed lifecycle events to maps.
- [ ] Step 4.2.4 — Feed lifecycle events to SIE/GDSP where appropriate.
- [ ] Step 4.2.5 — Add smoke telemetry for node growth/cull counts.

## Phase 5 — Validate Against Original Runtime Intent

### Task 5.1 — Zero-training and sparse guarantees

- [ ] Step 5.1.1 — Prove sparse neurogenesis uses no optimizer, loss, gradient, or training loop.
- [ ] Step 5.1.2 — Prove sparse neurogenesis imports no torch.
- [ ] Step 5.1.3 — Prove sparse neurogenesis does not allocate dense adjacency matrices.
- [ ] Step 5.1.4 — Prove node changes are driven by runtime pressure signals, not offline fitting.

### Task 5.2 — Runtime evidence package

- [ ] Step 5.2.1 — Add diagnostic run with growth enabled and culling disabled.
- [ ] Step 5.2.2 — Add diagnostic run with culling enabled and growth disabled.
- [ ] Step 5.2.3 — Add diagnostic run with both enabled inside min/max bounds.
- [ ] Step 5.2.4 — Export node lifecycle event table.
- [ ] Step 5.2.5 — Export population over time and territory response summaries.
