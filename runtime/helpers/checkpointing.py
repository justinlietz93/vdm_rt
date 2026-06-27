"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.


Runtime helper: checkpointing and retention.

Provides:
- save_tick_checkpoint(): periodic H5 snapshot with retention.
"""

from __future__ import annotations

from typing import Any

from vdm_rt.core.memory import save_checkpoint
from vdm_rt.runtime.retention import prune_checkpoints as _prune_ckpt


def save_tick_checkpoint(nx: Any, step: int) -> None:
    """
    Save checkpoint and run retention policy when configured.

    Checkpoint creation is fatal: if configured persistence cannot write the
    retained state, the runtime must stop instead of silently continuing without
    the requested checkpoint. Retention cleanup remains best effort.
    """
    if not getattr(nx, "checkpoint_every", 0):
        return
    if (int(step) % int(nx.checkpoint_every)) != 0 or int(step) <= 0:
        return

    path = save_checkpoint(
        nx.run_dir,
        int(step),
        nx.connectome,
        fmt=getattr(nx, "checkpoint_format", "h5") or "h5",
        adc=getattr(nx, "adc", None),
    )
    try:
        nx.logger.info("checkpoint_saved", extra={"extra": {"path": str(path), "step": int(step)}})
    except Exception:
        pass

    if int(getattr(nx, "checkpoint_keep", 0)) > 0:
        try:
            summary = _prune_ckpt(nx.run_dir, keep=int(nx.checkpoint_keep), last_path=path)
            try:
                nx.logger.info("checkpoint_retention", extra={"extra": summary})
            except Exception:
                pass
        except Exception:
            pass


__all__ = ["save_tick_checkpoint"]
