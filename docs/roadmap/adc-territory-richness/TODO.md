# ADC Territory Richness TODO

Status: active draft.
Source report: `reports/20260622/vdm_rt_void_bus_adc_loop_analysis.md`.

ADC is connected but underfed. It receives mostly `region_stat` and `cycle_hit`; it accepts `boundary_probe` and `novel_frontier`, but the current sparse path does not produce them.

## Phase 0 — Prove Current Thin Feed

### Task 0.1 — Add ADC feed diagnostics

- [ ] Step 0.1.1 — Add telemetry counters for each ADC-supported observation kind.
- [ ] Step 0.1.2 — Record `adc_seen_region_stat` per tick.
- [ ] Step 0.1.3 — Record `adc_seen_cycle_hit` per tick.
- [ ] Step 0.1.4 — Record `adc_seen_boundary_probe` per tick.
- [ ] Step 0.1.5 — Record `adc_seen_novel_frontier` per tick.

### Task 0.2 — Add smoke baseline

- [ ] Step 0.2.1 — Run a 64-neuron smoke test before routing changes.
- [ ] Step 0.2.2 — Save expected baseline that `adc_boundaries` may remain zero before Phase 2.
- [ ] Step 0.2.3 — Save published/drained counters for comparison after event spine changes.

## Phase 1 — Make `region_stat` Local and Identifiable

### Task 1.1 — Replace global weight statistics

- [ ] Step 1.1.1 — Change `region_stat.w_mean` to use local sampled nodes/edges.
- [ ] Step 1.1.2 — Change `region_stat.w_var` to use local sampled nodes/edges.
- [ ] Step 1.1.3 — Preserve global statistics separately as runtime metrics if still useful.
- [ ] Step 1.1.4 — Add unit test proving local region stats differ across two different local neighborhoods.

### Task 1.2 — Add territory identity hints

- [ ] Step 1.2.1 — Populate `domain_hint` or `source_hint` for region observations.
- [ ] Step 1.2.2 — Include traversal seed or region id when available.
- [ ] Step 1.2.3 — Stop using `coverage_id=0` for all cycle hits.
- [ ] Step 1.2.4 — Add tests proving cycle hits can map to more than one coverage id.

## Phase 2 — Produce Missing ADC Observation Kinds

### Task 2.1 — Emit `boundary_probe`

- [ ] Step 2.1.1 — Define boundary probe trigger from low support between adjacent regions.
- [ ] Step 2.1.2 — Define boundary probe trigger from repeated low-coupling cut behavior.
- [ ] Step 2.1.3 — Include source nodes, support score, and territory hints.
- [ ] Step 2.1.4 — Add test proving at least one synthetic sparse graph emits `boundary_probe`.
- [ ] Step 2.1.5 — Add smoke target where `adc_boundaries` becomes nonzero when a boundary is injected.

### Task 2.2 — Emit `novel_frontier`

- [ ] Step 2.2.1 — Define novelty from cold/rare/unseen region appearances.
- [ ] Step 2.2.2 — Include frontier nodes, novelty score, and source scout kind.
- [ ] Step 2.2.3 — Add test proving repeated rare frontier produces `novel_frontier`.
- [ ] Step 2.2.4 — Verify ADC territory count responds to sustained novel frontier input.

## Phase 3 — Make ADC Territory Output Useful to Global Systems

### Task 3.1 — Publish ADC summaries back to event spine

- [ ] Step 3.1.1 — Emit `ADCEvent` through event channel after ADC fold.
- [ ] Step 3.1.2 — Include territory count, boundary count, cycle hits, and current territory ids.
- [ ] Step 3.1.3 — Include changed territory ids since previous tick.
- [ ] Step 3.1.4 — Add tests proving maps and future sparse structural-plasticity code can read current ADC summary.

### Task 3.2 — Add territory evidence gates

- [ ] Step 3.2.1 — Add smoke assertion that ADC sees more than `cycle_hit` over a configured diagnostic run.
- [ ] Step 3.2.2 — Add smoke assertion that `boundary_probe` increments boundary telemetry in a synthetic diagnostic mode.
- [ ] Step 3.2.3 — Add regression artifact showing before/after ADC richness fields.
