"""Configuration and data-retention tests for external JSONL logging."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest

from vdm_rt.config import load_runtime_config
from vdm_rt.io.logging.rolling_jsonl import (
    RollingJsonlHandler,
    RollingJsonlWriter,
    RollingZipJsonlHandler,
    RollingZipJsonlWriter,
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


def test_zip_spool_reads_exact_configured_byte_limits(monkeypatch, tmp_path: Path) -> None:
    _configure_logging(
        monkeypatch,
        tmp_path,
        "[logging]\n"
        "zip_buffer_bytes = 16\n"
        "zip_ring_bytes = 5\n",
    )
    path = tmp_path / "run" / "events.jsonl"
    writer = RollingZipJsonlWriter(str(path))

    assert writer.max_buffer_bytes == 16
    assert writer._ring_cap == 5
    writer.write_line("1234567890")
    writer.write_line("abcdefghij")

    assert path.read_bytes() == b""
    with zipfile.ZipFile(writer.zip_path) as archive:
        assert archive.read(archive.namelist()[0]).decode("utf-8") == "1234567890\nabcdefghij\n"


@pytest.mark.parametrize(
    ("zip_spool", "handler_type"),
    ((True, RollingZipJsonlHandler), (False, RollingJsonlHandler)),
)
def test_standard_logger_honors_spool_mode_config_after_stream_setup(
    monkeypatch,
    tmp_path: Path,
    zip_spool: bool,
    handler_type: type[logging.Handler],
) -> None:
    _configure_logging(monkeypatch, tmp_path, f"[logging]\nzip_spool = {str(zip_spool).lower()}\n")
    name = f"rolling-jsonl-test-{uuid4()}"
    logger = get_logger(name)
    logger = get_logger(name, str(tmp_path / "run" / "events.jsonl"))
    try:
        assert any(isinstance(handler, handler_type) for handler in logger.handlers)
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
        logging.Logger.manager.loggerDict.pop(name, None)
