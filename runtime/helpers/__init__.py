"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.


Runtime helpers package (modularized).

Transitional re-exports:
- During migration away from the monolith [runtime_helpers.py](../runtime_helpers.py), we re-export
  its functions here to provide a stable import path:
    from vdm_rt.runtime.helpers import process_messages, emit_status_and_macro, ...
- New helpers live as separate modules under this package.
"""

from __future__ import annotations

# New, modular helpers
from .macro_board import register_macro_board  # re-export (modular)

# Modularized helper implementations (explicit re-exports)
from .engram import maybe_load_engram, derive_start_step
from .ingest import process_messages
from .smoke import maybe_smoke_tests
from .speak import maybe_auto_speak
from .emission import emit_status_and_macro
from .checkpointing import save_tick_checkpoint

__all__ = [
    # Transitional re-exports
    "register_macro_board",
    "maybe_load_engram",
    "derive_start_step",
    "process_messages",
    "maybe_smoke_tests",
    "maybe_auto_speak",
    "emit_status_and_macro",
    "save_tick_checkpoint",
]