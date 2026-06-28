"""
vdm_companion
=============

An asynchronous environmental companion that lives on VDM's afferent field.

It does not query the engine and does not scan the graph. It consumes the
pushed trace/witness/aperture stream VDM already emits, decides whether VDM is
in a receptive posture, and (when it is) places an under-determined stimulus
into VDM's input stream as a standing closure-gap that VDM can only resolve by
reaching toward the companion.

Coaxing phase only: no vector store, no knowledge retrieval, no curated answer.
The single question this phase answers is whether VDM, given the affordance,
starts orienting toward the companion on its own.

Design constraint inherited from package 06:
    coherent resolvable input -> VDM finds footing -> near-silence.
    Therefore the coax cannot be coherence. It must be an open structure.
"""
from .config import CompanionConfig
from .runtime import CompanionRuntime
from .channels import ReplayTraceSource, FileTailTraceSource, QueueFileAfferentSink

__all__ = [
    "CompanionConfig",
    "CompanionRuntime",
    "ReplayTraceSource",
    "FileTailTraceSource",
    "QueueFileAfferentSink",
]
