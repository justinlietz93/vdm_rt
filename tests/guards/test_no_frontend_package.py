"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

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


def test_no_embedded_frontend_or_browser_control_surface():
    root = _repo_root()
    package = root / "vdm_rt"
    live_paths = [
        package / "core",
        package / "runtime",
        package / "io",
        package / "cli",
        package / "control",
        package / "nexus.py",
        package / "run_nexus.py",
    ]
    forbidden = (
        "<html",
        "text/html",
        "document.getElementById",
        "addEventListener",
    )
    offenders: list[str] = []

    files: list[Path] = []
    for path in live_paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(path.rglob("*.py"))

    for path in files:
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in forbidden:
            if marker in text:
                offenders.append(f"{path.relative_to(root).as_posix()}: {marker}")

    assert not offenders, "Forbidden embedded frontend/control UI residue:\n" + "\n".join(offenders)


def test_no_embedded_control_server_surface():
    root = _repo_root()
    package = root / "vdm_rt"
    assert not (package / "core" / "control_server.py").exists()

    live_paths = [
        package / "core",
        package / "runtime",
        package / "cli",
        package / "control",
        package / "nexus.py",
        package / "run_nexus.py",
        package / "config",
    ]
    forbidden = (
        "control_server",
        "ControlServer",
        "--control-server",
        "server_enabled",
        "server_host",
        "server_port",
    )
    offenders: list[str] = []
    files: list[Path] = []
    for path in live_paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(
                p
                for p in path.rglob("*")
                if p.is_file() and p.suffix in {".py", ".toml"}
            )

    for path in files:
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in forbidden:
            if marker in text:
                offenders.append(f"{path.relative_to(root).as_posix()}: {marker}")

    assert not offenders, "Forbidden embedded control-server residue:\n" + "\n".join(offenders)
