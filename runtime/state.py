"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles. Commercial use requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""

from __future__ import annotations

"""
RuntimeState: small, explicit runtime context container.

Goals:
- Provide a stable place for lightweight runtime-scoped state (tick counters, RNG seed, small ring buffers),
  independent of Nexus internals. This helps freeze the seam while migrating logic out of Nexus.
- No I/O, logging, or JSON formatting here. Pure Python data only.

Usage:
- Orchestrator/Nexus may optionally hold an instance to track tick/time and share small buffers
  across helpers (telemetry, auditors, scouts). This module does not perform any scheduling.

Constraints:
- Keep memory footprint small; do not store large tensors or model state.
- Pure utility; not required for existing runs (parity preserved when unused).
"""

from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Optional
from collections import deque
import time
import random

from vdm_rt.config import config_int


def _cfg_ring(key: str, default: int) -> int:
    return max(1, config_int(key, default))


@dataclass
class RuntimeRing:
    """
    Small bounded ring buffer for lightweight signals (e.g., recent 'why' ticks, scout stats).
    """
    maxlen: int = field(default_factory=lambda: _cfg_ring("runtime.buffers.ring_maxlen", 512))
    buf: Deque[Any] = field(default_factory=deque)

    def __post_init__(self) -> None:
        try:
            if self.buf.maxlen != int(self.maxlen):
                self.buf = deque(self.buf, maxlen=int(max(1, self.maxlen)))
        except Exception:
            self.buf = deque(maxlen=int(max(1, self.maxlen)))

    def append(self, item: Any) -> None:
        try:
            self.buf.append(item)
        except Exception:
            pass

    def snapshot(self) -> list:
        try:
            return list(self.buf)
        except Exception:
            return []


@dataclass
class RuntimeState:
    """
    Tiny runtime state tracking tick/time and a small set of buffers.
    """
    seed: int = 0
    tick: int = 0
    t0: float = field(default_factory=time.time)

    # Small rings available to helpers
    recent_why: RuntimeRing = field(default_factory=lambda: RuntimeRing(maxlen=_cfg_ring("runtime.buffers.recent_why_maxlen", 256)))
    recent_status: RuntimeRing = field(default_factory=lambda: RuntimeRing(maxlen=_cfg_ring("runtime.buffers.recent_status_maxlen", 128)))
    scout_stats: RuntimeRing = field(default_factory=lambda: RuntimeRing(maxlen=_cfg_ring("runtime.buffers.scout_stats_maxlen", 256)))
    auditor_stats: RuntimeRing = field(default_factory=lambda: RuntimeRing(maxlen=_cfg_ring("runtime.buffers.auditor_stats_maxlen", 128)))

    # Scratchpad for helpers (e.g., last budget metrics), kept minimal
    scratch: Dict[str, Any] = field(default_factory=dict)

    def now(self) -> float:
        try:
            return float(time.time() - self.t0)
        except Exception:
            return 0.0

    def rng(self) -> random.Random:
        try:
            # Derive a deterministic stream per tick based on base seed
            r = random.Random(int(self.seed) ^ int(self.tick))
            return r
        except Exception:
            return random.Random(0)
