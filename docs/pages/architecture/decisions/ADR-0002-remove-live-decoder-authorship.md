---
title: ADR-0002 Remove Live Decoder Authorship
status: active
owner: runtime-core
source_authority: docs/roadmap/neurobiology-upgrade/VDM_Motor_Learning_Decoder_Matrix_Addendum_v0.1.md
summary: Decision to replace live decoder authorship with actuator trace control.
---


# ADR-0002 — Remove Live Decoder Authorship

## Status

Accepted as target architecture.

## Decision

The live output path must not author model output using a decoder, phrase bank, completion branch, lexical memory, or renderer repair.

## Replacement

Output becomes actuator-manifold control:

```text
articulation trace -> release -> actuator event -> witness -> reafferent feedback
```

## Consequences

- The decoder is not improved.
- The renderer becomes a witness surface only.
- The output basis is fixed by the device.
- Skill emerges through repeated trace formation, execution, feedback, and correction.
