from __future__ import annotations

import ast
from pathlib import Path


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "vdm_rt").is_dir():
            return parent
    raise AssertionError("repo root not found")


def test_non_runtime_experiment_folders_are_removed():
    root = _repo_root()
    removed = [
        "vdm_live.py",
        "vdm_rt/frontend",
        "vdm_rt/tests/frontend",
        "vdm_rt/ck",
        "vdm_rt/physics",
        "vdm_rt/tests/physics",
        "vdm_rt/data",
        "vdm_rt/core/tests",
        "vdm_rt/core/cosmology",
        "vdm_rt/io/sensors",
        "vdm_rt/io/maps_ring.py",
        "vdm_rt/io/visualization",
        "vdm_rt/core/visualizer.py",
        "vdm_rt/core/engine/maps_frame.py",
        "vdm_rt/runtime/helpers/maps_ws.py",
        "vdm_rt/runtime/helpers/viz.py",
        "vdm_rt/io/actuators/motor_control.py",
        "vdm_rt/io/actuators/symbols.py",
        "vdm_rt/io/actuators/visualize.py",
        "vdm_rt/io/actuators/vocalizer.py",
    ]
    existing = [rel for rel in removed if (root / rel).exists()]
    assert not existing, "Removed non-runtime paths reappeared: " + ", ".join(existing)


def test_runtime_package_does_not_import_removed_layers():
    root = _repo_root()
    forbidden_prefixes = (
        "vdm_rt.frontend",
        "vdm_rt.physics",
        "vdm_rt.data",
        "vdm_rt.ck",
        "vdm_rt.core.cosmology",
        "vdm_rt.io.sensors",
        "vdm_rt.io.maps_ring",
        "vdm_rt.io.visualization",
        "vdm_rt.core.visualizer",
        "vdm_rt.core.engine.maps_frame",
        "vdm_rt.runtime.helpers.maps_ws",
        "vdm_rt.runtime.helpers.viz",
        "vdm_rt.io.actuators.motor_control",
        "vdm_rt.io.actuators.symbols",
        "vdm_rt.io.actuators.visualize",
        "vdm_rt.io.actuators.vocalizer",
    )
    forbidden_top_level = {"dash"}
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
                    name = alias.name
                    if name in forbidden_top_level or any(name == p or name.startswith(p + ".") for p in forbidden_prefixes):
                        offenders.append(f"{rel}: import {name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod in forbidden_top_level or any(mod == p or mod.startswith(p + ".") for p in forbidden_prefixes):
                    offenders.append(f"{rel}: from {mod} import ...")
    assert not offenders, "Forbidden imports after runtime prune:\n" + "\n".join(offenders)
