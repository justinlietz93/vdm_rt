---
title: Motor-Learning System
status: active
owner: runtime-core
source_authority: docs/sources/neurobiology-upgrade/VDM_Motor_Learning_Decoder_Matrix_Addendum_v0.1.md
summary: Target architecture for decoder removal and actuator-manifold output.
---


# Motor-Learning System

## Position

The output path should become a motor-learning system, not a better symbolic decoder.

A live model output should be a device-bounded actuator trace that the runtime forms, releases, renders externally, and senses back through receptor feedback.

## Required split

```text
planning / preparation       internal articulation trace forms
selection / release          endogenous gate allows or holds prepared trace
execution                    actuator primitive is emitted
rendering                    device surface produces bounded witness
reafference                  sensed consequence returns through UTE
correction                   residual feedback updates future trace formation
```

## Target modules

Initial module names are intentionally provisional:

```text
core/motor/
  actuator_trace.py          prepared trace data model
  actuator_basis.py          fixed device degrees of freedom
  articulation_buffer.py     internal preparation surface
  selection.py               release/initiation pressure
  correction.py              residual/error channel
  skill_metrics.py           entropy, refinement, equivalence, cost

runtime/motor/
  tick_adapter.py            motor-learning step integration
  release_pipeline.py        trace -> actuator event flow
  reafference.py             UTD action -> UTE consequence handoff

io/actuators/
  keyboard.py                text/keyboard device pathway
  text_surface.py            renderer as witness surface, not author
```

## Core invariant

The model learns to use a fixed external device basis. The device basis does not grow from input history.

Bad:

```text
new word seen -> output alphabet expands -> model can now say word
```

Good:

```text
fixed keyboard/grapheme/scancode device basis
  -> runtime forms actuator traces over that basis
  -> visible output emerges through execution and feedback
```

## First accepted output path

The first motor pathway can be text-like, but it must be implemented as actuator control over a bounded device surface. The renderer may show text, but it may not author, complete, normalize, or repair text.

## Minimum telemetry chain

Every released action should be traceable as:

```text
internal metric state
  -> articulation trace update
  -> release event
  -> actuator event
  -> rendered witness
  -> reafferent receptor event
  -> residual/correction event
```
