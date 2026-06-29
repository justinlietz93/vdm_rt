from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List


AXES = (
    "attention",
    "salience",
    "valence",
    "intensity",
    "certainty",
    "confidence",
    "doubt",
    "uncertainty",
    "coherence",
    "ambiguity",
    "novelty",
    "familiarity",
    "memory",
    "recognition",
    "confirmation",
    "realization",
    "clarity",
    "surprise",
    "curiosity",
    "interest",
    "engagement",
    "search",
    "need",
    "comparison",
    "similarity",
    "difference",
    "connection",
    "separation",
    "ordering",
    "containment",
    "boundary",
    "completion",
    "incompletion",
    "closure_gap",
    "repair",
    "correction",
    "mismatch",
    "conflict",
    "rejection",
    "acceptance",
    "restraint",
    "hesitation",
    "readiness",
    "commitment",
    "persistence",
    "release_pressure",
    "approach",
    "avoidance",
    "withdrawal",
    "overload",
    "calm",
    "tension",
    "urgency",
    "relief",
    "friction",
    "importance",
    "agency",
    "orientation",
    "transition",
    "expectation",
    "saturation",
    "stability",
    "instability",
    "alignment",
)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _add(axis: str, amount: float, out: Dict[str, float]) -> None:
    if axis in out:
        out[axis] = _clamp01(out[axis] + amount)


def _f(row: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default) or default)
    except Exception:
        return float(default)


def _has_op(row: Dict[str, Any], op: str) -> bool:
    text = " ".join(
        str(row.get(k, ""))
        for k in row.keys()
        if "op" in k.lower() or "active" in k.lower() or "cmd" in k.lower()
    )
    return op.upper() in text.upper()


def project_rows(rows: List[Dict[str, Any]], tau: float = 10.0) -> Dict[str, float]:
    out = {axis: 0.0 for axis in AXES}
    if not rows:
        return {}
    try:
        end_tick = int(float(rows[-1].get("tick", len(rows) - 1)))
    except Exception:
        end_tick = len(rows) - 1
    near_release_no_witness = 0.0
    last_input = rows[-1].get("input_id") or rows[-1].get("input") or ""
    prev_input = rows[-2].get("input_id") if len(rows) > 1 else None
    repeated_input = bool(prev_input and prev_input == last_input)
    for row in rows:
        try:
            tick = int(float(row.get("tick", 0)))
        except Exception:
            tick = 0
        weight = math.exp(-max(0, end_tick - tick) / max(1e-9, float(tau)))
        gate = _f(row, "gate_pressure")
        release = _f(row, "release_score")
        witness = bool(row.get("witness"))
        if release > 0.45 and not witness:
            near_release_no_witness += weight * release
        if _has_op(row, "SELECT"):
            _add("attention", 0.05 * weight, out)
            _add("recognition", 0.04 * weight, out)
            _add("comparison", 0.02 * weight, out)
        if _has_op(row, "COMPARE"):
            _add("comparison", 0.08 * weight, out)
            _add("uncertainty", 0.04 * weight, out)
            _add("difference", 0.03 * weight, out)
        if _has_op(row, "HOLD"):
            _add("restraint", 0.08 * weight, out)
            _add("hesitation", 0.05 * weight, out)
            _add("stability", 0.03 * weight, out)
        if _has_op(row, "RELEASE"):
            _add("release_pressure", 0.06 * weight, out)
            _add("transition", 0.04 * weight, out)
            _add("readiness", 0.03 * weight, out)
        if _has_op(row, "ADVANCE"):
            _add("readiness", 0.07 * weight, out)
            _add("transition", 0.05 * weight, out)
            _add("commitment", 0.03 * weight, out)
        if _has_op(row, "RETREAT"):
            _add("withdrawal", 0.08 * weight, out)
            _add("avoidance", 0.06 * weight, out)
            _add("hesitation", 0.04 * weight, out)
        if _has_op(row, "ABORT"):
            _add("rejection", 0.08 * weight, out)
            _add("restraint", 0.05 * weight, out)
            _add("mismatch", 0.04 * weight, out)
        if _has_op(row, "CORRECT"):
            _add("repair", 0.07 * weight, out)
            _add("correction", 0.07 * weight, out)
            _add("alignment", 0.03 * weight, out)
        if _has_op(row, "MERGE"):
            _add("connection", 0.07 * weight, out)
            _add("similarity", 0.04 * weight, out)
            _add("coherence", 0.03 * weight, out)
        if _has_op(row, "SPLIT"):
            _add("separation", 0.07 * weight, out)
            _add("boundary", 0.04 * weight, out)
            _add("difference", 0.04 * weight, out)
        if gate > 0.9:
            _add("intensity", 0.04 * weight * gate, out)
            _add("salience", 0.03 * weight * gate, out)
            _add("urgency", 0.03 * weight * gate, out)
        if release > 0.7:
            _add("readiness", 0.04 * weight * release, out)
            _add("completion", 0.02 * weight * release, out)
    if repeated_input:
        _add("familiarity", 0.22, out)
        _add("recognition", 0.20, out)
        _add("memory", 0.12, out)
    if near_release_no_witness > 0.25:
        _add("hesitation", 0.18, out)
        _add("restraint", 0.14, out)
        _add("release_pressure", 0.10, out)
    final = rows[-1]
    if _has_op(final, "SELECT") and _has_op(final, "RELEASE"):
        _add("recognition", 0.18, out)
        _add("readiness", 0.12, out)
    if _has_op(final, "HOLD") and _has_op(final, "RELEASE"):
        _add("restraint", 0.12, out)
        _add("confirmation", 0.08, out)
    if _has_op(final, "ADVANCE"):
        _add("readiness", 0.15, out)
        _add("transition", 0.10, out)
    if final.get("witness"):
        _add("confirmation", 0.18, out)
        _add("completion", 0.12, out)
        _add("confidence", 0.10, out)
    return {k: round(_clamp01(v), 6) for k, v in out.items() if v > 0}


