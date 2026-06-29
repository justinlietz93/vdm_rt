from __future__ import annotations

import hashlib
from typing import Any, Dict, List


def _u64(label: str) -> int:
    return int.from_bytes(
        hashlib.blake2b(str(label).encode("utf-8"), digest_size=8).digest(),
        "little",
        signed=False,
    )


def _group(label: str, n: int, size: int, salt: str) -> List[int]:
    out: List[int] = []
    seen: set[int] = set()
    j = 0
    while len(out) < max(1, int(size)):
        idx = int(_u64(f"{salt}|{label}|{j}") % max(1, int(n)))
        j += 1
        if idx in seen:
            continue
        seen.add(idx)
        out.append(idx)
    return out


def short_hash_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:16]


class AfferenceTransducer:
    """
    IO-side raw receptor packaging.

    It turns externally sensed low-level units into explicit receptor indices.
    It preserves order and repetition by returning one event per sensed unit.
    """

    def __init__(self, n: int, group_size: int = 1, salt: str = "afference") -> None:
        self.n = int(n)
        self.group_size = int(max(1, group_size))
        self.salt = str(salt)

    def unit_indices(self, unit: str, position: int, stream_id: str = "") -> List[int]:
        label = f"unit:{stream_id}:pos:{int(position)}:raw:{unit}"
        return _group(label, self.n, self.group_size, self.salt)

    def text_events(
        self,
        text: str,
        *,
        tick: int,
        source: str,
        input_kind: str,
        motor_trace_id: str = "",
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        raw = "" if text is None else str(text)
        stream_id = short_hash_text(f"{motor_trace_id}|{tick}|{raw}")
        for pos, unit in enumerate(raw):
            out.append(
                {
                    "tick": int(tick),
                    "source": str(source),
                    "input_kind": str(input_kind),
                    "atom": unit,
                    "stim_indices": self.unit_indices(unit, pos, stream_id=stream_id),
                    "sequence_index": int(pos),
                    "sequence_len": int(len(raw)),
                    "stream_hash": stream_id,
                    "payload": {
                        "motor_trace_id": str(motor_trace_id),
                        "raw_output_hash": short_hash_text(raw),
                    },
                }
            )
        return out
