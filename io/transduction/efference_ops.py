from __future__ import annotations

from typing import Any, Dict


SELECTOR_OP_LABELS = {
    "OP_0000": "SELECT",
    "OP_0001": "HOLD",
    "OP_0002": "RELEASE",
    "OP_0003": "INHIBIT",
    "OP_0004": "ADVANCE",
    "OP_0005": "RETREAT",
    "OP_0006": "SPLIT",
    "OP_0007": "MERGE",
    "OP_0008": "AMPLIFY",
    "OP_0009": "DAMP",
    "OP_0010": "COMPARE",
    "OP_0011": "CORRECT",
    "OP_0012": "COMMIT",
    "OP_0013": "ABORT",
}


def label_selector_trace_row(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    for key in ("active_ops", "commands"):
        text = str(out.get(key, ""))
        for op_id, label in SELECTOR_OP_LABELS.items():
            text = text.replace(op_id, label)
        out[key] = text
    return out
