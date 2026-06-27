from __future__ import annotations

import pytest

from pathlib import Path

from vdm_rt.core.adc import ADC
from vdm_rt.core.announce import Observation
from vdm_rt.core.memory import engram_io
from vdm_rt.core.sparse_connectome import SparseConnectome
from vdm_rt.nexus import Nexus
from vdm_rt.utils import dependencies


def test_h5_checkpoint_requires_h5py(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(engram_io, "HAVE_H5", False)

    with pytest.raises(RuntimeError, match="h5py is required"):
        engram_io.save_checkpoint(str(tmp_path), 1, object(), fmt="h5", adc=object())

    assert not list(tmp_path.glob("state_*"))


def test_non_h5_checkpoint_writes_are_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="runtime checkpoints must be h5"):
        engram_io.save_checkpoint(str(tmp_path), 1, object(), fmt="json", adc=object())

    assert not list(tmp_path.glob("state_*"))


def test_engram_load_requires_h5_extension() -> None:
    with pytest.raises(ValueError, match="must be H5"):
        engram_io.load_engram("state_1.bin", object(), adc=object())


def test_checkpoint_save_requires_adc(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="ADC is required"):
        engram_io.save_checkpoint(str(tmp_path), 1, object(), fmt="h5", adc=None)

    assert not list(tmp_path.glob("state_*"))


def test_engram_load_requires_adc_for_h5_path() -> None:
    with pytest.raises(RuntimeError, match="ADC is required"):
        engram_io.load_engram("state_1.h5", object(), adc=None)


def test_checkpoint_save_requires_sparse_connectome_shape(tmp_path) -> None:
    with pytest.raises(TypeError, match="SparseConnectome"):
        engram_io.save_checkpoint(str(tmp_path), 1, object(), fmt="h5", adc=ADC())

    assert not list(tmp_path.glob("state_*"))


def test_h5_checkpoint_requires_adc_dataset(tmp_path) -> None:
    if not engram_io.HAVE_H5:
        pytest.skip("h5py not available")

    checkpoint = tmp_path / "state_1.h5"
    with engram_io.h5py.File(checkpoint, "w") as h5:
        h5.attrs["backend"] = "sparse"
        h5.attrs["N"] = 1
        h5.attrs["threshold"] = 0.0
        h5.attrs["lambda_omega"] = 0.0
        sparse = h5.create_group("sparse")
        sparse.create_dataset("W", data=[0.0])
        sparse.create_dataset("row_ptr", data=[0, 0])
        sparse.create_dataset("col_idx", data=[])

    connectome = SparseConnectome(N=1, k=0)
    before_w = connectome.W.copy()

    with pytest.raises(ValueError, match="required ADC state"):
        engram_io.load_engram(str(checkpoint), connectome, adc=ADC())

    assert connectome.W.tolist() == before_w.tolist()


def test_h5_checkpoint_rejects_dense_backend(tmp_path) -> None:
    if not engram_io.HAVE_H5:
        pytest.skip("h5py not available")

    checkpoint = tmp_path / "state_1.h5"
    with engram_io.h5py.File(checkpoint, "w") as h5:
        h5.attrs["backend"] = "dense"
        h5.attrs["N"] = 1
        h5.attrs["threshold"] = 0.0
        h5.attrs["lambda_omega"] = 0.0
        h5.create_dataset("adc_json", data="{}", dtype=engram_io.h5py.string_dtype(encoding="utf-8"))
        h5.create_group("dense")

    connectome = SparseConnectome(N=1, k=0)

    with pytest.raises(ValueError, match="must be sparse"):
        engram_io.load_engram(str(checkpoint), connectome, adc=ADC())


def test_checkpoint_io_has_no_dense_backend_branch() -> None:
    root = Path(__file__).resolve().parents[2]
    src = (root / "core" / "memory" / "engram_io.py").read_text(encoding="utf-8")
    forbidden = [
        "backend == \"dense\"",
        "backend == 'dense'",
        "f[\"dense\"]",
        "create_group(\"dense\")",
        "connectome.A",
        "connectome.E",
    ]

    offenders = [token for token in forbidden if token in src]

    assert offenders == []


def test_h5_checkpoint_round_trips_required_adc_state(tmp_path) -> None:
    if not engram_io.HAVE_H5:
        pytest.skip("h5py not available")

    connectome = SparseConnectome(N=8, k=2, seed=7)
    adc = ADC()
    adc.update_from(
        [
            Observation(
                tick=1,
                kind="region_stat",
                nodes=[1, 2],
                w_mean=0.4,
                s_mean=0.2,
                coverage_id=3,
                domain_hint="test",
            ),
            Observation(
                tick=1,
                kind="boundary_probe",
                nodes=[2, 3],
                cut_strength=0.7,
                coverage_id=3,
                domain_hint="test",
            ),
        ]
    )

    path = engram_io.save_checkpoint(str(tmp_path), 2, connectome, fmt="h5", adc=adc)

    loaded_connectome = SparseConnectome(N=8, k=2, seed=9)
    loaded_adc = ADC()
    engram_io.load_engram(path, loaded_connectome, adc=loaded_adc)

    assert len(loaded_adc._territories) == len(adc._territories)
    assert len(loaded_adc._boundaries) == len(adc._boundaries)
    assert loaded_adc._id_seq == adc._id_seq


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


def test_scipy_is_not_a_runtime_requirement() -> None:
    requirement_names = {requirement for requirement, _module in dependencies.RUNTIME_REQUIREMENTS}
    assert "scipy" not in requirement_names


def test_live_runtime_surfaces_do_not_import_scipy() -> None:
    root = Path(__file__).resolve().parents[2]
    checked_roots = [
        root / "core",
        root / "runtime",
        root / "io",
        root / "utils",
        root / "config",
    ]
    offenders = []
    for checked_root in checked_roots:
        for path in checked_root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "import scipy" in text or "from scipy" in text:
                offenders.append(path.relative_to(root).as_posix())

    assert offenders == []


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
