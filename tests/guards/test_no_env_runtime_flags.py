from __future__ import annotations

import ast
from pathlib import Path


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "vdm_rt").is_dir():
            return parent
    raise AssertionError("repo root not found")


def _iter_live_python(root: Path):
    package = root / "vdm_rt"
    for rel in ("cli", "core", "io", "runtime"):
        base = package / rel
        if base.is_dir():
            yield from base.rglob("*.py")
    for rel in ("nexus.py", "run_nexus.py"):
        path = package / rel
        if path.exists():
            yield path


def _is_os_getenv(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "getenv"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in {"os", "_os"}
    )


def _is_environ_get(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "environ"
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id in {"os", "_os"}
    )


def _is_environ_subscript(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "environ"
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id in {"os", "_os"}
    )


def test_live_runtime_flags_use_file_config() -> None:
    root = _repo_root()
    offenders: list[str] = []

    for path in _iter_live_python(root):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError as exc:
            offenders.append(f"{rel}: syntax error: {exc}")
            continue

        for node in ast.walk(tree):
            if _is_os_getenv(node) or _is_environ_get(node) or _is_environ_subscript(node):
                offenders.append(f"{rel}:{getattr(node, 'lineno', '?')}")

    assert not offenders, "Runtime config must use config/*.toml, not env flags:\n" + "\n".join(offenders)
