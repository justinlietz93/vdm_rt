"""
Copyright © 2025 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""
from __future__ import annotations

import os
import re
import sys

from vdm_rt.control.process_manager import ProcessManager


def _stub_popen(monkeypatch):
    class FakeProc:
        def __init__(self, *args, **kwargs):
            self._poll = None
            self.stdin = None

        def poll(self):
            return self._poll

        def terminate(self):
            self._poll = 0

        def wait(self, timeout=None):
            return 0

        def kill(self):
            self._poll = -9

    monkeypatch.setattr(
        "vdm_rt.control.process_manager.subprocess.Popen",
        lambda *a, **k: FakeProc(),
        raising=True,
    )
    monkeypatch.setattr(
        "vdm_rt.control.process_manager.time.sleep",
        lambda s: None,
        raising=True,
    )


def test_start_defaults_run_dir_under_runs_root(tmp_path, monkeypatch):
    rr = tmp_path / "runs_root"
    rr.mkdir(parents=True, exist_ok=True)

    pm = ProcessManager(str(rr))
    recorded: dict = {}

    def fake_build_cmd(self, profile):
        recorded["profile"] = dict(profile)
        return [sys.executable, "-c", "print('noop')"]

    monkeypatch.setattr(ProcessManager, "_build_cmd", fake_build_cmd, raising=True)
    _stub_popen(monkeypatch)

    ok, rd = pm.start({})
    assert ok is True
    assert "profile" in recorded
    rd_spec = recorded["profile"].get("run_dir")
    assert rd_spec
    assert rd_spec.startswith(str(rr))

    base = os.path.basename(rd_spec.rstrip(os.path.sep))
    assert re.match(r"^\d{8}_\d{6}$", base)
    assert rd == rd_spec


def test_start_respects_explicit_run_dir(tmp_path, monkeypatch):
    rr = tmp_path / "rr"
    rr.mkdir(parents=True, exist_ok=True)
    explicit = tmp_path / "custom" / "sessionX"
    explicit.mkdir(parents=True, exist_ok=True)

    pm = ProcessManager(str(rr))
    recorded: dict = {}

    def fake_build_cmd(self, profile):
        recorded["profile"] = dict(profile)
        return [sys.executable, "-c", "print('noop')"]

    monkeypatch.setattr(ProcessManager, "_build_cmd", fake_build_cmd, raising=True)
    _stub_popen(monkeypatch)

    ok, rd = pm.start({"run_dir": str(explicit)})
    assert ok is True
    assert recorded["profile"].get("run_dir") == str(explicit)
    assert rd == str(explicit)
