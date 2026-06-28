#!/usr/bin/env python3
"""
Static timing-touchpoint audit for VDM repos.

This is intentionally NOT a compliance verdict by itself. It lists every wall-time,
sleep, timestamp, dt, thread, async, flush, scheduler, and hz touchpoint and classifies
it by likely layer so you can inspect whether any cognitive update path consumes wall time.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

PATTERNS = [
    r"time\.time\(", r"perf_counter\(", r"monotonic\(", r"datetime", r"timestamp",
    r"sleep\(", r"asyncio", r"threading", r"Thread\(", r"yield", r"flush\(",
    r"elapsed", r"wall", r"dt\b", r"hz\b", r"scheduler", r"schedule", r"interval",
]
COMPILED = re.compile("|".join(PATTERNS), re.IGNORECASE)
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build", ".mypy_cache", ".pytest_cache"}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".sh", ".c", ".h", ".S"}


def layer_for(path: Path) -> str:
    parts = set(path.parts)
    s = str(path).lower()
    if any(x in s for x in ("void_equations", "sparse_connectome", "connectome", "stepper", "core/", "runtime/loop", "nexus")):
        return "inspect_cognitive_or_core"
    if any(x in s for x in ("logger", "dashboard", "status", "api", "server", "viz", "plot", "telemetry")):
        return "likely_observability_or_shell"
    if any(x in s for x in ("test", "tools", "scripts", "examples")):
        return "test_or_tooling"
    return "unknown"


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit timing touchpoints in a VDM repo.")
    ap.add_argument("repo", type=Path)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--markdown", type=Path, default=None)
    args = ap.parse_args()

    hits: List[Dict[str, object]] = []
    for p in args.repo.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if not p.is_file() or p.suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if COMPILED.search(line):
                hits.append({
                    "path": str(p.relative_to(args.repo)),
                    "line": line_no,
                    "layer": layer_for(p.relative_to(args.repo)),
                    "text": line.strip()[:240],
                })
    by_layer: Dict[str, int] = {}
    for h in hits:
        by_layer[h["layer"]] = by_layer.get(h["layer"], 0) + 1
    summary = {"repo": str(args.repo), "hit_count": len(hits), "by_layer": by_layer, "hits": hits}
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# Runtime Timing Touchpoint Audit", "", f"Total hits: {len(hits)}", "", "## Counts by layer", ""]
        for k, v in sorted(by_layer.items()):
            lines.append(f"- `{k}`: {v}")
        lines.extend(["", "## Hits", ""])
        for h in hits:
            lines.append(f"- `{h['path']}:{h['line']}` `{h['layer']}` — `{h['text']}`")
        args.markdown.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"hit_count": len(hits), "by_layer": by_layer}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
