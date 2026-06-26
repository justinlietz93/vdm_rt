# Motor-Learning System Roadmap TODO

Status: active draft.

This checklist is the working implementation tracker. The reader-facing version is `docs/pages/roadmap/motor-learning-roadmap.md`.


## Phase -1 — Runtime Event-Spine Preconditions

### Task -1.1 — Complete prerequisite runtime tracks

- [ ] Step -1.1.1 — Complete `docs/roadmap/runtime-event-spine/TODO.md` Phase 1 enough to publish and drain typed events.
- [ ] Step -1.1.2 — Complete `docs/roadmap/adc-territory-richness/TODO.md` Phase 2 enough to produce `boundary_probe` and `novel_frontier`.
- [ ] Step -1.1.3 — Complete `docs/roadmap/scout-map-ownership/TODO.md` Phase 2 enough for void walker products to reach global reducers.
- [ ] Step -1.1.4 — Complete `docs/roadmap/memory-gdsp-territory/TODO.md` Phase 3 enough to prevent stale observation reuse.
- [ ] Step -1.1.5 — Complete `docs/roadmap/loop-scan-reduction/TODO.md` Phase 1 enough to provide sparse cached metrics to new motor systems.

### Task -1.2 — Add motor event reservations to the event spine

- [ ] Step -1.2.1 — Reserve event kinds for actuator trace preparation.
- [ ] Step -1.2.2 — Reserve event kinds for release/hold.
- [ ] Step -1.2.3 — Reserve event kinds for rendered witness.
- [ ] Step -1.2.4 — Reserve event kinds for reafferent feedback.
- [ ] Step -1.2.5 — Reserve event kinds for motor residual/correction.

## Phase 0 — Runtime Ground

### Task 0.1 — Keep repo headless

- [x] Step 0.1.1 — Remove old frontend.
- [x] Step 0.1.2 — Remove old visualization adapter.
- [x] Step 0.1.3 — Remove no-op visualization flags.
- [ ] Step 0.1.4 — Add CI job for runtime smoke.
- [ ] Step 0.1.5 — Add CI job for docs front matter.

### Task 0.2 — Freeze boundary policy

- [x] Step 0.2.1 — Document retained runtime layers.
- [x] Step 0.2.2 — Record preserved SIE/substrate systems.
- [ ] Step 0.2.3 — Implement import-boundary checker.
- [ ] Step 0.2.4 — Implement live-output dependency scanner.

## Phase 1 — Decoder Removal Prep

### Task 1.1 — Audit live output path

- [x] Step 1.1.1 — Trace `runtime/helpers/speak.py`.
- [x] Step 1.1.2 — Trace `io/cognition/`.
- [x] Step 1.1.3 — Trace `io/lexicon/`.
- [x] Step 1.1.4 — Mark live-prohibited authoring modules in `IO_AUDIT.md` and `runtime-cleanup-classification.yml`.

### Task 1.2 — Add kill-switch tests

- [ ] Step 1.2.1 — Test no phrase bank in live UTD path.
- [ ] Step 1.2.2 — Test no release-time sentence composition.
- [ ] Step 1.2.3 — Test renderer cannot repair malformed trace.
- [ ] Step 1.2.4 — Test novel input cannot expand output basis.

## Phase 2 — Device Basis

### Task 2.1 — Define actuator basis

- [ ] Step 2.1.1 — Add `core/motor/actuator_basis.py`.
- [ ] Step 2.1.2 — Define text/keyboard primitive basis.
- [ ] Step 2.1.3 — Add basis identity/hash telemetry.
- [ ] Step 2.1.4 — Add config-free default basis for smoke tests.

### Task 2.2 — Validate basis invariance

- [ ] Step 2.2.1 — Feed unseen symbols.
- [ ] Step 2.2.2 — Verify basis unchanged.
- [ ] Step 2.2.3 — Verify emitted trace uses existing primitives only.

## Phase 3 — Articulation Trace

### Task 3.1 — Trace model

- [ ] Step 3.1.1 — Add primitive event type.
- [ ] Step 3.1.2 — Add trace identity.
- [ ] Step 3.1.3 — Add ordering pressure/duration fields.
- [ ] Step 3.1.4 — Add trace serialization for telemetry.

### Task 3.2 — Buffer model

- [ ] Step 3.2.1 — Add articulation buffer.
- [ ] Step 3.2.2 — Permit partial traces.
- [ ] Step 3.2.3 — Permit competing traces.
- [ ] Step 3.2.4 — Ensure buffer is not rendered prose.

## Phase 4 — Release and Execution

### Task 4.1 — Release-only gate

- [ ] Step 4.1.1 — Add release event.
- [ ] Step 4.1.2 — Bind gate to hold/release only.
- [ ] Step 4.1.3 — Test gate state cannot modify trace content.

### Task 4.2 — Actuator event emission

- [ ] Step 4.2.1 — Convert trace step to actuator event.
- [ ] Step 4.2.2 — Record event under UTD telemetry.
- [ ] Step 4.2.3 — Preserve trace id into rendered witness.

## Phase 5 — Reafference and Correction

### Task 5.1 — Receptor consequence loop

- [ ] Step 5.1.1 — Add action-consequence event type.
- [ ] Step 5.1.2 — Route rendered witness back through receptor path.
- [ ] Step 5.1.3 — Add explicit no-feedback reason where needed.

### Task 5.2 — Residual correction

- [ ] Step 5.2.1 — Define intended-vs-sensed residual.
- [ ] Step 5.2.2 — Add correction telemetry channel.
- [ ] Step 5.2.3 — Keep correction separate from release.

## Phase 6 — Skill Metrics

### Task 6.1 — Refinement metrics

- [ ] Step 6.1.1 — Track actuator entropy.
- [ ] Step 6.1.2 — Track trace length and primitive diversity.
- [ ] Step 6.1.3 — Track correction count.
- [ ] Step 6.1.4 — Track residual magnitude trend.

### Task 6.2 — Motor equivalence

- [ ] Step 6.2.1 — Allow multiple traces with same rendered witness.
- [ ] Step 6.2.2 — Test witness equality does not collapse trace identity.

## Phase 7 — Evidence Package

### Task 7.1 — Motor evidence export

- [ ] Step 7.1.1 — Add per-run motor summary JSON.
- [ ] Step 7.1.2 — Add trace/witness/reafference audit table.
- [ ] Step 7.1.3 — Add decoder-shortcut negative controls.

### Task 7.2 — Aura bridge

- [ ] Step 7.2.1 — Map D0.5 to forced-decoder replacement tests.
- [ ] Step 7.2.2 — Map D4.1 to phase-gated release telemetry.
- [ ] Step 7.2.3 — Map D8.1-D8.3 to endogenous timing tests.
