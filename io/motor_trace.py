"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict

from vdm_rt.io.logging.rolling_jsonl import RollingZstdJsonlWriter


class MotorTraceLog:
    """
    Sensorimotor boundary trace.

    This is not the internal runtime dynamics log. It records receptor activity,
    efferent/stimulation handoff, afferent/reafferent reactions, actuator trace
    preparation, witness events, and UTD actuation events in one compressed JSONL
    stream: motor_traces.jsonl.zst.
    """

    def __init__(self, run_dir: str, run_start_wall_time_s: float | None = None):
        self.run_dir = str(run_dir)
        os.makedirs(self.run_dir, exist_ok=True)
        self.run_start_wall_time_s = (
            float(run_start_wall_time_s)
            if run_start_wall_time_s is not None
            else time.time()
        )
        self._log = RollingZstdJsonlWriter(
            os.path.join(self.run_dir, "motor_traces.jsonl")
        )
        self.path = self._log.base_path

    def set_run_clock(self, run_start_wall_time_s: float) -> None:
        self.run_start_wall_time_s = float(run_start_wall_time_s)

    def record(self, trace_kind: str, record: Dict[str, Any] | None = None) -> bool:
        try:
            rec = dict(record or {})
            rec["trace_kind"] = str(trace_kind)
            now = time.time()
            rec.setdefault("wall_time_s", now)
            rec.setdefault("ts", rec.get("wall_time_s", now))
            rec.setdefault(
                "run_elapsed_s",
                max(0.0, float(rec["wall_time_s"]) - self.run_start_wall_time_s),
            )
            self._log.write_record(rec)
            return True
        except Exception:
            return False

    def record_ute_input(self, record: Dict[str, Any]) -> bool:
        source = str(record.get("source", "")).strip().lower()
        if source in {"reafference", "afferent", "self_consequence"}:
            return self.record_afferent_reaction(record)
        return self.record("ute_input", record)

    def record_efferent_dynamics(self, record: Dict[str, Any]) -> bool:
        return self.record("efferent_dynamics", record)

    def record_stimulation(self, record: Dict[str, Any]) -> bool:
        return self.record("stimulation", record)

    def record_afferent_reaction(self, record: Dict[str, Any]) -> bool:
        return self.record("afferent_reaction", record)

    def record_actuator_trace(self, record: Dict[str, Any]) -> bool:
        return self.record("actuator_trace", record)

    def record_witness_event(self, record: Dict[str, Any]) -> bool:
        return self.record("witness_event", record)

    def record_utd_actuation(self, record: Dict[str, Any]) -> bool:
        return self.record("utd_actuation", record)


__all__ = ["MotorTraceLog"]
