from __future__ import annotations

import ast
from pathlib import Path


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "vdm_rt").is_dir():
            return parent
    raise AssertionError("repo root not found")


def _package_root() -> Path:
    return _repo_root() / "vdm_rt"


def _iter_live_python() -> list[Path]:
    root = _package_root()
    paths: list[Path] = []
    for rel in ("cli", "control", "core", "io", "runtime"):
        base = root / rel
        if base.is_dir():
            paths.extend(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)
    for rel in ("nexus.py", "run_nexus.py"):
        path = root / rel
        if path.exists():
            paths.append(path)
    return sorted(paths)


REMOVED_PATHS = [
    "io/cognition/composer.py",
    "io/cognition/speaker.py",
    "io/cognition/stimulus.py",
    "io/lexicon/idf.py",
    "io/lexicon/phrase_bank_min.json",
    "io/lexicon/store.py",
    "io/actuators/__init__.py",
    "io/actuators/macros.py",
    "io/actuators/thoughts.py",
    "runtime/emitters.py",
    "runtime/helpers/speak.py",
    "runtime/helpers/macro_board.py",
    "runtime/helpers/emission.py",
    "core/text_utils.py",
]

FORBIDDEN_IMPORT_PREFIXES = (
    "vdm_rt.io.cognition.composer",
    "vdm_rt.io.cognition.speaker",
    "vdm_rt.io.cognition.stimulus",
    "vdm_rt.io.lexicon",
    "vdm_rt.io.actuators.macros",
    "vdm_rt.io.actuators.thoughts",
    "vdm_rt.runtime.emitters",
    "vdm_rt.runtime.helpers.speak",
    "vdm_rt.runtime.helpers.macro_board",
    "vdm_rt.runtime.helpers.emission",
    "vdm_rt.core.text_utils",
)

FORBIDDEN_ATTR_CALLS = {
    "emit_text",
    "emit_macro",
    "register_macro",
    "list_macros",
    "_save_lexicon",
    "_compose_say_text",
    "_update_lexicon_and_ngrams",
    "_symbols_to_indices",
}

FORBIDDEN_TEXT_TOKENS = {
    "compose_say_text",
    "maybe_auto_speak",
    "phrase_bank",
    "generate_emergent_sentence",
    "update_ngrams",
    "MacroEmitter",
    "ThoughtEmitter",
}


def test_removed_decoder_authoring_files_are_absent() -> None:
    root = _package_root()
    offenders = [path for path in REMOVED_PATHS if (root / path).exists()]
    assert not offenders, "Removed decoder/authorship files still exist:\n" + "\n".join(offenders)


def test_live_code_does_not_import_or_call_decoder_authorship() -> None:
    root = _package_root()
    offenders: list[str] = []

    for path in _iter_live_python():
        rel = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8", errors="ignore")
        for token in FORBIDDEN_TEXT_TOKENS:
            if token in source:
                offenders.append(f"{rel}: forbidden token {token!r}")

        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            offenders.append(f"{rel}: syntax error: {exc}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                        offenders.append(f"{rel}:{node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    offenders.append(f"{rel}:{node.lineno}: from {module} import ...")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in FORBIDDEN_ATTR_CALLS:
                    offenders.append(f"{rel}:{node.lineno}: call .{node.func.attr}()")

    assert not offenders, "Live decoder/authorship path remains:\n" + "\n".join(offenders)
