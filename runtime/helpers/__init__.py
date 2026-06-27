"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.


Runtime helpers package.

Helpers exposed here support runtime orchestration only. Output authorship,
macro emission, and decoder-style speaking helpers are intentionally absent.
"""

from __future__ import annotations

# Modularized helper implementations (explicit re-exports)
from .engram import maybe_load_engram, derive_start_step
from .ingest import process_messages
from .checkpointing import save_tick_checkpoint

__all__ = [
    "maybe_load_engram",
    "derive_start_step",
    "process_messages",
    "save_tick_checkpoint",
]
