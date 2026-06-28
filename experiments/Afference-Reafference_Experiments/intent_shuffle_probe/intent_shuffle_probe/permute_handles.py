"""
The permutation control: shuffle which neuron sits in which intent-handle slot.

This is the load-bearing manipulation. It is a pure relocation: the SAME set of
neuron locations, only the slot->neuron assignment is permuted. Nothing is added,
removed, reinitialized, or rescaled. That is what makes the control clean -- any
behavioral change under the shuffle is attributable to structure (which neuron is
which handle), not to a changed population or changed values.

ONE integration point you must confirm against your engine: the representation of
the intent-handle map. This module assumes it is expressible as an ordered
sequence handle_locations[slot] = neuron_location (a list, or a dict keyed by
slot). If your translator stores it differently (a matrix, a name->coord dict),
adapt extract()/inject() only; make_permutation/apply stay the same.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np


def make_permutation(n: int, seed: int, force_derangement: bool = True) -> list[int]:
    """A seeded permutation of range(n). With force_derangement, no slot keeps its
    original neuron (every handle is genuinely relocated), so the shuffle cannot
    accidentally leave structure partly intact."""
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n)
    if force_derangement and n > 1:
        # rotate any fixed points into their neighbor until none remain
        for _ in range(n):
            fixed = [i for i in range(n) if perm[i] == i]
            if not fixed:
                break
            for i in fixed:
                j = (i + 1) % n
                perm[i], perm[j] = perm[j], perm[i]
    return [int(x) for x in perm]


def apply_permutation(handle_locations, perm: list[int]):
    """Relocate: new[slot] = old[perm[slot]]. Preserves the multiset of locations."""
    assert len(perm) == len(handle_locations), "perm length must match handle count"
    return [handle_locations[perm[i]] for i in range(len(perm))]


def extract(handle_map):
    """Normalize a handle map (list or {slot: loc} dict) to an ordered list."""
    if isinstance(handle_map, dict):
        keys = sorted(handle_map, key=lambda k: int(k))
        return [handle_map[k] for k in keys], ("dict", keys)
    return list(handle_map), ("list", None)


def inject(shuffled_list, shape):
    kind, keys = shape
    if kind == "dict":
        return {k: shuffled_list[i] for i, k in enumerate(keys)}
    return shuffled_list


def shuffle_handle_map(handle_map, seed: int):
    locs, shape = extract(handle_map)
    perm = make_permutation(len(locs), seed)
    return inject(apply_permutation(locs, perm), shape), perm


def _self_test():
    # list form
    base = list(range(64))
    shuffled, perm = shuffle_handle_map(base, seed=7)
    assert sorted(shuffled) == sorted(base), "multiset not preserved"
    assert all(shuffled[i] != base[i] for i in range(len(base))), "derangement failed"
    # dict form
    dmap = {str(i): 1000 + i for i in range(32)}
    dshuf, _ = shuffle_handle_map(dmap, seed=7)
    assert sorted(dshuf.values()) == sorted(dmap.values())
    assert any(dshuf[k] != dmap[k] for k in dmap)
    # determinism
    again, _ = shuffle_handle_map(base, seed=7)
    assert again == shuffled
    print("permute_handles self-test OK (multiset preserved, derangement, deterministic)")


def main():
    ap = argparse.ArgumentParser(description="Shuffle an intent-handle map (pure relocation).")
    ap.add_argument("--in", dest="inp", help="JSON handle map (list or {slot: loc})")
    ap.add_argument("--out", help="where to write the shuffled map")
    ap.add_argument("--seed", type=int, default=20260627)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test or not a.inp:
        _self_test()
        return
    hm = json.loads(Path(a.inp).read_text())
    shuf, perm = shuffle_handle_map(hm, a.seed)
    out = a.out or (a.inp.rsplit(".", 1)[0] + f".shuffled_{a.seed}.json")
    Path(out).write_text(json.dumps(shuf, indent=2))
    Path(out + ".perm").write_text(json.dumps(perm))
    print(f"wrote {out} (and .perm). handles: {len(perm)}")


if __name__ == "__main__":
    main()
