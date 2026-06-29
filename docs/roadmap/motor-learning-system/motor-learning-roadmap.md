---
title: Motor-Learning Roadmap
status: active
owner: runtime-core
source_authority: docs/roadmap/motor-learning-system/TODO.md
summary: Phase/task/step roadmap for the motor-learning upgrade.
---


# Motor-Learning Roadmap

This roadmap is intentionally written around phases, tasks, and steps. It is not a generic feature list. Each phase exists to remove live decoder authorship and replace it with a bounded actuator-learning pathway.

## Phase 0 — Preserve the Clean Runtime Ground

### Task 0.1 — Keep the repo headless

- [x] Remove old frontend package.
- [x] Remove old visualization/WebSocket path.
- [x] Remove no-op visualization flags.
- [x] Preserve headless runtime smoke path.
- [ ] Add CI job for runtime smoke and boundary guards.

### Task 0.2 — Protect core/runtime boundaries

- [x] Keep `core`, `runtime`, `io`, and `control` separable.
- [x] Retain SIE and substrate variants rather than deleting by naive static orphan status.
- [ ] Add import-boundary policy checker.
- [ ] Add dependency check proving no Dash/frontend install is needed.

## Phase 1 — Remove Live Decoder Authorship

### Task 1.1 — Identify live authoring paths

- [x] Audit `io/cognition`, `io/lexicon`, and `runtime/helpers/speak.py`.
- [x] Mark any phrase bank, macro composer, summary fallback, n-gram, or completion branch as forbidden in live output.
- [x] Split diagnostic/offline utilities from live UTD path.

### Task 1.2 — Add decoder kill-switch tests

- [x] Test live UTD cannot import lexical authoring modules.
- [x] Test gate opening cannot create content.
- [ ] Test renderer cannot repair malformed traces.
- [x] Test novel input symbols do not expand output basis through the removed lexicon/text-mapper path.

## Phase 2 — Define the Device Basis

### Task 2.1 — Create fixed actuator basis model

- [x] Add `core/sensorimotor/efference/basis.py`.
- [ ] Define device-owned primitive dimensions.
- [ ] Represent text output as keyboard/grapheme/scancode-like actuation, not as a vocabulary.
- [ ] Add basis hash to telemetry.

### Task 2.2 — Add basis invariance tests

- [ ] Run with novel input symbols.
- [ ] Verify actuator basis is unchanged.
- [ ] Verify no input-history-grown alphabet appears.

## Phase 3 — Build the Articulation Trace Buffer

### Task 3.1 — Add trace data model

- [x] Add `core/sensorimotor/efference/trace.py`.
- [x] Represent primitive, amplitude/pressure, ordering pressure, and trace identity.
- [ ] Keep trace separate from rendered witness.

### Task 3.2 — Add articulation buffer

- [ ] Add `core/sensorimotor/efference/articulation_buffer.py`.
- [ ] Permit partial, malformed, competing, or unfinished traces.
- [ ] Ensure buffer does not require a prebuilt sentence.

## Phase 4 — Replace Release with Release-Only Gate

### Task 4.1 — Separate selection, release, and content

- [ ] Add release event type.
- [ ] Wire B1/valence-like signal to release/hold only.
- [ ] Prove changing gate state changes timing only, not trace content.

### Task 4.2 — Emit actuator events

- [ ] Convert released trace steps into actuator events.
- [ ] Preserve trace identity through event emission.
- [ ] Store rendered witness separately.

## Phase 5 — Add Reafferent Feedback

### Task 5.1 — Route action consequences back through UTE

- [x] Add IO-owned `io/transduction/reafference.py`.
- [x] Record action consequence as receptor event when externally visible.
- [ ] Add explicit `no_feedback_available` reason when a medium cannot provide feedback.

### Task 5.2 — Add residual/correction channel

- [ ] Define intended trace vs sensed consequence comparison.
- [ ] Emit residual/correction telemetry.
- [ ] Keep correction separate from selection/release.

## Phase 6 — Motor Skill Development

### Task 6.1 — Track integration, differentiation, refinement

- [ ] Add actuator entropy metric.
- [ ] Add trace length and primitive diversity metrics.
- [ ] Add correction count and residual magnitude metrics.
- [ ] Track refinement across runs without ML training.

### Task 6.2 — Permit motor equivalence

- [ ] Allow multiple traces to render the same witness.
- [ ] Preserve trace identity even when witness matches.
- [ ] Add tests proving witness equality does not collapse trace identity.

## Phase 7 — Evidence and Reporting

### Task 7.1 — Package motor-learning evidence

- [ ] Generate per-run motor telemetry summary.
- [ ] Generate trace/witness/reafference audit table.
- [ ] Add negative controls for decoder-like shortcuts.

### Task 7.2 — Connect to Aura distinction families

- [ ] Map D0.5 forced decoder evidence to new UTD tests.
- [ ] Map D4 phase-gated output to release-only gate telemetry.
- [ ] Map D8 endogenous clock to output timing tests.

## Phase 8 — New Frontend Only After Control Boundary Exists

### Task 8.1 — Define future frontend contract

- [ ] Frontend reads status/run artifacts or a control API.
- [ ] Frontend never owns runtime launch or filesystem mutation directly.
- [ ] Frontend never authors model output.

### Task 8.2 — Build client after headless proof

- [ ] Build a minimal viewer only after Phase 1-5 tests pass.
- [ ] Keep UI as witness/control surface, not cognition.
