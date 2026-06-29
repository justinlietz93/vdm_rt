from __future__ import annotations

import gzip
import json
from pathlib import Path

import zstandard as zstd

from vdm_rt.io.logging.jsonl_reader import iter_jsonl_rows, open_text_stream


ROWS = [{"tick": 1, "value": "a"}, {"tick": 2, "value": "b"}]


def _payload() -> str:
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in ROWS)


def _write_plain(path: Path) -> None:
    path.write_text(_payload(), encoding="utf-8")


def _write_gz(path: Path) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write(_payload())


def _write_zst(path: Path) -> None:
    compressor = zstd.ZstdCompressor(level=1)
    path.write_bytes(compressor.compress(_payload().encode("utf-8")))


def test_iter_jsonl_rows_reads_plain_gzip_and_zstd(tmp_path: Path) -> None:
    writers = {
        "events.jsonl": _write_plain,
        "events.jsonl.gz": _write_gz,
        "events.jsonl.zst": _write_zst,
    }
    for name, writer in writers.items():
        path = tmp_path / name
        writer(path)
        assert list(iter_jsonl_rows(path)) == ROWS


def test_open_text_stream_streams_compressed_text(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl.zst"
    _write_zst(path)

    with open_text_stream(path) as fh:
        assert json.loads(next(fh)) == ROWS[0]
        assert json.loads(next(fh)) == ROWS[1]
