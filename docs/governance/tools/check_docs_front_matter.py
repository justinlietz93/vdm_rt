#!/usr/bin/env python3
"""Minimal docs quality gate for VDM RT.

Checks only docs/pages/*.md because imported source docs are allowed to keep their
original structure.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "pages"
REQUIRED = ("title", "status", "owner", "source_authority", "summary")
ALLOWED_STATUS = {"active", "draft", "source", "archived", "generated"}


def parse_front_matter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    block = text[4:end]
    data: dict[str, str] = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def main() -> int:
    failures: list[str] = []
    if not PAGES.exists():
        failures.append(f"missing pages directory: {PAGES}")
    else:
        for path in sorted(PAGES.rglob("*.md")):
            rel = path.relative_to(ROOT)
            data = parse_front_matter(path.read_text(encoding="utf-8"))
            if data is None:
                failures.append(f"{rel}: missing YAML front matter")
                continue
            missing = [key for key in REQUIRED if not data.get(key)]
            if missing:
                failures.append(f"{rel}: missing required fields: {', '.join(missing)}")
            status = data.get("status")
            if status and status not in ALLOWED_STATUS:
                failures.append(f"{rel}: invalid status {status!r}")

    if failures:
        print("docs front matter check failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("docs front matter check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
