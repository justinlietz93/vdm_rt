---
title: Sensorimotor Loop Glossary
status: draft
owner: runtime-core
source_authority: docs/pages/architecture/motor-learning-system.md
summary: Definitions for the VDM sensorimotor loop and its IO, transduction, afference, efference, and reafference boundaries.
---

# VDM Sensorimotor Feedback Loop Glossary

## Boundary Rules

These rules apply to every layer in this glossary.

- **Endogenous model time is preserved.** Wall-clock fields may be logged as provenance, but they must not become the model clock, release driver, aperture driver, learning signal, or comparison axis.
- **No dense scans in live runtime.** Live sensorimotor code consumes sparse events, bounded traces, existing telemetry snapshots, and explicit bus observations. Full graph/vector scans belong only in offline analysis.
- **IO is core-opaque.** `io/` packages inbound and outbound channel payloads. It does not import, inspect, or interpret `core/` state.
- **Transduction is fixed-basis packaging.** Transduction maps between concrete hardware channels and fixed model indices. It does not grow vocabularies, author content, or infer semantic meaning.

## 1. Input/Output Layer (`io/`)

The hardware/simulator port layer for asynchronous buffering and stream serialization.

- `utd.py` (Universal Transduction Device): outbound actuator port. It receives concrete, channel-specific payloads prepared by runtime/transduction and fires them to physical or simulated actuators. It does not author output and does not inspect core internals.
- `ute.py` (Universal Temporal Encoder): inbound receptor port. It captures raw receptor events into a queue and records the receptor stream to `motor_traces.jsonl.zst`. It does not classify core state or drive model timing from wall time.

## 2. Transduction Layer (`io/transduction/`)

The hardware packaging layer between concrete channels/pins and abstract fixed model indices.

- `efference.py`: outbound translator. It maps abstract motor activation packets onto finite physical actuator channels expected by the target device.
- `afference.py`: inbound translator. It maps raw receptor packets from `ute.py` onto fixed receptor-node indices.
- `reafference.py`: self-consequence interceptor. It labels sensor telemetry caused by the system's own actuator movement so runtime can route it into the reafference loop.

This layer knows device channels and fixed mappings. It does not know connectome topology, ADC, SIE, B1, void walkers, territories, or motor-learning internals.

## 3. Core Sensorimotor Module (`core/sensorimotor/`)

The VDM-native sensorimotor layer. It defines fixed index/basis boundaries and endogenous timing boundaries for self-organizing sensorimotor dynamics.

## A. Efference Directory (`efference/`)

Outgoing motor intention and actuator-trace preparation.

- `basis.py`: fixed abstract motor primitive basis and output node groups. The basis is device-owned and cannot grow from input history.
- `trace.py`: sparse chronological trace of outgoing motor activations, primitive pressure, ordering, and trace identity. It records emitted/active events, not dense full-vector state.
- `observer.py`: event-triggered telemetry copier. At witness release, it copies the already-available efferent telemetry snapshot and stores it under a trace/pairing id. When the matching reafferent event returns, it pairs that later telemetry snapshot for offline analysis. It does not scan adjacency, compute graph metrics, poll core internals, or influence runtime behavior.

## B. Reafference Directory (`reafference/`)

Self-consequence tracking for how the model responds to its own actions.

- `loop_basis.py`: fixed pairing handles across the closed-loop pathway, such as motor trace id to receptor consequence id.
- `loop_trace.py`: sparse timeline of self-generated action consequences and the matched telemetry snapshots.
- `observation.py`: offline analysis surface for paired efferent/reafferent snapshots. Cross-correlations, propagation latencies, and body-schema analyses are derived from stored event pairs, not live dense scans.

## C. Afference Directory (`afference/`)

Incoming receptor stimulation boundaries.

- `basis.py`: fixed receptor basis and entry-point node groups.
- `trace.py`: sparse chronological trace of incoming receptor indices and stimulation packets.
- `sensorimotor_aperture.py`: non-semantic gate over receptor throughput. It may use bounded, already-available activity telemetry; it must not scan all nodes/edges or assign semantic labels to channels.

## D. Preprocessing Sub-Module (`afference/preprocessing/`)

Signal conditioning before receptor packets reach the core sensorimotor boundary.

- `sensory_adaptation.py`: bounded nonlinear scaling to preserve dynamic range and reduce saturation from static inputs.
- `lateral_inhibition.py`: local contrast enhancement across fixed neighboring receptor channels. It operates over local channel neighborhoods, not global connectome structure.
