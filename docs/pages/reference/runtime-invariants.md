---
title: Runtime Invariants
status: active
owner: runtime-core
source_authority: docs/contracts/runtime-invariants.yml
summary: Hard and strong invariants for the headless runtime and motor-learning upgrade.
---


# Runtime Invariants

## Hard invariants

| ID | Rule | Acceptance implication |
|---|---|---|
| M01 | Interface-only coupling | Core does not touch world/UI directly. |
| M03 | No completion-branch authorship in live path | No live phrase bank, n-gram, lexicon, sentence macro, or completion branch. |
| M04 | Endogenous cognitive time is sovereign | Model time is endogenous; wall-clock fields are logging/provenance/offline-analysis coordinates, not model authorship. Fixed-step substitution and unmeasured per-tick overhead are rejected. |
| M12 | Text intake preserves full order and repetition | Ordered input must not collapse into a set or semantic dump. |
| M17 | Actuator basis belongs to the device | Output basis cannot grow from input history. |
| M18 | Articulation is model-authored before release | Release-time composition is rejected. |
| M19 | Release gate is release-only | Gate can allow/block timing, not author content. |
| M26 | Output is actuator-manifold control, not text decoding | Output is device primitive control, not vocabulary decoding. |
| M27 | Articulation buffer stores actuator-trace preparation | Buffer stores trace, not finished prose. |
| M28 | Serial output unfolds through execution | Multi-step trace can exist without prebuilt string. |
| M29 | Reafferent feedback is mandatory for motor learning | UTD action must return sensed consequence or explicit no-feedback reason. |
| M31 | Motor routines are emergent internal synergies | No installed routine table authors live output. |
| M35 | Device basis is external and bounded | Basis unchanged after novel input. |
| M36 | Output timing is endogenous release over prepared trace | Timing changes do not rewrite trace. |
| M37 | Renderer is body surface, not author | Renderer does not fill, repair, or normalize trace. |

## Strong invariants

| ID | Rule | Implementation direction |
|---|---|---|
| M30 | Motor equivalence is allowed | Same witness can arise from different traces. |
| M32 | Selection/release and correction are separate channels | Keep release signal and residual correction telemetry separate. |
| M33 | Skill develops by integration, differentiation, refinement | Track actuator entropy, trace length, correction counts, and refinement. |
| M34 | Communicative actuation is modality-flexible | Text is one device pathway, not the only real output. |

## Rejection examples

Reject implementations where:

- a renderer completes missing text,
- fixed-step or wall-clock tooling redefines the endogenous model clock,
- unmeasured per-tick IO, logging, or actuator work is added to the default timing path,
- a phrase bank writes live output,
- gate-open calls a sentence composer,
- input symbols expand output vocabulary,
- action has no receptor consequence and no explicit no-feedback reason,
- UI code launches hidden runtime behavior outside the control boundary.
