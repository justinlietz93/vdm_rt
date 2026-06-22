import importlib
import sys

import pytest


def _import_dense_connectome():
    importlib.invalidate_caches()
    if "vdm_rt.core.connectome" in sys.modules:
        del sys.modules["vdm_rt.core.connectome"]
    return importlib.import_module("vdm_rt.core.connectome")


def test_dense_connectome_module_is_absent_or_guarded_by_default(monkeypatch):
    monkeypatch.delenv("FORCE_DENSE", raising=False)
    try:
        _import_dense_connectome()
    except ModuleNotFoundError:
        return
    except RuntimeError:
        return
    raise AssertionError("Dense connectome module imported without guard")


def test_dense_branch_raises_when_forced_but_no_dense_policy(monkeypatch):
    monkeypatch.setenv("FORCE_DENSE", "1")
    monkeypatch.setenv("NO_DENSE_CONNECTOME", "1")
    monkeypatch.delenv("ALLOW_DENSE_VALIDATION", raising=False)

    try:
        mod = _import_dense_connectome()
    except ModuleNotFoundError:
        return

    C = mod.Connectome(N=64, k=8, structural_mode="dense")
    with pytest.raises(RuntimeError):
        C.step(t=0.0, domain_modulation=1.0, sie_drive=1.0, use_time_dynamics=True)
