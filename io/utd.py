"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""
import os
from typing import Any, Dict

from vdm_rt.io.logging.sensorimotor_trace import SensorimotorTraceLog


class UTD:
    """Universal Transduction Device boundary.

    This port records explicit motor events only. It does not provide text
    emission, macro registration, sentence composition, or input echo.
    Records are written to motor_traces.jsonl.zst as raw trace rows with
    trace_kind="utd_actuation".
    """
    def __init__(
        self,
        run_dir: str,
        run_start_wall_time_s: float | None = None,
        sensorimotor_trace: SensorimotorTraceLog | None = None,
    ):
        self.run_dir = run_dir
        os.makedirs(self.run_dir, exist_ok=True)
        self.sensorimotor_trace = sensorimotor_trace or SensorimotorTraceLog(
            self.run_dir,
            run_start_wall_time_s=run_start_wall_time_s,
        )
        self.path = self.sensorimotor_trace.path

    def set_run_clock(self, run_start_wall_time_s: float) -> None:
        self.sensorimotor_trace.set_run_clock(run_start_wall_time_s)

    def emit_motor_event(self, event: Dict[str, Any]) -> bool:
        try:
            rec = dict(event or {})
            return bool(self.sensorimotor_trace.record_utd_actuation(rec))
        except Exception:
            return False

    def close(self):
        return None
