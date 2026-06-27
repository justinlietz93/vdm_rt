"""
Runtime dependency checks for launch-time fail-fast behavior.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


RUNTIME_REQUIREMENTS: tuple[tuple[str, str], ...] = (
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("h5py", "h5py"),
    ("zstandard", "zstandard"),
)

DEFAULT_REQUIREMENTS_PATH = Path(__file__).resolve().parents[1] / "requirements.txt"


def missing_runtime_requirements() -> list[str]:
    """Return requirement names whose import modules are not available."""
    missing: list[str] = []
    for requirement, module_name in RUNTIME_REQUIREMENTS:
        if importlib.util.find_spec(module_name) is None:
            missing.append(requirement)
    return missing


def assert_runtime_requirements_installed(requirements_path: str | Path | None = None) -> None:
    """
    Stop runtime launch when required runtime packages are missing.

    The runtime writes H5 checkpoints, compressed JSONL logs, and relies on
    NumPy/SciPy for connectome state and sparse operations, so these are hard
    launch requirements.
    """
    missing = missing_runtime_requirements()
    if not missing:
        return

    req_path = str(requirements_path or DEFAULT_REQUIREMENTS_PATH)
    missing_csv = ", ".join(missing)
    raise RuntimeError(
        f"Missing required runtime dependencies: {missing_csv}. "
        f"Install them with `pip install -r {req_path}` before launching vdm_rt."
    )


__all__ = [
    "RUNTIME_REQUIREMENTS",
    "DEFAULT_REQUIREMENTS_PATH",
    "missing_runtime_requirements",
    "assert_runtime_requirements_installed",
]
