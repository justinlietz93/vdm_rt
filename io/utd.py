"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""
import os
import time
from typing import Any, Dict

from vdm_rt.io.logging.rolling_jsonl import RollingZstdJsonlWriter


class UTD:
    """Universal Transduction Device boundary.

    This port records explicit motor events only. It does not provide text
    emission, macro registration, sentence composition, or input echo.
    Records are written directly to utd_events.jsonl.zst as raw event
    dictionaries, matching the Orthad selector-trace harness.
    """
    def __init__(self, run_dir: str, run_start_wall_time_s: float | None = None):
        self.run_dir = run_dir
        os.makedirs(self.run_dir, exist_ok=True)
        self.run_start_wall_time_s = (
            float(run_start_wall_time_s)
            if run_start_wall_time_s is not None
            else time.time()
        )
        self._log = RollingZstdJsonlWriter(
            os.path.join(self.run_dir, "utd_events.jsonl")
        )
        self.path = self._log.base_path

    def set_run_clock(self, run_start_wall_time_s: float) -> None:
        self.run_start_wall_time_s = float(run_start_wall_time_s)

    def emit_motor_event(self, event: Dict[str, Any]) -> bool:
        try:
            rec = dict(event or {})
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

    def close(self):
        return None
