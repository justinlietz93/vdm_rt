"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles. Commercial use requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""

from __future__ import annotations

"""
Runtime stepper: compute one tick worth of core signals and advance the connectome.

Behavior:
- Mirrors Nexus inline logic exactly (move-only extraction).
- No logging or IO here. Pure computation + state updates on the nx object.
"""

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from vdm_rt.config import config_float
from vdm_rt.core.metrics import compute_metrics
from vdm_rt.core.signals import (
    compute_active_edge_density as _comp_density,
    compute_td_signal as _comp_td,
    compute_firing_var as _comp_fvar,
)


@dataclass(frozen=True)
class SIEGateInputs:
    """
    Inputs available at the pre-step gate boundary.

    The cached SIE v2 value is from a prior SparseConnectome.step() call. Fresh
    SIE v2 is produced after this gate is applied, so it cannot influence this
    tick without changing the runtime time relationship.
    """

    runtime_valence_01: float
    cached_sie_v2_valence_01: float


@dataclass(frozen=True)
class SIEGateDecision:
    gate: float
    runtime_valence_01: float
    cached_sie_v2_valence_01: float


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def select_sie_gate(inputs: SIEGateInputs) -> SIEGateDecision:
    """
    Preserve the current SIE gate relationship.

    Runtime SIE owns the current tick drive packet. SIE v2 contributes only as
    the cached intrinsic valence from the prior connectome step. The gate is the
    clamped maximum of those two values.
    """
    runtime_valence = _clamp01(inputs.runtime_valence_01)
    cached_sie_v2_valence = _clamp01(inputs.cached_sie_v2_valence_01)
    return SIEGateDecision(
        gate=_clamp01(max(runtime_valence, cached_sie_v2_valence)),
        runtime_valence_01=runtime_valence,
        cached_sie_v2_valence_01=cached_sie_v2_valence,
    )


def _read_cached_sie_v2_valence(connectome: Any) -> float:
    """
    Read the intrinsic SIE v2 valence produced by a prior connectome step.

    SparseConnectome computes SIE v2 after applying the current tick's gate,
    so this cached value is intentionally a prior-tick signal at this boundary.
    """
    try:
        return float(getattr(connectome, "_last_sie2_valence", 0.0))
    except Exception:
        return 0.0


def compute_step_and_metrics(nx: Any, t: float, step: int, novelty_scale: float = 1.0) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Compute density/TD/firing_var, derive SIE drive, step connectome, and build metrics.

    Returns (metrics_dict, sie_drive_dict) where sie_drive_dict matches Nexus.sie.get_drive(..) result.
    """
    m: Dict[str, Any] = {}
    drive: Dict[str, Any] = {}

    # 1) density from active edges
    try:
        E, density = _comp_density(getattr(nx, "connectome", None), int(getattr(nx, "N", 0)))
    except Exception:
        E, density = 0, 0.0

    # 2) TD-like signal from topology change + VT entropy delta
    try:
        prev_E = getattr(nx, "_prev_active_edges", E)
        vte_prev = getattr(nx, "_prev_vt_entropy", None)
        vte_last = getattr(nx, "_last_vt_entropy", None)
        td_signal = _comp_td(prev_E, E, vte_prev, vte_last)
        nx._prev_active_edges = E
    except Exception:
        td_signal = 0.0

    # 3) firing variability (HSI proxy)
    try:
        firing_var = _comp_fvar(getattr(nx, "connectome", None))
    except Exception:
        firing_var = None

    # 4) Runtime SIE drive. This is the current-tick global drive packet.
    try:
        drive = nx.sie.get_drive(
            W=None,
            external_signal=float(td_signal),
            time_step=int(step),
            firing_var=firing_var,
            target_var=float(getattr(nx, "sie_target_var", config_float("sie.target_var", 0.15))),
            density_override=density,
            novelty_scale=float(novelty_scale),
        )
        runtime_sie_valence = float(drive.get("valence_01", 1.0))
    except Exception:
        drive = {"valence_01": 1.0}
        runtime_sie_valence = 1.0

    # SIE v2 is computed inside SparseConnectome.step() after this gate is
    # applied. The value read here is therefore the prior intrinsic valence.
    cached_sie_v2_valence = _read_cached_sie_v2_valence(getattr(nx, "connectome", None))
    gate_decision = select_sie_gate(
        SIEGateInputs(
            runtime_valence_01=runtime_sie_valence,
            cached_sie_v2_valence_01=cached_sie_v2_valence,
        )
    )
    sie_gate = gate_decision.gate

    # 5) advance connectome
    try:
        nx.connectome.step(
            t,
            domain_modulation=float(getattr(nx, "dom_mod", 1.0)),
            sie_drive=sie_gate,
            use_time_dynamics=bool(getattr(nx, "use_time_dynamics", True)),
        )
    except Exception:
        pass

    # 6) metrics (scan-based, parity-preserving)
    try:
        m = compute_metrics(nx.connectome)
    except Exception:
        m = {}

    # Attach structural homeostasis and TD diagnostics
    try:
        m["homeostasis_pruned"] = int(getattr(nx.connectome, "_last_pruned_count", 0))
        m["homeostasis_bridged"] = int(getattr(nx.connectome, "_last_bridged_count", 0))
        m["active_edges"] = int(E)
        m["td_signal"] = float(td_signal)
        m["novelty_scale"] = float(novelty_scale)
        if firing_var is not None:
            m["firing_var"] = float(firing_var)
    except Exception:
        pass

    # Attach traversal findings
    try:
        findings = getattr(nx.connectome, "findings", None)
        if findings:
            m.update(findings)
    except Exception:
        pass

    # Expose sie_gate
    try:
        m["sie_gate"] = float(sie_gate)
        m["sie_runtime_valence_01"] = float(gate_decision.runtime_valence_01)
        m["sie_v2_cached_valence_01"] = float(gate_decision.cached_sie_v2_valence_01)
    except Exception:
        pass

    # Update VT entropy history for next tick's TD proxy
    try:
        nx._prev_vt_entropy = getattr(nx, "_last_vt_entropy", None)
        nx._last_vt_entropy = float(m.get("vt_entropy", 0.0))
    except Exception:
        pass

    return m, drive


__all__ = [
    "SIEGateDecision",
    "SIEGateInputs",
    "compute_step_and_metrics",
    "select_sie_gate",
]
