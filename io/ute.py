"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""

import queue
import threading
from typing import Any, Dict

from vdm_rt.config import config_int

class UTE:
    """Universal Temporal Encoder.
    Queue-style receptor boundary.

    The old stdin/chat-inbox/ticker readers are intentionally absent. Tested
    receptor paths should enqueue explicit receptor events through push().
    """
    def __init__(
        self,
        queue_maxsize: int | None = None,
        poll_max_items: int | None = None,
    ):
        queue_size = config_int("ute.queue_maxsize", 1024) if queue_maxsize is None else int(queue_maxsize)
        self.q = queue.Queue(maxsize=max(1, queue_size))
        self._stop = threading.Event()
        self.poll_max_items = max(1, config_int("ute.poll_max_items", 32) if poll_max_items is None else int(poll_max_items))

    def start(self):
        return None

    def stop(self):
        self._stop.set()

    def push(self, event: Dict[str, Any]) -> bool:
        if self._stop.is_set():
            return False
        try:
            self.q.put_nowait(dict(event))
            return True
        except Exception:
            return False

    def poll(self, max_items=None):
        if max_items is None:
            max_items = self.poll_max_items
        out = []
        while len(out) < max_items:
            try:
                out.append(self.q.get_nowait())
            except queue.Empty:
                break
        return out
