from __future__ import annotations

import pytest

from pathlib import Path

from vdm_rt.core.memory import engram_io
from vdm_rt.nexus import Nexus
from vdm_rt.utils import dependencies


def test_h5_checkpoint_requires_h5py(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(engram_io, "HAVE_H5", False)

    with pytest.raises(RuntimeError, match="h5py is required"):
        engram_io.save_checkpoint(str(tmp_path), 1, object(), fmt="h5")

    assert not list(tmp_path.glob("state_*"))


def test_non_h5_checkpoint_writes_are_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="runtime checkpoints must be h5"):
        engram_io.save_checkpoint(str(tmp_path), 1, object(), fmt="json")

    assert not list(tmp_path.glob("state_*"))


def test_engram_load_requires_h5_extension() -> None:
    with pytest.raises(ValueError, match="must be H5"):
        engram_io.load_engram("state_1.bin", object())


def test_runtime_dependency_gate_reports_missing_h5py(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_find_spec(name: str):
        if name == "h5py":
            return None
        return object()

    monkeypatch.setattr(dependencies.importlib.util, "find_spec", fake_find_spec)

    with pytest.raises(RuntimeError) as exc:
        dependencies.assert_runtime_requirements_installed()

    msg = str(exc.value)
    assert "h5py" in msg
    assert "pip install -r" in msg
    assert "requirements.txt" in msg


def test_nexus_rejects_non_h5_checkpoint_format_before_side_effects(tmp_path) -> None:
    run_dir = tmp_path / "bad-format-run"

    with pytest.raises(ValueError, match="runtime checkpoints must be h5"):
        Nexus(run_dir=str(run_dir), checkpoint_format="json")

    assert not run_dir.exists()


def test_live_runtime_surfaces_do_not_reference_compressed_array_checkpoints() -> None:
    root = Path(__file__).resolve().parents[2]
    forbidden = chr(110) + chr(112) + chr(122)
    checked_roots = [
        root / "core",
        root / "runtime",
        root / "docs",
        root / "tests",
        root / "utils",
    ]
    checked_files = [
        root / "README.md",
        root / "run_nexus.py",
        root / "config" / "persistence.toml",
    ]
    for checked_root in checked_roots:
        checked_files.extend(
            path
            for path in checked_root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix in {".py", ".md", ".toml", ".yml", ".yaml"}
        )

    offenders = []
    for path in checked_files:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        if forbidden in text:
            offenders.append(path.relative_to(root).as_posix())

    assert offenders == []
