"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles. Commercial use requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""

from __future__ import annotations

"""
Runtime emitters initialization (MacroEmitter, ThoughtEmitter).

Behavior:
- Mirrors Nexus inline initialization exactly:
  * MacroEmitter path priority: config emitters.utd_out, utd.path,
    then <run_dir>/utd_events.jsonl
  * ThoughtEmitter enabled only when config emitters.enable_thoughts is true.
- Returns (macro_emitter_or_None, thought_emitter_or_None)
- No logging or file writes here (pure construction).
"""

from typing import Any, Callable, Optional, Tuple
import os

from vdm_rt.config import config_bool, config_str
# IO-layer actuators (allowed in runtime layer)
from vdm_rt.io.actuators.macros import MacroEmitter
from vdm_rt.io.actuators.thoughts import ThoughtEmitter


def initialize_emitters(
    utd: Any,
    run_dir: str,
    why_provider: Callable[[], dict],
) -> Tuple[Optional[MacroEmitter], Optional[ThoughtEmitter]]:
    """
    Create MacroEmitter and ThoughtEmitter with legacy-equivalent configuration.
    """
    macro: Optional[MacroEmitter] = None
    thoughts: Optional[ThoughtEmitter] = None

    # Macro emitter (write-only; respects configured override if set)
    try:
        out_path = config_str("emitters.utd_out", "").strip() or getattr(utd, "path", None) or os.path.join(run_dir, "utd_events.jsonl")
        macro = MacroEmitter(path=str(out_path), why_provider=why_provider)
    except Exception:
        macro = None

    # Introspection Ledger (emit-only), behind config flag.
    try:
        if config_bool("emitters.enable_thoughts", False):
            th_path = config_str("emitters.thought_out", "").strip() or os.path.join(run_dir, "thoughts.ndjson")
            thoughts = ThoughtEmitter(path=str(th_path), why=why_provider)
    except Exception:
        thoughts = None

    return macro, thoughts


__all__ = ["initialize_emitters"]
