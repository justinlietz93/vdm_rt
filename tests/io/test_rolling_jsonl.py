"""Configuration and data-retention tests for external JSONL logging."""

from __future__ import annotations

import logging
import json
from pathlib import Path
from uuid import uuid4

import pytest
import zstandard as zstd

from vdm_rt.config import load_runtime_config
from vdm_rt.io.logging.rolling_jsonl import (
    RollingJsonlHandler,
    RollingJsonlWriter,
    RollingZstdJsonlHandler,
    RollingZstdJsonlWriter,
)
from vdm_rt.utils.logging_setup import get_logger


def _configure_logging(monkeypatch, tmp_path: Path, body: str) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "logging.toml").write_text(body, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    load_runtime_config(force=True)


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def _read_zstd_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    dctx = zstd.ZstdDecompressor()
    with path.open("rb") as fh:
        try:
            reader = dctx.stream_reader(fh, read_across_frames=True)
        except TypeError:
            reader = dctx.stream_reader(fh)
        with reader:
            return reader.read().decode("utf-8").splitlines()


def test_rolling_writer_reads_toml_line_caps_and_enforces_each_write(monkeypatch, tmp_path: Path) -> None:
    _configure_logging(
        monkeypatch,
        tmp_path,
        "[logging]\n"
        "events_max_lines = 2\n"
        "events_archive_segment_lines = 10\n"
        "roll_check_every = 1\n",
    )
    path = tmp_path / "run" / "events.jsonl"
    writer = RollingJsonlWriter(str(path))

    assert writer.max_main_lines == 2
    assert writer.archive_segment_max_lines == 10
    assert writer._check_every == 1

    for line in ("first", "second", "third"):
        writer.write_line(line)

    assert _read_lines(path) == ["second", "third"]
    archived = [
        line
        for archive in (tmp_path / "run" / "archived").rglob("events.jsonl")
        for line in _read_lines(archive)
    ]
    assert archived == ["first"]


def test_rolling_writer_rotates_archive_segments_without_dropping_lines(tmp_path: Path) -> None:
    path = tmp_path / "run" / "events.jsonl"
    writer = RollingJsonlWriter(
        str(path),
        max_main_lines=1,
        archive_segment_max_lines=1,
        check_every=3,
    )

    for line in ("first", "second", "third"):
        writer.write_line(line)

    archived_files = sorted((tmp_path / "run" / "archived").rglob("events.jsonl"))
    archived = [line for archive in archived_files for line in _read_lines(archive)]
    assert _read_lines(path) == ["third"]
    assert archived == ["first", "second"]
    assert len(archived_files) == 2


def test_zstd_writer_uses_configured_uncompressed_byte_limits(monkeypatch, tmp_path: Path) -> None:
    _configure_logging(
        monkeypatch,
        tmp_path,
        "[logging]\n"
        "events_max_mb = 256\n"
        "zstd_level = 1\n",
    )
    path = tmp_path / "run" / "events.jsonl"
    writer = RollingZstdJsonlWriter(str(path))

    assert writer.max_main_bytes == 256 * 1024 * 1024
    assert writer.zstd_level == 1
    assert Path(writer.base_path).name == "events.jsonl.zst"


def test_motor_trace_writer_uses_motor_trace_limits(monkeypatch, tmp_path: Path) -> None:
    _configure_logging(
        monkeypatch,
        tmp_path,
        "[logging]\n"
        "motor_trace_max_mb = 3\n"
        "log_max_mb = 99\n",
    )
    path = tmp_path / "run" / "motor_traces.jsonl"
    writer = RollingZstdJsonlWriter(str(path))

    assert writer.max_main_bytes == 3 * 1024 * 1024
    assert Path(writer.base_path).name == "motor_traces.jsonl.zst"


def test_zstd_writer_rotates_on_uncompressed_byte_cap(tmp_path: Path) -> None:
    path = tmp_path / "run" / "events.jsonl"
    writer = RollingZstdJsonlWriter(str(path), max_main_bytes=16)

    writer.write_line("1234567890")
    writer.write_line("abcdefghij")

    compressed_path = tmp_path / "run" / "events.jsonl.zst"
    assert not path.exists()
    assert _read_zstd_lines(compressed_path) == ["abcdefghij"]
    archived = [
        line
        for archive in (tmp_path / "run" / "archived").rglob("events.jsonl.zst")
        for line in _read_zstd_lines(archive)
    ]
    assert archived == ["1234567890"]


def test_standard_logger_uses_zstd_by_default_after_stream_setup(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _configure_logging(monkeypatch, tmp_path, "[logging]\n")
    name = f"rolling-jsonl-test-{uuid4()}"
    logger = get_logger(name)
    logger = get_logger(name, str(tmp_path / "run" / "events.jsonl"))
    try:
        assert any(isinstance(handler, RollingZstdJsonlHandler) for handler in logger.handlers)
        logger.info(
            "hello",
            extra={
                "extra": {
                    "tick": 7,
                    "wall_time_s": 123.5,
                    "run_elapsed_s": 1.25,
                }
            },
        )
        rows = [
            json.loads(line)
            for line in _read_zstd_lines(tmp_path / "run" / "events.jsonl.zst")
        ]
        assert rows[-1]["msg"] == "hello"
        assert rows[-1]["tick"] == 7
        assert rows[-1]["wall_time_s"] == 123.5
        assert rows[-1]["ts"] == 123.5
        assert rows[-1]["run_elapsed_s"] == 1.25
        assert not (tmp_path / "run" / "events.jsonl").exists()
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
        logging.Logger.manager.loggerDict.pop(name, None)


def test_standard_logger_can_use_plain_jsonl_for_debug_when_configured(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _configure_logging(monkeypatch, tmp_path, '[logging]\ncompression = "plain"\n')
    name = f"rolling-jsonl-test-{uuid4()}"
    logger = get_logger(name, str(tmp_path / "run" / "events.jsonl"))
    try:
        assert any(isinstance(handler, RollingJsonlHandler) for handler in logger.handlers)
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
        logging.Logger.manager.loggerDict.pop(name, None)
