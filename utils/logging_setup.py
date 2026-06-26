"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles. Commercial use requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""

import logging, json, os, sys, time

from vdm_rt.config import config_bool


class JsonFormatter(logging.Formatter):
    def format(self, record):
        base = {
            "ts": time.time(),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        if record.__dict__.get("extra"):
            base.update(record.__dict__["extra"])
        return json.dumps(base, ensure_ascii=False)


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
            try:
                # The normal event logger follows the same visible zip-spool
                # choice as UTD and other JSONL writers.
                if config_bool("logging.zip_spool", True):
                    from vdm_rt.io.logging.rolling_jsonl import RollingZipJsonlHandler as _RJHandler  # type: ignore
                else:
                    from vdm_rt.io.logging.rolling_jsonl import RollingJsonlHandler as _RJHandler  # type: ignore
                fh = _RJHandler(resolved_log_file)
            except Exception:
                # Safe fallback: non-rolling file handler.
                fh = logging.FileHandler(resolved_log_file)
            setattr(fh, "_vdm_rt_log_file", resolved_log_file)
            fh.setFormatter(JsonFormatter())
            logger.addHandler(fh)

    return logger
