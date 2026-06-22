# Scout and Map Ownership TODO

Status: active draft.
Source report: `reports/20260622/vdm_rt_void_bus_adc_loop_analysis.md`.

Void walkers and maps are core runtime systems. The current issue is duplicate ownership and bypassed routing, not low importance.

## Phase 0 — Establish Ownership Rules

### Task 0.1 — Classify scouts and maps as runtime systems

- [ ] Step 0.1.1 — Add docs contract declaring `core/cortex/void_walkers/` live runtime code.
- [ ] Step 0.1.2 — Add docs contract declaring `core/cortex/maps/` live runtime code.
- [ ] Step 0.1.3 — Add guard test proving both packages remain importable.
- [ ] Step 0.1.4 — Add guard test preventing accidental deletion of these packages during cleanup.

### Task 0.2 — Identify duplicate scout paths

- [ ] Step 0.2.1 — Trace `CoreEngine._void_scout` ownership.
- [ ] Step 0.2.2 — Trace runtime loop's explicit multi-scout batch ownership.
- [ ] Step 0.2.3 — Identify which scouts are active per tick when `CoreEngine` is present.
- [ ] Step 0.2.4 — Identify which scouts are skipped or shadowed by fallback paths.

## Phase 1 — Choose One Scout Execution Owner

### Task 1.1 — Move scout orchestration into one module

- [ ] Step 1.1.1 — Add `runtime/loop/producers.py`.
- [ ] Step 1.1.2 — Move explicit scout-batch execution into `producers.py`.
- [ ] Step 1.1.3 — Make `CoreEngine` consume scout events rather than owning a separate scout path.
- [ ] Step 1.1.4 — Leave compatibility shim only until parity tests pass.

### Task 1.2 — Define scout cadence and budget

- [ ] Step 1.2.1 — Add bounded scout budget per tick.
- [ ] Step 1.2.2 — Add per-scout enabled/disabled telemetry.
- [ ] Step 1.2.3 — Add map-head seeded scout selection.
- [ ] Step 1.2.4 — Add fallback seed policy when no map head exists.

## Phase 2 — Route Scout Products Correctly

### Task 2.1 — Send scout events through event spine

- [ ] Step 2.1.1 — Publish `VTTouchEvent` to event channel.
- [ ] Step 2.1.2 — Publish `EdgeOnEvent` to event channel.
- [ ] Step 2.1.3 — Publish `SpikeEvent` to event channel.
- [ ] Step 2.1.4 — Publish `DeltaWEvent` to event channel.
- [ ] Step 2.1.5 — Add test proving each scout event kind reaches EventDrivenMetrics or an explicit reducer.

### Task 2.2 — Summarize scout events for ADC

- [ ] Step 2.2.1 — Convert cold/frontier scout outputs into `novel_frontier` observations when appropriate.
- [ ] Step 2.2.2 — Convert boundary-like scout outputs into `boundary_probe` observations when appropriate.
- [ ] Step 2.2.3 — Convert cycle scout outputs into meaningful cycle coverage observations.
- [ ] Step 2.2.4 — Add test proving scout-derived ADC observations reach ADC in the same tick.

## Phase 3 — Make Maps Reducer-Owned

### Task 3.1 — Centralize map folding

- [ ] Step 3.1.1 — Add `runtime/loop/reducers.py`.
- [ ] Step 3.1.2 — Fold event maps from drained spine events only.
- [ ] Step 3.1.3 — Remove scattered direct map mutation from the main loop.
- [ ] Step 3.1.4 — Add tests proving map counts match the events drained by the spine.

### Task 3.2 — Expose map heads to producers

- [ ] Step 3.2.1 — Add bounded map-head snapshot API.
- [ ] Step 3.2.2 — Feed map heads into scout seed selection.
- [ ] Step 3.2.3 — Verify the main loop does not scan the full graph to discover seeds already present in maps.
