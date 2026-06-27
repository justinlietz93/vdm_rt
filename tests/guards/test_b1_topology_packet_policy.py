from __future__ import annotations

from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_live_b1z_detector_lives_in_void_b1_module() -> None:
    from vdm_rt.core.void_b1 import StreamingZEMA

    det = StreamingZEMA(half_life_ticks=4, z_spike=1.0, hysteresis=0.25, min_interval_ticks=1)
    first = det.update(0.0, tick=0)
    second = det.update(2.0, tick=1)

    assert set(first) >= {"value", "delta", "mu", "sigma", "z", "spike"}
    assert second["value"] == 2.0
    assert second["delta"] == 2.0


def test_no_duplicate_streaming_zema_in_metrics_module() -> None:
    root = _project_root()
    metrics_src = (root / "core" / "metrics.py").read_text(encoding="utf-8")

    assert "class StreamingZEMA" not in metrics_src
    assert "from vdm_rt.core.metrics import StreamingZEMA" not in metrics_src


def test_void_b1_packet_is_not_wired_into_live_runtime_yet() -> None:
    root = _project_root()
    checked_roots = [root / "core", root / "runtime"]
    checked_files = [root / "nexus.py"]
    for checked_root in checked_roots:
        checked_files.extend(
            path
            for path in checked_root.rglob("*.py")
            if path.name != "void_b1.py" and "__pycache__" not in path.parts
        )

    offenders = []
    for path in checked_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "VoidB1Meter" in text or "update_void_b1(" in text:
            offenders.append(path.relative_to(root).as_posix())

    assert offenders == []
