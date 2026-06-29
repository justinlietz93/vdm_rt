"""
Streaming readers for runtime JSONL log artifacts.

The runtime writes compressed JSONL by default. Analysis code should use these
helpers instead of open-coding decompression for every script.
"""

from __future__ import annotations

from contextlib import contextmanager
import gzip
import io
import json
from pathlib import Path
from typing import Any, Iterator, TextIO


PathLike = str | Path


@contextmanager
def open_text_stream(path: PathLike) -> Iterator[TextIO]:
    """Open plain, gzip, or zstd-compressed text as a streaming text file."""
    p = Path(path)
    name = p.name.lower()
    if name.endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8", errors="replace") as fh:
            yield fh
        return
    if name.endswith(".zst"):
        import zstandard as zstd

        with p.open("rb") as raw:
            dctx = zstd.ZstdDecompressor()
            try:
                reader = dctx.stream_reader(raw, read_across_frames=True)
            except TypeError:
                reader = dctx.stream_reader(raw)
            with reader:
                text = io.TextIOWrapper(reader, encoding="utf-8", errors="replace")
                try:
                    yield text
                finally:
                    text.detach()
        return
    with p.open("r", encoding="utf-8", errors="replace") as fh:
        yield fh


def iter_jsonl_lines(path: PathLike, *, skip_blank: bool = True) -> Iterator[str]:
    """Yield JSONL text lines from plain, gzip, or zstd-compressed files."""
    with open_text_stream(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if skip_blank and not line.strip():
                continue
            yield line


def iter_jsonl_rows(path: PathLike, *, skip_invalid: bool = True) -> Iterator[dict[str, Any]]:
    """Yield parsed JSON object rows from a JSONL artifact."""
    for line in iter_jsonl_lines(path):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            if skip_invalid:
                continue
            raise
        if isinstance(obj, dict):
            yield obj


def load_jsonl_rows(path: PathLike, *, skip_invalid: bool = True) -> list[dict[str, Any]]:
    """Load parsed JSONL rows into memory when a caller explicitly wants a list."""
    return list(iter_jsonl_rows(path, skip_invalid=skip_invalid))


__all__ = [
    "open_text_stream",
    "iter_jsonl_lines",
    "iter_jsonl_rows",
    "load_jsonl_rows",
]
