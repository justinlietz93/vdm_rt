# bus.py
"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles. Commercial use requires written permission from Justin K. Lietz.
See LICENSE file for full terms.

Lock-free announcement bus for void-walker observations (ADC input).

Blueprint alignment:
- Walkers traverse with void equations and publish compact Observation packets.
- ADC consumes only these announcements to maintain territories/boundaries incrementally.
- Cost is proportional to number of announcements, not to graph size.

Usage
- Producer (connectome walkers):
    bus.publish(observation)
- Consumer (Nexus/ADC loop):
    batch = bus.drain(max_items=2048)

Behavior
- Bounded deque with overwrite-on-full semantics (drop oldest) to keep runtime stable.
"""

from __future__ import annotations
from collections import deque
from typing import Deque, List, Any, Optional

from vdm_rt.config import config_int


class AnnounceBus:
    """Bounded, overwrite-on-full FIFO for Observation events."""
    def __init__(self, capacity: int | None = None):
        cap = config_int("bus.capacity", 65536) if capacity is None else int(capacity)
        self._q: Deque[Any] = deque(maxlen=int(max(1, cap)))

    @property
    def capacity(self) -> int:
        return int(self._q.maxlen or 0)

    def size(self) -> int:
        return len(self._q)

    def publish(self, obs: Any) -> None:
        """
        Append an event; when full, the oldest is dropped automatically.
        This keeps the system stable under load without backpressure deadlocks.
        """
        self._q.append(obs)

    def drain(self, max_items: int | None = None) -> List[Any]:
        """
        Pop up to max_items from the left, returning them in arrival order.
        """
        if max_items is None:
            max_items = config_int("bus.drain", 2048)
        n = min(int(max_items), len(self._q))
        out: List[Any] = []
        append = out.append
        for _ in range(n):
            append(self._q.popleft())
        return out

    def clear(self) -> None:
        self._q.clear()
