# Memory, Structural Plasticity, and Territory Timing TODO

Status: active draft.
Source report: `reports/20260622/vdm_rt_void_bus_adc_loop_analysis.md`.

This checklist fixes ownership and timing issues around memory fields, territory folds, future sparse structural-plasticity inputs, and stale observations.

## Phase 0 — Prove Current Ownership and Timing

### Task 0.1 — Memory field ownership audit

- [ ] Step 0.1.1 — Trace writes to `eng._memory_field`.
- [ ] Step 0.1.2 — Trace writes to `connectome._memory_field`.
- [ ] Step 0.1.3 — Trace reads from `nx._memory_field` in telemetry fold.
- [ ] Step 0.1.4 — Add diagnostic telemetry showing which memory field object is active each tick.

### Task 0.2 — Structural-plasticity territory timing audit

- [ ] Step 0.2.1 — Trace when the future sparse structural-plasticity owner asks for `territory_indices`.
- [ ] Step 0.2.2 — Trace when `TerritoryUF` folds current observations.
- [ ] Step 0.2.3 — Add test proving structural-plasticity territory input is current or explicitly next-tick scheduled.
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

### Task 2.1 — Define structural-plasticity territory timing

- [ ] Step 2.1.1 — Move ADC/TerritoryUF fold before future sparse structural-plasticity code if it needs current territories.
- [ ] Step 2.1.2 — Alternatively mark sparse structural-plasticity as explicitly next-tick scheduled and encode that in telemetry.
- [ ] Step 2.1.3 — Add test proving the selected rule.
- [ ] Step 2.1.4 — Add field `territory_age_ticks` to structural-plasticity telemetry.

### Task 2.2 — Make `bias_hint` meaningful or remove it

- [ ] Step 2.2.1 — Decide whether `bias_hint` is an ADC observation, BaseEvent, structural-plasticity hint, or deprecated signal.
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
- [ ] Step 3.2.4 — Emit `structural_plasticity_territory_source` per structural-plasticity invocation.

## Phase 4 — Engram Resume Integrity

### Task 4.1 — Reproduce the Aura reload failure mode

- [ ] Step 4.1.1 — Create a short run with checkpointing enabled and nontrivial connectome, ADC, memory, map, and SIE state.
- [ ] Step 4.1.2 — Stop the run, reload from the checkpoint with `--load-engram`, and continue for a small number of ticks.
- [ ] Step 4.1.3 — Compare pre-stop state against post-load state before the first continued tick.
- [ ] Step 4.1.4 — Record whether only config-like values are restored while state history is lost.
- [ ] Step 4.1.5 — Preserve an Aura-style regression fixture once the exact failure is reproduced.

### Task 4.2 — Audit checkpoint save coverage

- [ ] Step 4.2.1 — List every field saved by `core/memory/engram_io.py` for sparse checkpoints.
- [ ] Step 4.2.2 — List every live runtime state field needed to resume a run without semantic reset.
- [ ] Step 4.2.3 — Compare saved fields against `SparseConnectome`, ADC, memory field, trail/map reducers, SIE, phase, and runtime counters.
- [ ] Step 4.2.4 — Mark each field as `required`, `optional`, `derived`, or `do_not_resume`.
- [ ] Step 4.2.5 — Add a manifest section to every checkpoint describing what was saved and what was intentionally omitted.

### Task 4.3 — Audit checkpoint load behavior

- [ ] Step 4.3.1 — Trace `runtime/helpers/engram.py::maybe_load_engram`.
- [ ] Step 4.3.2 — Trace `core/memory/engram_io.py::load_engram`.
- [ ] Step 4.3.3 — Trace phase-file hot loading through `runtime/phase.py`.
- [ ] Step 4.3.4 — Verify load restores arrays, adjacency, active-state trackers, ADC territories, memory fields, and reducer state instead of only applying config.
- [ ] Step 4.3.5 — Make incomplete restore fail loudly unless explicitly requested as config-only import.

### Task 4.4 — Separate config load from state resume

- [ ] Step 4.4.1 — Define `resume_state` semantics for full state restoration.
- [ ] Step 4.4.2 — Define `load_config` semantics for importing run parameters without state history.
- [ ] Step 4.4.3 — Prevent `--load-engram` from silently behaving like config-only load.
- [ ] Step 4.4.4 — Add telemetry field `resume_mode` with values `none`, `state`, `config_only`, or `failed`.
- [ ] Step 4.4.5 — Add telemetry field `resume_state_fields_loaded` listing restored sections.

### Task 4.5 — Add resume parity tests

- [ ] Step 4.5.1 — Save a checkpoint from a deterministic synthetic sparse runtime.
- [ ] Step 4.5.2 — Load the checkpoint into a fresh runtime object.
- [ ] Step 4.5.3 — Assert structural parity for node count, adjacency, active weights, stimulation state, and traversal state.
- [ ] Step 4.5.4 — Assert ADC parity for territories, boundaries, cycle hits, TTL, and split state.
- [ ] Step 4.5.5 — Assert memory/map parity for memory field, trail state, and event-map heads where those systems are enabled.
- [ ] Step 4.5.6 — Assert continued tick numbering and checkpoint retention do not overwrite or prune the resumed history incorrectly.
