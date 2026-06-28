"""
Projection-independent observables from a VDM tick_rows stream.

Everything here is read straight off the engine output. No posture projection,
no reaching overlay, nothing this experiment's verdict should not rest on. The
op dominance is the rank-1 fraction in top_ops, which reproduces the
summary_by_phase_kind op-rate scale (factual_exposure HOLD ~ 0.5, question ~ 0.04).

Observables per window:
    witness_rate    fraction of ticks that closed a witness         (quiet vs active)
    gate_mean       mean gate_pressure                              (drive)
    gate_var        variance of gate_pressure                       (stability)
    release_mean    mean release_score
    op_<NAME>       rank-1 fraction for HOLD/SELECT/RELEASE/...      (restraint, attention, ...)
    op_entropy      Shannon entropy of the rank-1 op distribution   (settledness; low = settled)
    stability_index composite, z-free, in roughly [-1, 1]           (high = settled/restrained/quiet)
"""
from __future__ import annotations
import ast
import csv
import math
from dataclasses import dataclass, asdict
from pathlib import Path

KEY_OPS = ("HOLD", "SELECT", "RELEASE", "INHIBIT", "CORRECT", "ADVANCE",
           "ABORT", "COMPARE", "MERGE", "DAMP", "AMPLIFY")


def _active_ops(cell: str):
    return (cell or "").split()


def load_tick_rows(run_dir) -> list[dict]:
    p = Path(run_dir) / "tick_rows.csv"
    return list(csv.DictReader(p.open(encoding="utf-8")))


def _ffloat(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


@dataclass
class Observables:
    n_ticks: int
    witness_rate: float
    gate_mean: float
    gate_var: float
    release_mean: float
    op_rates: dict
    op_entropy: float
    stability_index: float

    def to_dict(self):
        d = asdict(self)
        return d


def compute_observables(rows: list[dict]) -> Observables:
    n = len(rows)
    if n == 0:
        return Observables(0, 0, 0, 0, 0, {k: 0.0 for k in KEY_OPS}, 0, 0)
    gates = [_ffloat(r.get("gate_pressure")) for r in rows]
    rels = [_ffloat(r.get("release_score")) for r in rows]
    gate_mean = sum(gates) / n
    gate_var = sum((g - gate_mean) ** 2 for g in gates) / n
    wit = sum(
        1 for r in rows
        if str(r.get("witnesses", "") or "").strip()
        and str(r.get("witnesses", "")).strip().lower() not in ("[]", "none")
    )
    counts = {k: 0 for k in KEY_OPS}
    dist = {}
    for r in rows:
        ops = _active_ops(r.get("active_ops", ""))
        for op in ops:
            dist[op] = dist.get(op, 0) + 1
            if op in counts:
                counts[op] += 1
    op_rates = {k: counts[k] / n for k in KEY_OPS}
    # entropy of the op presence distribution (settledness; concentrated = low)
    total_presence = sum(dist.values())
    ent = 0.0
    if total_presence:
        for c in dist.values():
            p = c / total_presence
            ent -= p * math.log(p + 1e-12)
    # composite stability: restrained (HOLD high), settled (low entropy),
    # steady (low gate variance), quiet (low witness rate). Scaled to ~[-1,1].
    hold = op_rates["HOLD"]
    churn = op_rates["INHIBIT"] + op_rates["CORRECT"] + op_rates["ADVANCE"] + op_rates["ABORT"]
    ent_norm = ent / math.log(len(KEY_OPS) + 2)          # ~[0,1]
    gate_var_norm = min(1.0, gate_var / 0.25)             # 0.25 ~ a loud var
    wit_norm = min(1.0, wit / n / 0.02)                  # 0.02 ~ a busy witness rate
    stability_index = (
        0.40 * (hold - churn)
        + 0.25 * (1.0 - ent_norm)
        + 0.20 * (1.0 - gate_var_norm)
        + 0.15 * (1.0 - wit_norm)
    )
    return Observables(
        n_ticks=n,
        witness_rate=round(wit / n, 6),
        gate_mean=round(gate_mean, 6),
        gate_var=round(gate_var, 6),
        release_mean=round(sum(rels) / n, 6),
        op_rates={k: round(v, 4) for k, v in op_rates.items()},
        op_entropy=round(ent, 4),
        stability_index=round(stability_index, 4),
    )


def window(rows: list[dict], lo: int, hi: int, tick_key="tick") -> list[dict]:
    out = []
    for r in rows:
        t = _ffloat(r.get(tick_key))
        if lo <= t < hi:
            out.append(r)
    return out
