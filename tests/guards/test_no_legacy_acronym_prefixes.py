"""Reject retired acronym prefixes from live runtime source."""

from __future__ import annotations

import re
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
LIVE_ROOTS = (
    PACKAGE_ROOT / "cli",
    PACKAGE_ROOT / "control",
    PACKAGE_ROOT / "core",
    PACKAGE_ROOT / "io",
    PACKAGE_ROOT / "runtime",
    PACKAGE_ROOT / "utils",
)
LIVE_FILES = (
    PACKAGE_ROOT / "__init__.py",
    PACKAGE_ROOT / "nexus.py",
    PACKAGE_ROOT / "run_nexus.py",
)
LEGACY_ACRONYM = re.compile(r"(?i)(?<![a-z0-9])(?:fum|qfum)(?![a-z0-9])")


def _live_python_files() -> list[Path]:
    files = [path for path in LIVE_FILES if path.is_file()]
    for root in LIVE_ROOTS:
        if root.is_dir():
            files.extend(root.rglob("*.py"))
    return sorted(files)


def test_live_runtime_has_no_legacy_acronym_prefixes() -> None:
    offenders: list[str] = []
    for path in _live_python_files():
        relative_path = path.relative_to(PACKAGE_ROOT)
        path_match = LEGACY_ACRONYM.search(str(relative_path))
        if path_match:
            offenders.append(f"{relative_path}: legacy module path")

        source = path.read_text(encoding="utf-8", errors="ignore")
        for match in LEGACY_ACRONYM.finditer(source):
            line = source.count("\n", 0, match.start()) + 1
            offenders.append(f"{relative_path}:{line}: {match.group(0)}")

    assert not offenders, "Legacy acronym prefixes remain in live runtime:\n" + "\n".join(offenders)
