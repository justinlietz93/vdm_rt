"""
Reaching overlay (additive, inspectable, toggleable).

Justin's trace_to_posture_projection is intentionally conservative and does not
populate the "reaching" axes the coax gate keys on (curiosity, search,
incompletion, closure_gap, need, approach, novelty) nor the heavy-shut axes
(overload, saturation, calm). This overlay derives ONLY those missing axes, from
the same trace evidence already in the rows. It does not touch the base
projection; project_window merges the two.

Every rule is named in RULES and can be zeroed individually. Nothing here is a
relabel of an existing axis -- each rule cites the specific in-window evidence it
reads.

Rules
  unwitnessed_release  release_score > .45 on a non-witness tick = a reach that
                       did not land = an open closure.
                       -> closure_gap, search, need, incompletion
  unresolved_compare   COMPARE active but MERGE absent in the window = comparison
                       that did not resolve. -> search, curiosity, interest
  novel_unrecognized   comparison present while recognition + familiarity stay
                       low = encountering without matching. -> novelty, curiosity,
                       interest, approach, attention
  saturation_load      sustained high gate_pressure with wide active-op spread and
                       no witness close = the field is loaded. -> saturation,
                       overload, tension
  settled_calm         low mean gate_pressure with a clean witness close = nothing
                       is being reached for. -> calm, stability
"""
from __future__ import annotations
import math

# coefficients kept small and explicit; tune against real runs
RULES = {
    "unwitnessed_release": True,
    "unresolved_compare": True,
    "novel_unrecognized": True,
    "saturation_load": True,
    "settled_calm": True,
}


def _f(row, key, default=0.0):
    try:
        return float(row.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _ops(row):
    return str(row.get("active_ops", "") or "").upper()


def _is_witness(row, col_witnesses):
    w = str(row.get(col_witnesses, "") or "").strip()
    return bool(w) and w.lower() not in ("[]", "none")


def reaching_overlay(rows, cfg) -> dict[str, float]:
    out: dict[str, float] = {}
    if not rows:
        return out

    def add(axis, amt):
        out[axis] = max(0.0, min(1.0, out.get(axis, 0.0) + amt))

    n = len(rows)
    gate_vals, op_widths = [], []
    saw_merge = "MERGE" in " ".join(_ops(r) for r in rows)
    saw_compare = False
    unwit_release = 0.0
    recognition_proxy = 0.0  # SELECT density ~ recognition pressure in base proj

    for r in rows:
        ops = _ops(r)
        gate_vals.append(_f(r, cfg.col_gate))
        op_widths.append(len([t for t in ops.split() if t]))
        if "COMPARE" in ops:
            saw_compare = True
        if "SELECT" in ops:
            recognition_proxy += 1.0
        rel = _f(r, cfg.col_release)
        if rel > 0.45 and not _is_witness(r, cfg.col_witnesses):
            unwit_release += rel

    mean_gate = sum(gate_vals) / n
    mean_width = sum(op_widths) / n
    final = rows[-1]
    final_witness = _is_witness(final, cfg.col_witnesses)
    recognition_density = recognition_proxy / n
    familiar = (rows[-1].get(cfg.col_atom, "") ==
                (rows[-2].get(cfg.col_atom, "") if n > 1 else None))

    # --- rules ---
    if RULES["unwitnessed_release"] and unwit_release > 0.25:
        s = min(1.0, unwit_release / max(1.0, n * 0.5))
        add("closure_gap", 0.40 * s)
        add("search", 0.30 * s)
        add("need", 0.22 * s)
        add("incompletion", 0.18 * s)

    if RULES["unresolved_compare"] and saw_compare and not saw_merge:
        add("search", 0.22)
        add("curiosity", 0.16)
        add("interest", 0.14)

    if (RULES["novel_unrecognized"] and saw_compare
            and recognition_density < 0.5 and not familiar):
        s = 1.0 - recognition_density
        add("novelty", 0.30 * s)
        add("curiosity", 0.24 * s)
        add("interest", 0.18 * s)
        add("approach", 0.16 * s)
        add("attention", 0.12 * s)

    if RULES["saturation_load"] and not final_witness:
        load = max(0.0, (mean_gate - 0.6)) * (1.0 - math.exp(-mean_width / 8.0))
        if load > 0.05:
            add("saturation", min(0.6, 1.2 * load))
            add("overload", min(0.5, 0.9 * load))
            add("tension", min(0.4, 0.7 * load))

    if RULES["settled_calm"] and final_witness and mean_gate < 0.35:
        add("calm", 0.30)
        add("stability", 0.20)

    return out
