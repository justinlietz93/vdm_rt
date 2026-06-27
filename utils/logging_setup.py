"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles. Commercial use requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""

import logging, json, os, sys, time

from vdm_rt.config import config_str


class JsonFormatter(logging.Formatter):
    def __init__(self, *args, run_start_wall_time_s=None, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.run_start_wall_time_s = float(run_start_wall_time_s)
        except Exception:
            self.run_start_wall_time_s = time.time()

    def format(self, record):
        now = time.time()
        base = {
            "wall_time_s": now,
            "ts": now,
            "run_elapsed_s": max(0.0, now - float(self.run_start_wall_time_s)),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        extra = record.__dict__.get("extra")
        if extra:
            base.update(extra)
            if "wall_time_s" in extra and "ts" not in extra:
                base["ts"] = base["wall_time_s"]
        return json.dumps(base, ensure_ascii=False)


def set_logger_run_start(logger, run_start_wall_time_s: float) -> None:
    """Align existing JsonFormatter instances to the current run clock."""
    for handler in getattr(logger, "handlers", []) or []:
        formatter = getattr(handler, "formatter", None)
        if isinstance(formatter, JsonFormatter):
            formatter.run_start_wall_time_s = float(run_start_wall_time_s)


def get_logger(name, log_file=None):
    """
    Structured JSON logger.

    When log_file is provided, prefer a bounded rolling JSONL handler that streams
    trimmed lines into timestamped archived segments under runs/<ts>/archived/<stamp>/.
    Falls back to a plain FileHandler if the rolling handler is unavailable.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # stdout stream handler (always on)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(JsonFormatter())
        logger.addHandler(sh)

    if log_file:
        resolved_log_file = os.path.abspath(log_file)
        has_file_sink = any(
            getattr(handler, "_vdm_rt_log_file", None) == resolved_log_file
            for handler in logger.handlers
        )
        if not has_file_sink:
            os.makedirs(os.path.dirname(resolved_log_file), exist_ok=True)
            compression = config_str("logging.compression", "zstd").strip().lower()
            if compression == "zstd":
                from vdm_rt.io.logging.rolling_jsonl import (
                    RollingZstdJsonlHandler as _RJHandler,
                )
                fh = _RJHandler(resolved_log_file)
            elif compression in {"none", "plain", "jsonl"}:
                from vdm_rt.io.logging.rolling_jsonl import (
                    RollingJsonlHandler as _RJHandler,
                )
                fh = _RJHandler(resolved_log_file)
            else:
                raise ValueError(f"Unsupported logging.compression value: {compression!r}")
            setattr(fh, "_vdm_rt_log_file", resolved_log_file)
            fh.setFormatter(JsonFormatter())
            logger.addHandler(fh)

    return logger
