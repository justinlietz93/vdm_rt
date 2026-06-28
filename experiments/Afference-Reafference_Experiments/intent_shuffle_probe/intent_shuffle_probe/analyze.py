"""
Analysis for the intent-handle-shuffle experiment.

Decides one thing: is VDM's gravitation toward restraint/stability coupled to
intact intent-handle structure, or invariant to it?

Verdict is read off projection-independent observables:
  - full-shuffle effect : track2 steady-state vs track1 steady-state.
  - switch effect       : track3 post-switch vs pre-switch.
  - change-point scan    : where the stability signal actually steps, to confirm
                          the step lands at the manipulation tick (not drift).

If shuffling leaves the stability profile unmoved (both effects ~ 0, no step at
the switch), which neuron sits in which handle does not matter -> the gravitation
is not a structure-coupled choice -> MIRAGE. If shuffling degrades stability
(HOLD down, entropy up, gate variance up, witness rate up) with a step at the
switch -> COUPLED.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict

import numpy as np

from .observables import (load_tick_rows, compute_observables, window,
                          _ffloat, _active_ops)


def _hold_signal(rows):
    """Per-tick restraint signal: 1.0 if rank-1 op is HOLD else 0.0.
    Sensitive, projection-free, and the channel that moved 0.507 -> 0.039 at the
    factual->question switch, so it is the natural change-point carrier."""
    return np.array([1.0 if "HOLD" in _active_ops(r.get("active_ops", "")) else 0.0
                     for r in rows], dtype=float)


def change_point_scan(rows, min_seg=80):
    """Return (best_tick, score) maximizing the absolute difference of the HOLD
    signal mean across a split. score is the standardized step height."""
    ticks = np.array([_ffloat(r.get("tick")) for r in rows])
    sig = _hold_signal(rows)
    n = len(sig)
    best_t, best_score = None, 0.0
    for i in range(min_seg, n - min_seg):
        a, b = sig[:i], sig[i:]
        pooled = sig.std() + 1e-9
        score = abs(a.mean() - b.mean()) / pooled
        if score > best_score:
            best_score, best_t = score, float(ticks[i])
    return best_t, round(best_score, 4)


def _composite(obs):
    return obs.stability_index


def _bootstrap_pvalue(pre_rows, post_rows, n_boot=2000, seed=0):
    """Null: pre and post come from the same regime. Shuffle the tick labels and
    recompute the stability-index gap. p = fraction of |null gap| >= |observed|."""
    rng = np.random.default_rng(seed)
    obs_pre = _composite(compute_observables(pre_rows))
    obs_post = _composite(compute_observables(post_rows))
    observed = abs(obs_post - obs_pre)
    pool = pre_rows + post_rows
    k = len(pre_rows)
    idx = np.arange(len(pool))
    null = np.empty(n_boot)
    for b in range(n_boot):
        rng.shuffle(idx)
        a = [pool[i] for i in idx[:k]]
        c = [pool[i] for i in idx[k:]]
        null[b] = abs(_composite(compute_observables(c)) - _composite(compute_observables(a)))
    p = float((null >= observed).mean())
    return observed, p


@dataclass
class TrackSummary:
    name: str
    observables: dict


@dataclass
class Verdict:
    full_shuffle_stability_delta: float | None
    switch_stability_delta: float | None
    switch_pvalue: float | None
    change_point_tick: float | None
    change_point_score: float | None
    expected_switch_tick: int | None
    reading: str


def steady_state(rows, frac=0.4):
    """Last `frac` of the run, to drop warm-in transient."""
    n = len(rows)
    return rows[int(n * (1 - frac)):]


def analyze(track1_dir=None, track2_dir=None, track3_dir=None,
            switch_tick=1000, window_w=300, seed=0):
    out = {"tracks": {}, "verdict": None}

    t1 = t2 = None
    if track1_dir:
        r1 = load_tick_rows(track1_dir)
        t1 = compute_observables(steady_state(r1))
        out["tracks"]["track1_baseline"] = TrackSummary("track1_baseline", t1.to_dict()).__dict__
    if track2_dir:
        r2 = load_tick_rows(track2_dir)
        t2 = compute_observables(steady_state(r2))
        out["tracks"]["track2_full_shuffle"] = TrackSummary("track2_full_shuffle", t2.to_dict()).__dict__

    full_delta = None
    if t1 and t2:
        full_delta = round(t2.stability_index - t1.stability_index, 4)

    switch_delta = pval = cp_tick = cp_score = None
    if track3_dir:
        r3 = load_tick_rows(track3_dir)
        pre = window(r3, switch_tick - window_w, switch_tick)
        post = window(r3, switch_tick, switch_tick + window_w)
        o_pre = compute_observables(pre)
        o_post = compute_observables(post)
        out["tracks"]["track3_pre_switch"] = TrackSummary("track3_pre_switch", o_pre.to_dict()).__dict__
        out["tracks"]["track3_post_switch"] = TrackSummary("track3_post_switch", o_post.to_dict()).__dict__
        switch_delta = round(o_post.stability_index - o_pre.stability_index, 4)
        observed, pval = _bootstrap_pvalue(pre, post, seed=seed)
        cp_tick, cp_score = change_point_scan(r3)

    # reading
    reading = _read_verdict(full_delta, switch_delta, pval, cp_tick, switch_tick)
    out["verdict"] = asdict(Verdict(
        full_shuffle_stability_delta=full_delta,
        switch_stability_delta=switch_delta,
        switch_pvalue=pval,
        change_point_tick=cp_tick,
        change_point_score=cp_score,
        expected_switch_tick=switch_tick if track3_dir else None,
        reading=reading,
    ))
    return out


def _read_verdict(full_delta, switch_delta, pval, cp_tick, switch_tick,
                  null_band=0.05, near=120):
    parts = []
    coupled_signals = 0
    tested = 0
    if switch_delta is not None:
        tested += 1
        step_here = (cp_tick is not None and abs(cp_tick - switch_tick) <= near)
        sig = (pval is not None and pval < 0.05)
        if abs(switch_delta) > null_band and sig and step_here:
            coupled_signals += 1
            parts.append(
                f"track3 steps {switch_delta:+.3f} in stability at the switch "
                f"(change-point tick {cp_tick:.0f} vs expected {switch_tick}, p={pval:.3f}) -> coupled")
        else:
            parts.append(
                f"track3 shows no decisive step at the switch "
                f"(delta {switch_delta:+.3f}, change-point tick {cp_tick}, p={pval}) -> mirage-leaning")
    if full_delta is not None:
        tested += 1
        if abs(full_delta) > null_band:
            coupled_signals += 1
            parts.append(f"full shuffle moves steady-state stability {full_delta:+.3f} vs baseline -> coupled")
        else:
            parts.append(f"full shuffle leaves steady-state stability unmoved ({full_delta:+.3f}) -> mirage-leaning")
    if tested == 0:
        return "insufficient tracks: provide track3 (switch) and ideally track1+track2"
    if coupled_signals == tested and tested >= 1:
        head = "COUPLED: gravitation depends on intent-handle structure (a real choice, not a readout artifact). "
    elif coupled_signals == 0:
        head = "MIRAGE: stability profile invariant to intent-handle structure. "
    else:
        head = "MIXED: partial coupling; inspect which observable moved. "
    return head + " | ".join(parts)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--track1")
    ap.add_argument("--track2")
    ap.add_argument("--track3")
    ap.add_argument("--switch-tick", type=int, default=1000)
    ap.add_argument("--window", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    res = analyze(a.track1, a.track2, a.track3, a.switch_tick, a.window, a.seed)
    print(json.dumps(res, indent=2))
