# Memory, GDSP, and Territory Timing TODO

Status: active draft.
Source report: `reports/20260622/vdm_rt_void_bus_adc_loop_analysis.md`.

This checklist fixes ownership and timing issues around memory fields, territory folds, GDSP inputs, and stale observations.

## Phase 0 — Prove Current Ownership and Timing

### Task 0.1 — Memory field ownership audit

- [ ] Step 0.1.1 — Trace writes to `eng._memory_field`.
- [ ] Step 0.1.2 — Trace writes to `connectome._memory_field`.
- [ ] Step 0.1.3 — Trace reads from `nx._memory_field` in telemetry fold.
- [ ] Step 0.1.4 — Add diagnostic telemetry showing which memory field object is active each tick.

### Task 0.2 — GDSP territory timing audit

- [ ] Step 0.2.1 — Trace when GDSP asks for `territory_indices`.
- [ ] Step 0.2.2 — Trace when `TerritoryUF` folds current observations.
- [ ] Step 0.2.3 — Add test proving current GDSP territory input is one tick stale or prove it has been corrected.
- [ ] Step 0.2.4 — Trace `bias_hint` publication and consumption.

## Phase 1 — Fix Memory Ownership

### Task 1.1 — Choose single memory owner

- [ ] Step 1.1.1 — Decide whether memory field ownership lives on `CoreEngine`, `SparseConnectome`, or a dedicated reducer state.
- [ ] Step 1.1.2 — Document the ownership decision in `docs/pages/architecture/runtime-boundaries.md` or a new architecture page.
- [ ] Step 1.1.3 — Replace split writes with single-owner updates.
- [ ] Step 1.1.4 — Add compatibility reads only during migration.

### Task 1.2 — Restore memory telemetry

- [ ] Step 1.2.1 — Ensure `mem_Theta` is emitted when memory field is active.
- [ ] Step 1.2.2 — Ensure `mem_Da` is emitted when memory field is active.
- [ ] Step 1.2.3 — Ensure `mem_Lambda` is emitted when memory field is active.
- [ ] Step 1.2.4 — Ensure `mem_Gamma` is emitted when memory field is active.
- [ ] Step 1.2.5 — Add smoke assertion for memory telemetry under a memory-enabled run.

## Phase 2 — Fix Territory Timing

### Task 2.1 — Fold territories before GDSP consumes them

- [ ] Step 2.1.1 — Move ADC/TerritoryUF fold before GDSP if GDSP needs current territories.
- [ ] Step 2.1.2 — Alternatively mark GDSP as explicitly next-tick scheduled and encode that in telemetry.
- [ ] Step 2.1.3 — Add test proving the selected rule.
- [ ] Step 2.1.4 — Add field `territory_age_ticks` to GDSP telemetry.

### Task 2.2 — Make `bias_hint` meaningful or remove it

- [ ] Step 2.2.1 — Decide whether `bias_hint` is an ADC observation, BaseEvent, GDSP-private hint, or deprecated signal.
- [ ] Step 2.2.2 — Route `bias_hint` through the event spine if retained.
- [ ] Step 2.2.3 — Add consumer tests for retained `bias_hint`.
- [ ] Step 2.2.4 — Remove `bias_hint` production if no consumer exists.

## Phase 3 — Prevent Stale Observation Reuse

### Task 3.1 — Clear per-tick observation state

- [ ] Step 3.1.1 — Set `_last_obs_batch = []` before each drain.
- [ ] Step 3.1.2 — Set `_last_adc_metrics = {}` before each ADC fold.
- [ ] Step 3.1.3 — Add test where one tick produces observations and the next tick produces none.
- [ ] Step 3.1.4 — Verify old observations do not re-enter event folding.

### Task 3.2 — Add status counters

- [ ] Step 3.2.1 — Emit `obs_batch_size` per tick.
- [ ] Step 3.2.2 — Emit `adc_folded_this_tick` per tick.
- [ ] Step 3.2.3 — Emit `territory_folded_this_tick` per tick.
- [ ] Step 3.2.4 — Emit `gdsp_territory_source` per GDSP invocation.