class ReafferentPostureIndex:
    """Log-only 2048-style posture projection and optional bank query."""

    def __init__(self, bank_path: str | Path | None = None, k: int = 8, tau: float = 10.0) -> None:
        self.bank_path = self._resolve_bank_path(bank_path)
        self.k = int(k)
        self.tau = float(tau)
        self._bank: List[Dict[str, Any]] | None = None

    def _resolve_bank_path(self, path: str | Path | None) -> Path | None:
        if path is None or str(path).strip() == "":
            return None
        p = Path(path).expanduser()
        if p.is_dir():
            p = p / "utterance_bank_2048.jsonl"
        return p

    def project_and_query(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        axis = project_rows(rows, tau=self.tau)
        query = self.query(axis, k=self.k) if axis and self.bank_path else {
            "top_utterance": None,
            "rank_margin": None,
            "top_k": [],
        }
        return {
            "projection_kind": "2048_trace_to_posture_log_only",
            "axis_vector": axis,
            "top_utterance": query.get("top_utterance"),
            "rank_margin": query.get("rank_margin"),
            "top_k": query.get("top_k", [])[: self.k],
            "submitted_to_reafference": False,
        }

    def _load_bank(self) -> List[Dict[str, Any]]:
        if self._bank is not None:
            return self._bank
        if self.bank_path is None or not self.bank_path.exists():
            self._bank = []
            return self._bank
        self._bank = [
            json.loads(line)
            for line in self.bank_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return self._bank

    def query(self, axis_json: Dict[str, float], k: int = 8) -> Dict[str, Any]:
        qvec = _normalize(_vector(axis_json))
        scored = []
        for row in self._load_bank():
            axes = row.get("axes") if isinstance(row, dict) else None
            if not isinstance(axes, dict):
                continue
            score = _dot(_normalize(_vector(axes)), qvec)
            scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        out = []
        for rank, (score, row) in enumerate(scored[: int(k)], 1):
            out.append(
                {
                    "rank": rank,
                    "id": row.get("id"),
                    "utterance": row.get("utterance"),
                    "family": row.get("family"),
                    "leaf": row.get("leaf"),
                    "form": row.get("form"),
                    "strength": row.get("strength"),
                    "cosine": round(float(score), 6),
                    "distance": round(1.0 - float(score), 6),
                }
            )
        margin = out[0]["cosine"] - out[1]["cosine"] if len(out) >= 2 else None
        return {"top_utterance": out[0]["utterance"] if out else None, "rank_margin": margin, "top_k": out}


def _vector(axis_json: Dict[str, Any]) -> List[float]:
    return [float(axis_json.get(axis, 0.0) or 0.0) for axis in AXES]


def _normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(float(v) * float(v) for v in vec))
    if norm <= 0.0:
        return vec
    return [float(v) / norm for v in vec]


def _dot(a: Iterable[float], b: Iterable[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))
