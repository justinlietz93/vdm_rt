"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.


Redis status publishing helper (optional, bounded, void-faithful).

- Publishes compact runtime status metrics to a Redis Stream.
- No schedulers or background threads here; caller invokes once per tick from the runtime loop.
- Uses MAXLEN trimming to keep Redis bounded.

Enable via env:
  REDIS_URL=redis://127.0.0.1:6379/0
  ENABLE_REDIS_STATUS=1
  REDIS_STREAM_STATUS=fum:status         (optional; default shown)
  REDIS_STATUS_MAXLEN=2000               (approximate trim)
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import os
import json

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # lazy-fail if missing


def _truthy(x: Any) -> bool:
    try:
        if isinstance(x, (int, float, bool)):
            return bool(x)
        s = str(x).strip().lower()
        return s in ("1", "true", "yes", "on", "y", "t")
    except Exception:
        return False


def _get_client(nx: Any) -> Optional["redis.Redis"]:
    """
    Lazy-initialize and cache a Redis client on nx._redis_client.
    Returns None if redis-py is unavailable or the URL/env is missing.
    """
    if redis is None:
        return None
    try:
        cli = getattr(nx, "_redis_client", None)
        if cli is not None:
            return cli
    except Exception:
        cli = None
    try:
        url = os.getenv("REDIS_URL", "").strip()
        if not url:
            return None
        cli = redis.from_url(url, decode_responses=False)  # keep bytes payloads raw
        setattr(nx, "_redis_client", cli)
        return cli
    except Exception:
        return None


def maybe_publish_status_redis(nx: Any, metrics: Dict[str, Any], step: int) -> None:
    """
    Publish a compact status JSON to a bounded Redis Stream once per tick.

    Fields:
      stream = REDIS_STREAM_STATUS (default 'fum:status')
      MAXLEN  = REDIS_STATUS_MAXLEN (default 2000, approximate)
      entry   = { 'json': b'{"type":"status",...}' }
    """
    try:
        if not _truthy(os.getenv("ENABLE_REDIS_STATUS", "0")):
            return
        cli = _get_client(nx)
        if cli is None:
            return
        stream = os.getenv("REDIS_STREAM_STATUS", "fum:status")
        try:
            maxlen = int(os.getenv("REDIS_STATUS_MAXLEN", "2000"))
        except Exception:
            maxlen = 2000

        # Select a compact subset to keep bandwidth low
        m = metrics or {}
        payload = {
            "type": "status",
            "t": int(step),
            "phase": int(m.get("phase", 0)),
            "neurons": int(getattr(nx, "N", 0)),
            "b1_z": float(m.get("b1_z", 0.0)),
            "cohesion_components": int(m.get("cohesion_components", 0)),
            "vt_entropy": float(m.get("vt_entropy", 0.0)),
            "sie_valence_01": float(m.get("sie_valence_01", 0.0)),
            "sie_v2_valence_01": float(m.get("sie_v2_valence_01", m.get("sie_valence_01", 0.0))),
        }
        js = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        cli.xadd(stream, {"json": js}, maxlen=maxlen, approximate=True)
    except Exception:
        # Never disrupt runtime parity
        pass


__all__ = ["maybe_publish_status_redis"]