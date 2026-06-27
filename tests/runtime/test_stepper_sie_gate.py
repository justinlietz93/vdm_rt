from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from vdm_rt.runtime.stepper import SIEGateInputs, compute_step_and_metrics, select_sie_gate


class _SIE:
    def __init__(self, valence: float) -> None:
        self.valence = float(valence)
        self.calls: list[dict] = []

    def get_drive(self, **kwargs) -> dict:
        self.calls.append(dict(kwargs))
        return {
            "valence_01": self.valence,
            "total_reward": self.valence,
            "components": {},
        }


class _Connectome:
    def __init__(self, cached_sie_v2: float, post_step_sie_v2: float) -> None:
        self.W = np.asarray([0.25, 0.5, 0.75], dtype=np.float32)
        self._last_sie2_valence = float(cached_sie_v2)
        self._post_step_sie_v2 = float(post_step_sie_v2)
        self.step_calls: list[dict] = []

    def active_edge_count(self) -> int:
        return 2

    def connected_components(self) -> int:
        return 1

    def cyclomatic_complexity(self) -> int:
        return 0

    def connectome_entropy(self) -> float:
        return 0.0

    def step(self, t: float, domain_modulation: float, sie_drive: float, use_time_dynamics: bool) -> None:
        self.step_calls.append(
            {
                "t": float(t),
                "domain_modulation": float(domain_modulation),
                "sie_drive": float(sie_drive),
                "use_time_dynamics": bool(use_time_dynamics),
            }
        )
        self._last_sie2_valence = self._post_step_sie_v2


def test_stepper_uses_current_runtime_sie_and_cached_prior_sie_v2_for_gate() -> None:
    connectome = _Connectome(cached_sie_v2=0.8, post_step_sie_v2=0.1)
    nx = SimpleNamespace(
        N=4,
        connectome=connectome,
        sie=_SIE(valence=0.2),
        sie_target_var=0.15,
        dom_mod=1.25,
        use_time_dynamics=True,
        _prev_active_edges=None,
        _prev_vt_entropy=None,
        _last_vt_entropy=None,
    )

    metrics, drive = compute_step_and_metrics(nx, t=3.5, step=7)

    assert drive["valence_01"] == 0.2
    assert len(connectome.step_calls) == 1
    assert connectome.step_calls[0]["sie_drive"] == 0.8
    assert connectome._last_sie2_valence == 0.1
    assert metrics["sie_gate"] == 0.8
    assert metrics["sie_runtime_valence_01"] == 0.2
    assert metrics["sie_v2_cached_valence_01"] == 0.8


def test_stepper_uses_runtime_sie_when_it_exceeds_cached_sie_v2() -> None:
    connectome = _Connectome(cached_sie_v2=0.2, post_step_sie_v2=0.9)
    nx = SimpleNamespace(
        N=4,
        connectome=connectome,
        sie=_SIE(valence=0.7),
        sie_target_var=0.15,
        dom_mod=1.0,
        use_time_dynamics=True,
        _prev_active_edges=None,
        _prev_vt_entropy=None,
        _last_vt_entropy=None,
    )

    metrics, _drive = compute_step_and_metrics(nx, t=1.0, step=3)

    assert connectome.step_calls[0]["sie_drive"] == 0.7
    assert connectome._last_sie2_valence == 0.9
    assert metrics["sie_gate"] == 0.7
    assert metrics["sie_runtime_valence_01"] == 0.7
    assert metrics["sie_v2_cached_valence_01"] == 0.2


def test_sie_gate_policy_clamps_existing_max_relationship() -> None:
    decision = select_sie_gate(
        SIEGateInputs(
            runtime_valence_01=1.4,
            cached_sie_v2_valence_01=-0.5,
        )
    )

    assert decision.gate == 1.0
    assert decision.runtime_valence_01 == 1.0
    assert decision.cached_sie_v2_valence_01 == 0.0
