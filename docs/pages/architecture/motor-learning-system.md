---
title: Motor-Learning System
status: active
owner: runtime-core
source_authority: docs/roadmap/neurobiology-upgrade/VDM_Motor_Learning_Decoder_Matrix_Addendum_v0.1.md
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

The IO plan owns the live layout:

```text
core/sensorimotor/
  efference/basis.py         fixed abstract operation/lane basis
  efference/trace.py         sparse trace pressure and release state
  efference/observer.py      passive witness-time telemetry copier
  reafference/loop_trace.py  action/consequence pairing handles
  afference/trace.py         sparse receptor-index trace

io/transduction/
  efference_keyboard.py      abstract packet -> keyboard grid packet
  afference.py               raw receptor units -> explicit receptor indices
  reafference.py             witness consequence -> receptor events
  reafferent_index.py        log-only 2048 posture projection

io/actuators/virtual_keyboard/
  key_matrix.py              fixed external keyboard surface
  endpoint.py                renderer/witness surface, not author
```

The runtime loop only invokes the attached `observe_nodes(...)` hook and UTD
port. It does not own the sensorimotor system.

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
