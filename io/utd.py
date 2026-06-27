"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""
import json, os
from typing import Any, Dict

from vdm_rt.config import config_bool
from vdm_rt.io.logging.rolling_jsonl import RollingJsonlWriter
try:
    # Prefer zip spooler when available
    from vdm_rt.io.logging.rolling_jsonl import RollingZipJsonlWriter  # type: ignore
except Exception:
    RollingZipJsonlWriter = None  # type: ignore

class UTD:
    """Universal Transduction Device boundary.

    This port records explicit motor events only. It does not provide text
    emission, macro registration, sentence composition, or input echo.
    """
    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        os.makedirs(self.run_dir, exist_ok=True)
        self.path = os.path.join(self.run_dir, 'utd_events.jsonl')
        # Prefer zip-spooled writer to bound disk pressure; fallback to rolling JSONL
        use_zip = config_bool("logging.zip_spool", True)
        try:
            if use_zip and RollingZipJsonlWriter is not None:  # type: ignore
                self._writer = RollingZipJsonlWriter(self.path)  # type: ignore
            else:
                self._writer = RollingJsonlWriter(self.path)
        except Exception:
            # Safe fallback
            self._writer = RollingJsonlWriter(self.path)

    def emit_motor_event(self, event: Dict[str, Any]) -> bool:
        rec = {"type": "motor_event", "event": dict(event or {})}
        try:
            line = json.dumps(rec, ensure_ascii=False)
            self._writer.write_line(line)
            return True
        except Exception:
            return False

    def close(self):
        # RollingJsonlWriter does not keep a persistent file handle.
        return None
