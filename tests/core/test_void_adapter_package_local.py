from __future__ import annotations

import numpy as np

from vdm_rt.core.void_dynamics_adapter import get_domain_modulation, universal_void_dynamics


def test_void_adapter_uses_retained_package_local_equations():
    w = np.array([0.1, 0.5, 0.9], dtype=float)
    out = universal_void_dynamics(w, t=1, domain_modulation=1.0, use_time_dynamics=False)
    assert out.shape == w.shape
    assert np.isfinite(out).all()


def test_domain_modulation_resolves_without_external_top_level_files():
    value = get_domain_modulation("biology_consciousness")
    assert isinstance(value, float)
    assert value > 0.0
