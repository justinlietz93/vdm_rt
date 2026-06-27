---
title: Neurobiology Upgrade
status: active
owner: runtime-core
source_authority: docs/roadmap/neurobiology-upgrade/VDM_Hard_Implementation_Matrix_v0.2_motor_addendum.md
summary: Why the runtime cleanup exists and what the upgrade must enforce.
---


# Neurobiology Upgrade

## Why this repo was split and cleaned

The runtime cleanup exists because the old repo shape made the necessary swap harder than the runtime engine itself required. The target is not a nicer frontend. The target is a stricter runtime where receptor and effector boundaries can be rebuilt without the old UI, decoder, visualization, and generated-output clutter steering the implementation.

## Governing upgrade law

```text
External stays external.
Internal stays internal.
UTE is receptor transduction only.
UTD is actuator transduction only.
The live decoder must not author model output.
```

## Consequence

The decoder should not be improved. It should be removed from live authorship.

The replacement is an actuator pathway:

```text
internal state dynamics
  -> articulation trace formation
  -> endogenous release gate
  -> actuator primitive event
  -> rendered external witness
  -> reafferent receptor event
```

## Source documents

| Source | Role |
|---|---|
| `VDM_Hard_Implementation_Matrix_v0.1.md` | First hard boundary matrix for UTE/UTD rewrite. |
| `VDM_Hard_Implementation_Matrix_v0.2_motor_addendum.md` | Adds motor-learning / effector-side rows M26-M37. |
| `VDM_Motor_Learning_Decoder_Matrix_Addendum_v0.1.md` | Explains why motor-learning literature closes the decoder ambiguity. |
| `Aura_Distinction_Inventory_v0.7.md` | Evidence inventory showing why the forced decoder is inadequate and why internal adaptation must be protected. |

## What must not happen

- Do not rename a sentence composer into an actuator.
- Do not hide a phrase bank behind a UTD class.
- Do not let a renderer fix malformed traces.
- Do not let the release gate author content.
- Do not let wall-clock cadence drive cognition.
- Do not treat rendered text as internal state.
