from __future__ import annotations

from typing import Any, Dict, Iterable, List

from vdm_rt.core.sensorimotor.basis import short_hash_ints


class AfferenceTrace:
    """Sparse receptor-index trace. It stores indices, not device semantics."""

    def __init__(self, maxlen: int = 2048) -> None:
        self.maxlen = int(max(1, maxlen))
        self.rows: List[Dict[str, Any]] = []

    def record(self, tick: int, indices: Iterable[int], trace_id: str | None = None) -> Dict[str, Any]:
        nodes = [int(i) for i in indices]
        row = {
            "tick": int(tick),
            "trace_id": str(trace_id or ""),
            "stim_count": int(len(nodes)),
            "stim_hash": short_hash_ints(nodes),
            "stim_nodes_sample": nodes[:32],
        }
        self.rows.append(row)
        if len(self.rows) > self.maxlen:
            self.rows = self.rows[-self.maxlen :]
        return row
