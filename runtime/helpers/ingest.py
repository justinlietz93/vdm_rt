"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.


Runtime helper: message ingestion counters.

Provides:
- process_messages(): Counts inbound receptor messages without authoring output
  or mapping chat/stdin text into connectome stimulation.

Policy:
- Runtime helpers may import vdm_rt.io.* and vdm_rt.core.*.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Set, Tuple


_EXPLICIT_INDEX_KEYS = (
    "stim_indices",
    "stimulus_indices",
    "receptor_indices",
    "indices",
    "nodes",
)


def _coerce_explicit_indices(nx: Any, msg: Dict[str, Any]) -> Set[int]:
    out: Set[int] = set()
    try:
        n = int(getattr(nx, "N", 0))
    except Exception:
        n = 0
    for key in _EXPLICIT_INDEX_KEYS:
        raw = msg.get(key)
        if raw is None:
            continue
        if isinstance(raw, (str, bytes)):
            raw = [raw]
        try:
            iterator = iter(raw)
        except TypeError:
            iterator = iter([raw])
        for item in iterator:
            try:
                idx = int(item)
            except Exception:
                continue
            if idx < 0:
                continue
            if n > 0 and idx >= n:
                continue
            out.add(idx)
    return out


def process_messages(nx: Any, msgs: Iterable[Dict[str, Any]]) -> Tuple[int, Set[int], Dict[int, Any]]:
    """
    Process UTE messages:
      - Count text messages
      - Do not update lexical state
      - Do not map text into connectome indices
      - Accept only explicit receptor/stimulation node indices supplied by UTE
      - Do not echo input through UTD

    Returns: (ute_text_count, stim_idxs, tick_rev_map)
    """
    ute_text_count = 0
    stim_idxs: Set[int] = set()
    tick_rev_map: Dict[int, Any] = {}

    for m in msgs:
        try:
            if isinstance(m, dict) and m.get("type") == "text":
                ute_text_count += 1
            if isinstance(m, dict):
                indices = _coerce_explicit_indices(nx, m)
                if indices:
                    stim_idxs.update(indices)
                    symbol = (
                        m.get("atom")
                        or m.get("symbol")
                        or m.get("category")
                        or m.get("source")
                    )
                    if symbol is not None:
                        for idx in indices:
                            tick_rev_map[int(idx)] = symbol
        except Exception:
            # Fail-soft per message
            pass

    return ute_text_count, stim_idxs, tick_rev_map


__all__ = ["process_messages"]
