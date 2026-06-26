"""Protect archived substrate source and keep it out of live runtime imports."""

from __future__ import annotations

import ast
from pathlib import Path


ARCHIVE_FILES = (
    "substrate.py",
    "neurogenesis.py",
    "growth_arbiter.py",
    "structural_homeostasis.py",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_legacy_substrate_source_is_preserved_outside_core() -> None:
    root = _repo_root()
    archive = root / "docs" / "sources" / "legacy-substrate-neurogenesis"

    assert archive.is_dir(), "Legacy substrate source archive must remain present."
    missing = [name for name in ARCHIVE_FILES if not (archive / name).is_file()]
    assert not missing, "Archived substrate source must not be deleted: " + ", ".join(missing)
    assert (archive / "README.md").is_file(), "Archive must explain its sparse-native port obligation."
    assert not (root / "core" / "substrate").exists(), "Dense substrate source must not remain importable from core/."


def test_live_runtime_does_not_import_archived_substrate() -> None:
    root = _repo_root()
    offenders: list[str] = []
    live_roots = ("cli", "core", "io", "runtime", "control", "utils")

    paths = [root / name for name in ("nexus.py", "run_nexus.py") if (root / name).is_file()]
    for live_root in live_roots:
        base = root / live_root
        if base.is_dir():
            paths.extend(base.rglob("*.py"))

    for path in paths:
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "vdm_rt.core.substrate" or alias.name.startswith("vdm_rt.core.substrate."):
                        offenders.append(f"{relative}:{node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                relative_substrate = node.level > 0 and (module == "substrate" or module.startswith("substrate."))
                absolute_substrate = module == "vdm_rt.core.substrate" or module.startswith("vdm_rt.core.substrate.")
                if relative_substrate or absolute_substrate:
                    offenders.append(f"{relative}:{node.lineno}: from {module or '.'} import ...")

    assert not offenders, "Live runtime imports archived substrate:\n" + "\n".join(offenders)
