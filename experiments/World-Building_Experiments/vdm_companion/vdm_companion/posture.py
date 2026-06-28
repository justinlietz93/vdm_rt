"""
Inter-witness window construction and posture projection.

Reuses Justin's trace_to_posture_projection.project_rows unchanged. The only
work here is normalizing the real tick_rows column names into the generic shape
that projection expects:

    tick_rows has `witnesses` (plural id column) and `atom` (topic text).
    projection looks for `witness`/`witness_id` and `input_id`/`input`.

We map those so familiarity-from-repeated-topic and witness-confirmation fire
correctly, without touching the projection's evidence weights.
"""
from __future__ import annotations

from . import _posture_projection as proj
from .config import CompanionConfig
from .reaching import reaching_overlay


def normalize_row(row: dict, cfg: CompanionConfig) -> dict:
    """Return a shallow copy with projection-friendly keys added."""
    r = dict(row)
    w = str(row.get(cfg.col_witnesses, "") or "").strip()
    # projection treats any truthy witness/witness_id as a witness tick
    r["witness"] = w if w and w.lower() not in ("[]", "none") else ""
    # use the topic atom as input identity so repeated-topic -> familiarity
    r.setdefault("input_id", row.get(cfg.col_atom, "") or "")
    return r


def project_window(rows, cfg: CompanionConfig) -> dict[str, float]:
    """Project a window of tick rows (since the previous witness, through the
    current one) into a posture64_v1 axis vector. Base = Justin's conservative
    projection; the additive reaching overlay supplies the reaching/saturation
    axes the base does not populate (toggle via cfg.use_reaching_overlay)."""
    rows = list(rows)
    norm = [normalize_row(r, cfg) for r in rows]
    base = proj.project_rows(norm, tau=cfg.tau)
    if not cfg.use_reaching_overlay:
        return base
    overlay = reaching_overlay(rows, cfg)
    merged = dict(base)
    for k, v in overlay.items():
        merged[k] = max(0.0, min(1.0, merged.get(k, 0.0) + v))
    return {k: round(val, 6) for k, val in merged.items() if val > 0}


def axis_mass(posture: dict[str, float], axes) -> float:
    """Summed score over a named axis set (the receptive / shut / engagement
    aggregates the Logic gate and instrument compare against)."""
    return float(sum(posture.get(a, 0.0) for a in axes))
