"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""

import os
import queue
import threading
from typing import Any, Dict

from vdm_rt.config import config_int
from vdm_rt.io.logging.sensorimotor_trace import SensorimotorTraceLog


class UTE:
    """Universal Temporal Encoder.
    Queue-style receptor boundary.

    The old stdin/chat-inbox/ticker readers are intentionally absent. Tested
    receptor paths should enqueue explicit receptor events through push().
    The observed receptor stream is recorded into motor_traces.jsonl.zst.
    """
    def __init__(
        self,
        run_dir: str | None = None,
        queue_maxsize: int | None = None,
        poll_max_items: int | None = None,
        sensorimotor_trace: SensorimotorTraceLog | None = None,
    ):
        self.run_dir = str(run_dir) if run_dir is not None else None
        if self.run_dir:
            os.makedirs(self.run_dir, exist_ok=True)
        self.sensorimotor_trace = sensorimotor_trace or (
            SensorimotorTraceLog(self.run_dir) if self.run_dir else None
        )
        self.input_stream_path = (
            self.sensorimotor_trace.path if self.sensorimotor_trace is not None else None
        )
        queue_size = (
            config_int("ute.queue_maxsize", 1024)
            if queue_maxsize is None
            else int(queue_maxsize)
        )
        self.q = queue.Queue(maxsize=max(1, queue_size))
        self._stop = threading.Event()
        self.poll_max_items = max(
            1,
            config_int("ute.poll_max_items", 32)
            if poll_max_items is None
            else int(poll_max_items),
        )

    def start(self):
        return None

    def stop(self):
        self._stop.set()

    def push(self, event: Dict[str, Any]) -> bool:
        if self._stop.is_set():
            return False
        rec = dict(event or {})
        try:
            self.q.put_nowait(rec)
        except Exception:
            return False
        self.record_input(rec)
        return True

    def record_input(self, record: Dict[str, Any]) -> bool:
        """Append a receptor-stream row to motor_traces.jsonl.zst."""
        if self.sensorimotor_trace is None:
            return False
        try:
            return self.sensorimotor_trace.record_ute_input(dict(record or {}))
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
