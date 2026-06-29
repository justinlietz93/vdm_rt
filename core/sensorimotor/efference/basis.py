from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from vdm_rt.core.sensorimotor.basis import deterministic_group, short_hash_text


DEFAULT_OPERATIONS = tuple(f"OP_{i:04d}" for i in range(14))
DEFAULT_LANES = tuple(f"LANE_{i:04d}" for i in range(8))


@dataclass(frozen=True)
class FixedEfferenceBasis:
    """Sparse fixed operation/lane basis for agnostic efference traces."""

    n: int
    group_size: int
    salt: str
    operations: tuple[str, ...] = DEFAULT_OPERATIONS
    lanes: tuple[str, ...] = DEFAULT_LANES

    def op_groups(self) -> Dict[str, List[int]]:
        return {
            op: deterministic_group(f"efference_op:{op}", self.n, self.group_size, self.salt)
            for op in self.operations
        }

    def lane_groups(self) -> Dict[str, List[int]]:
        return {
            lane: deterministic_group(f"efference_lane:{lane}", self.n, self.group_size, self.salt)
            for lane in self.lanes
        }

    def identity(self) -> str:
        raw = "|".join(
            [
                str(int(self.n)),
                str(int(self.group_size)),
                self.salt,
                ",".join(self.operations),
                ",".join(self.lanes),
            ]
        )
        return short_hash_text(raw)


def reverse_index(groups: Dict[str, Iterable[int]]) -> Dict[int, List[str]]:
    out: Dict[int, List[str]] = {}
    for name, nodes in groups.items():
        for node in nodes:
            out.setdefault(int(node), []).append(str(name))
    return out
