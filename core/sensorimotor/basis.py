from __future__ import annotations

import hashlib
from typing import Iterable, List


def stable_u64(label: str) -> int:
    return int.from_bytes(
        hashlib.blake2b(str(label).encode("utf-8"), digest_size=8).digest(),
        "little",
        signed=False,
    )


def deterministic_group(label: str, n: int, size: int, salt: str) -> List[int]:
    count = max(1, int(size))
    limit = max(1, int(n))
    out: List[int] = []
    seen: set[int] = set()
    j = 0
    while len(out) < count:
        idx = int(stable_u64(f"{salt}|{label}|{j}") % limit)
        j += 1
        if idx in seen:
            continue
        seen.add(idx)
        out.append(idx)
    return out


def short_hash_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:16]


def short_hash_ints(values: Iterable[int]) -> str:
    h = hashlib.sha256()
    for value in values:
        h.update(str(int(value)).encode("ascii"))
        h.update(b",")
    return h.hexdigest()[:16]
