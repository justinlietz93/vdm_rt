from __future__ import annotations

from typing import Any, Dict, List


class ReafferencePairTrace:
    """Agnostic action/consequence pairing ids for offline analysis."""

    def __init__(self, maxlen: int = 2048) -> None:
        self.maxlen = int(max(1, maxlen))
        self.count = 0
        self.rows: List[Dict[str, Any]] = []

    def pair(self, action_tick: int, consequence_tick: int, motor_trace_id: str) -> Dict[str, Any]:
        self.count += 1
        row = {
            "pair_id": f"p{self.count:06d}",
            "act_tick": int(action_tick),
            "consequence_tick": int(consequence_tick),
            "motor_trace_id": str(motor_trace_id),
        }
        self.rows.append(row)
        if len(self.rows) > self.maxlen:
            self.rows = self.rows[-self.maxlen :]
        return row
