from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_dense_connectome_module_is_absent():
    assert not (_repo_root() / "core" / "connectome.py").exists()


def test_dense_runtime_selection_flags_are_removed():
    root = _repo_root()
    live_files = [
        root / "nexus.py",
        root / "run_nexus.py",
        root / "cli" / "args.py",
        root / "control" / "process_manager.py",
    ]
    forbidden = (
        "FORCE_DENSE",
        "--dense",
        "--dense-mode",
        "--sparse",
        "--sparse-mode",
        "sparse_mode",
        "dense_mode",
    )
    for path in live_files:
        text = path.read_text(encoding="utf-8")
        hits = [token for token in forbidden if token in text]
        assert not hits, f"{path.relative_to(root)} still contains dense/sparse selection tokens: {hits}"
