"""
Copyright © 2025 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""
from __future__ import annotations

import ast
from pathlib import Path


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "vdm_rt").is_dir():
            return parent
    raise AssertionError("repo root not found")


def test_frontend_package_is_removed():
    root = _repo_root()
    assert not (root / "vdm_rt" / "frontend").exists()
    assert not (root / "vdm_rt" / "tests" / "frontend").exists()


def test_no_package_imports_vdm_rt_frontend_or_dash():
    root = _repo_root()
    offenders: list[str] = []
    for path in (root / "vdm_rt").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError as exc:
            offenders.append(f"{rel}: syntax error: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "dash" or alias.name.startswith("dash.") or alias.name.startswith("vdm_rt.frontend"):
                        offenders.append(f"{rel}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "dash" or mod.startswith("dash.") or mod.startswith("vdm_rt.frontend"):
                    offenders.append(f"{rel}: from {mod} import ...")
    assert not offenders, "Forbidden frontend/Dash imports:\n" + "\n".join(offenders)
