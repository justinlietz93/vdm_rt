"""
Central file-backed runtime configuration.

The canonical tracked config surface is the config/ folder. Keep
operator-facing knobs in named TOML files there rather than scattering hidden
environment-variable flags through runtime code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import copy
import tomllib


CONFIG_FILE_NAME = "runtime.toml"

_CACHE_KEY: tuple[tuple[Path, float | None], ...] | None = None
_CACHE_DATA: dict[str, Any] = {}


def _package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _candidate_paths(path: str | Path | None = None) -> list[Path]:
    if path:
        return [Path(path).expanduser()]
    cwd = Path.cwd()
    package_root = _package_root()
    return [
        cwd / "config",
        cwd / "vdm_rt" / "config",
        package_root / "config",
    ]


def resolve_config_path(path: str | Path | None = None) -> Path | None:
    """Return the first existing config directory or TOML file."""
    seen: set[Path] = set()
    for candidate in _candidate_paths(path):
        try:
            resolved = candidate.resolve()
        except Exception:
            resolved = candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_dir() or resolved.is_file():
            return resolved
    return None


def resolve_config_paths(path: str | Path | None = None) -> list[Path]:
    """Return TOML files to load, sorted by filename for stable merging."""
    resolved = resolve_config_path(path)
    if resolved is None:
        return []
    if resolved.is_file():
        return [resolved] if resolved.suffix == ".toml" else []
    try:
        return sorted(p for p in resolved.glob("*.toml") if p.is_file())
    except Exception:
        return []


def _merge(dst: dict[str, Any], src: Mapping[str, Any]) -> dict[str, Any]:
    for key, value in src.items():
        if isinstance(value, Mapping) and isinstance(dst.get(key), dict):
            _merge(dst[key], value)  # type: ignore[index]
        elif isinstance(value, Mapping):
            dst[key] = _merge({}, value)
        else:
            dst[key] = value
    return dst


def load_runtime_config(path: str | Path | None = None, *, force: bool = False) -> dict[str, Any]:
    """Load and merge runtime TOML config files, cached by path and mtime."""
    global _CACHE_KEY, _CACHE_DATA

    config_paths = resolve_config_paths(path)
    if not config_paths:
        return {}

    cache_parts: list[tuple[Path, float | None]] = []
    for config_path in config_paths:
        try:
            mtime = config_path.stat().st_mtime
        except Exception:
            mtime = None
        cache_parts.append((config_path, mtime))
    cache_key = tuple(cache_parts)

    if not force and _CACHE_KEY == cache_key:
        return copy.deepcopy(_CACHE_DATA)

    data: dict[str, Any] = {}
    for config_path in config_paths:
        with config_path.open("rb") as fh:
            loaded = tomllib.load(fh)
        if isinstance(loaded, dict):
            _merge(data, loaded)

    _CACHE_KEY = cache_key
    _CACHE_DATA = data
    return copy.deepcopy(data)


def _lookup(config: Mapping[str, Any], key: str, default: Any) -> Any:
    cur: Any = config
    for part in str(key).split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return default
        cur = cur[part]
    return cur


def config_get(key: str, default: Any = None, *, config: Mapping[str, Any] | None = None) -> Any:
    source = load_runtime_config() if config is None else config
    return _lookup(source, key, default)


def config_bool(key: str, default: bool = False, *, config: Mapping[str, Any] | None = None) -> bool:
    value = config_get(key, default, config=config)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    try:
        return str(value).strip().lower() in ("1", "true", "yes", "on", "y", "t")
    except Exception:
        return bool(default)


def config_int(key: str, default: int = 0, *, config: Mapping[str, Any] | None = None) -> int:
    value = config_get(key, default, config=config)
    try:
        return int(value)
    except Exception:
        return int(default)


def config_float(key: str, default: float = 0.0, *, config: Mapping[str, Any] | None = None) -> float:
    value = config_get(key, default, config=config)
    try:
        return float(value)
    except Exception:
        return float(default)


def config_str(key: str, default: str = "", *, config: Mapping[str, Any] | None = None) -> str:
    value = config_get(key, default, config=config)
    if value is None:
        return str(default)
    try:
        return str(value)
    except Exception:
        return str(default)
