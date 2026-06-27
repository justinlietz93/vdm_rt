"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.


Rolling JSONL writers with bounded main files and archival segments.

- Maintains capped active JSONL streams.
- The default runtime writer stores JSONL records immediately in zstd-compressed
  files (e.g., events.jsonl.zst, utd_events.jsonl.zst).
- A plain JSONL debug writer remains available when explicitly configured.
- When the active file exceeds the configured size or line cap, the oldest lines
  are archived for the plain writer; the zstd writer rotates the active
  compressed segment when its uncompressed payload cap is reached.
- Archive segments live under: <run_dir>/archived/<YYYYMMDD_HHMMSS>/<base_name>
  Example: runs/<ts>/archived/20250815_120828/events.jsonl.zst
- When the current archive segment exceeds its cap, a new timestamped segment
  directory is created and subsequent archival lines are appended there.

Configuration lives in config/logging.toml [logging].

Notes:
- Uses a cross-process advisory lock via <base_path>.lock to serialize trimming with writers.
- Writers should not hold persistent file handles; always append per call.
"""

from __future__ import annotations

import io
import json
import os
import time
import threading
from typing import Optional, Tuple

from vdm_rt.config import config_int

try:
    import fcntl as _fcntl
except Exception:  # non-posix fallback (no-op locks)
    _fcntl = None


def _now_ts() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def _zstd_path(path: str) -> str:
    return path if path.endswith(".zst") else f"{path}.zst"


def _is_ts_dir(name: str) -> bool:
    # YYYYMMDD_HHMMSS
    if len(name) != 15:
        return False
    d, u = name.split("_", 1) if "_" in name else ("", "")
    return d.isdigit() and u.isdigit() and len(d) == 8 and len(u) == 6


class RollingJsonlWriter:
    """
    Append-only JSONL writer with rolling buffer and archival segments.

    Usage:
        w = RollingJsonlWriter("/path/to/events.jsonl")
        w.write_line('{"msg":"hello"}')
    """

    def __init__(
        self,
        base_path: str,
        *,
        max_main_bytes: Optional[int] = None,
        max_main_lines: Optional[int] = None,
        archive_dir: Optional[str] = None,
        archive_segment_max_bytes: Optional[int] = None,
        archive_segment_max_lines: Optional[int] = None,
        check_every: Optional[int] = None,
    ) -> None:
        self.base_path = os.path.abspath(base_path)
        _ensure_dir(os.path.dirname(self.base_path))
        self.lock_path = self.base_path + ".lock"
        self._local_lock = threading.Lock()

        base_name = os.path.basename(self.base_path).lower()
        if base_name == "events.jsonl":
            cat = "EVENTS"
        elif "utd" in base_name:
            cat = "UTD"
        else:
            cat = "LOG"

        # Defaults via config/logging.toml (prefer bytes caps unless line caps are set).
        def _cfg_int(key: str, default: Optional[int]) -> Optional[int]:
            if default is None:
                value = config_int(key, 0)
                return None if value <= 0 else value
            return config_int(key, int(default))

        if max_main_bytes is None:
            if cat == "EVENTS":
                max_main_bytes = _cfg_int("logging.events_max_mb", 256)
            elif cat == "UTD":
                max_main_bytes = _cfg_int("logging.utd_max_mb", 256)
            else:
                max_main_bytes = _cfg_int("logging.log_max_mb", 128)
            max_main_bytes = int(max_main_bytes) * 1024 * 1024 if max_main_bytes else None

        if max_main_lines is None:
            if cat == "EVENTS":
                max_main_lines = _cfg_int("logging.events_max_lines", None)
            elif cat == "UTD":
                max_main_lines = _cfg_int("logging.utd_max_lines", None)
            else:
                max_main_lines = _cfg_int("logging.log_max_lines", None)

        if archive_dir is None:
            archive_dir = os.path.join(os.path.dirname(self.base_path), "archived")
        self.archive_dir = archive_dir

        if archive_segment_max_bytes is None:
            if cat == "EVENTS":
                archive_segment_max_bytes = _cfg_int("logging.events_archive_segment_mb", 512)
            elif cat == "UTD":
                archive_segment_max_bytes = _cfg_int("logging.utd_archive_segment_mb", 512)
            else:
                archive_segment_max_bytes = _cfg_int("logging.log_archive_segment_mb", 256)
            archive_segment_max_bytes = (
                int(archive_segment_max_bytes) * 1024 * 1024 if archive_segment_max_bytes else None
            )

        if archive_segment_max_lines is None:
            if cat == "EVENTS":
                archive_segment_max_lines = _cfg_int("logging.events_archive_segment_lines", None)
            elif cat == "UTD":
                archive_segment_max_lines = _cfg_int("logging.utd_archive_segment_lines", None)
            else:
                archive_segment_max_lines = _cfg_int("logging.log_archive_segment_lines", None)

        self.max_main_bytes = max_main_bytes
        self.max_main_lines = max_main_lines
        self.archive_segment_max_bytes = archive_segment_max_bytes
        self.archive_segment_max_lines = archive_segment_max_lines

        if check_every is None:
            check_every = _cfg_int("logging.roll_check_every", 1) or 1
        self._check_every = max(1, int(check_every))
        self._ops = 0

    # ------------- public -------------
    def write_line(self, line: str) -> None:
        data = (line.rstrip("\n") + "\n").encode("utf-8", errors="ignore")
        with self._local_lock:
            with self._acquire_lock():
                # append
                with open(self.base_path, "ab") as fh:
                    fh.write(data)
                self._ops += 1
                if (self._ops % self._check_every) == 0:
                    self._enforce()

    # ------------- internals -------------
    def _acquire_lock(self):
        class _Locker:
            def __init__(self, p: str) -> None:
                self.p = p
                self.fh = None

            def __enter__(self):
                _ensure_dir(os.path.dirname(self.p))
                self.fh = open(self.p, "a+")
                if _fcntl is not None:
                    _fcntl.flock(self.fh.fileno(), _fcntl.LOCK_EX)
                return self

            def __exit__(self, exc_type, exc, tb):
                try:
                    if _fcntl is not None and self.fh is not None:
                        _fcntl.flock(self.fh.fileno(), _fcntl.LOCK_UN)
                finally:
                    try:
                        if self.fh:
                            self.fh.close()
                    except Exception:
                        pass

        return _Locker(self.lock_path)

    def _enforce(self) -> None:
        """Trim oldest lines to keep main file under configured cap and move trimmed lines to archive."""
        try:
            size = os.path.getsize(self.base_path)
        except Exception:
            return

        # Prefer bytes cap unless a line cap is explicitly configured
        if self.max_main_lines and self.max_main_lines > 0:
            self._enforce_by_lines(self.max_main_lines)
        elif self.max_main_bytes and size > self.max_main_bytes:
            to_remove = size - self.max_main_bytes
            self._trim_oldest_bytes_to_archive(to_remove)

    def _enforce_by_lines(self, keep_last_lines: int) -> None:
        try:
            # Count lines
            total = 0
            with open(self.base_path, "rb") as fh:
                for _ in fh:
                    total += 1
            if total <= keep_last_lines:
                return
            to_remove = total - keep_last_lines

            # Stream: first 'to_remove' lines -> archive; remainder -> temp; then replace
            self._stream_archive_and_tail(to_remove_lines=to_remove)
        except Exception:
            return

    def _trim_oldest_bytes_to_archive(self, remove_bytes: int) -> None:
        if remove_bytes <= 0:
            return
        # Best-effort: move enough whole lines to cover remove_bytes
        moved = 0
        try:
            seg_fh, _ = self._open_archive_for_append()
            try:
                tmp_path = self.base_path + ".tmp"
                with open(self.base_path, "rb") as src, open(tmp_path, "wb") as dst:
                    for line in src:
                        if moved < remove_bytes:
                            # ensure we rotate segment if needed
                            seg_fh = self._seg_write(seg_fh, line)
                            moved += len(line)
                        else:
                            dst.write(line)
                # Replace atomically
                os.replace(tmp_path, self.base_path)
            finally:
                try:
                    if seg_fh:
                        seg_fh.close()
                except Exception:
                    pass
        except Exception:
            return

    def _stream_archive_and_tail(self, to_remove_lines: int) -> None:
        if to_remove_lines <= 0:
            return
        removed = 0
        try:
            seg_fh, _ = self._open_archive_for_append()
            try:
                tmp_path = self.base_path + ".tmp"
                with open(self.base_path, "rb") as src, open(tmp_path, "wb") as dst:
                    for line in src:
                        if removed < to_remove_lines:
                            seg_fh = self._seg_write(seg_fh, line)
                            removed += 1
                        else:
                            dst.write(line)
                os.replace(tmp_path, self.base_path)
            finally:
                try:
                    if seg_fh:
                        seg_fh.close()
                except Exception:
                    pass
        except Exception:
            return

    # ----- archive segment helpers -----
    def _open_archive_for_append(self) -> Tuple[io.BufferedWriter, str]:
        """
        Return a file handle opened for appending to the current archive segment and the segment dir.
        Creates archive dir/segment as needed.
        """
        _ensure_dir(self.archive_dir)
        # Reuse the latest segment only while it remains below its configured cap.
        try:
            dirs = [d for d in os.listdir(self.archive_dir) if _is_ts_dir(d)]
        except Exception:
            dirs = []
        if dirs:
            dirs.sort()
            seg_dir = os.path.join(self.archive_dir, dirs[-1])
            arch_file = os.path.join(seg_dir, os.path.basename(self.base_path))
            if not self._segment_full(arch_file):
                return open(arch_file, "ab"), seg_dir

        seg_dir = self._create_archive_segment_dir()
        arch_file = os.path.join(seg_dir, os.path.basename(self.base_path))

        fh = open(arch_file, "ab")
        return fh, seg_dir

    def _create_archive_segment_dir(self) -> str:
        """Create a distinct timestamp segment, even during same-second rotation."""
        _ensure_dir(self.archive_dir)
        epoch = time.time()
        for offset in range(86_400):
            name = time.strftime("%Y%m%d_%H%M%S", time.localtime(epoch + offset))
            candidate = os.path.join(self.archive_dir, name)
            try:
                os.mkdir(candidate)
                return candidate
            except FileExistsError:
                continue
        raise OSError(f"Unable to create archive segment under {self.archive_dir}")

    def _segment_full(self, arch_file: str) -> bool:
        try:
            size = os.path.getsize(arch_file)
        except Exception:
            size = 0
        # bytes-based check first
        if self.archive_segment_max_bytes and self.archive_segment_max_bytes > 0:
            if size >= self.archive_segment_max_bytes:
                return True
        # optional lines-based check
        if self.archive_segment_max_lines and self.archive_segment_max_lines > 0:
            try:
                cnt = 0
                with open(arch_file, "rb") as fh:
                    for _ in fh:
                        cnt += 1
                if cnt >= self.archive_segment_max_lines:
                    return True
            except Exception:
                return False
        return False

    def _seg_write(self, seg_fh: io.BufferedWriter, line: bytes) -> io.BufferedWriter:
        """Append one line and return an open segment handle for the next write."""
        try:
            if self._segment_full(seg_fh.name):  # type: ignore[attr-defined]
                seg_fh.close()
                seg_fh, _ = self._open_archive_for_append()
        except Exception:
            pass
        try:
            seg_fh.write(line)
            seg_fh.flush()
        except Exception:
            return seg_fh
        return seg_fh


class RollingZstdJsonlWriter:
    """
    Append JSONL records into an immediately compressed zstd stream.

    The active file is <logical>.zst, for example events.jsonl.zst. Rotation is
    based on the uncompressed JSONL bytes in the active compressed stream, so
    logging.events_max_mb = 256 means 256 MiB of JSONL payload before rollover.
    """

    def __init__(
        self,
        base_path: str,
        *,
        max_main_bytes: Optional[int] = None,
        max_main_lines: Optional[int] = None,
        archive_dir: Optional[str] = None,
        zstd_level: Optional[int] = None,
    ) -> None:
        self.logical_path = os.path.abspath(base_path)
        self.base_path = os.path.abspath(_zstd_path(self.logical_path))
        _ensure_dir(os.path.dirname(self.base_path))
        self.lock_path = self.base_path + ".lock"
        self.meta_path = self.base_path + ".meta.json"
        self._local_lock = threading.Lock()

        try:
            import zstandard as _zstd  # type: ignore
        except Exception as exc:  # pragma: no cover - covered by dependency gate
            raise RuntimeError(
                "zstandard is required for runtime JSONL logging. "
                "Install requirements.txt before launching vdm_rt."
            ) from exc
        self._zstd = _zstd

        base_name = os.path.basename(self.logical_path).lower()
        if base_name.endswith(".zst"):
            base_name = base_name[:-4]
        if base_name == "events.jsonl":
            cat = "EVENTS"
        elif "utd" in base_name:
            cat = "UTD"
        else:
            cat = "LOG"

        def _cfg_int(key: str, default: Optional[int]) -> Optional[int]:
            if default is None:
                value = config_int(key, 0)
                return None if value <= 0 else value
            return config_int(key, int(default))

        if max_main_bytes is None:
            if cat == "EVENTS":
                max_main_bytes = _cfg_int("logging.events_max_mb", 256)
            elif cat == "UTD":
                max_main_bytes = _cfg_int("logging.utd_max_mb", 256)
            else:
                max_main_bytes = _cfg_int("logging.log_max_mb", 256)
            max_main_bytes = int(max_main_bytes) * 1024 * 1024 if max_main_bytes else None

        if max_main_lines is None:
            if cat == "EVENTS":
                max_main_lines = _cfg_int("logging.events_max_lines", None)
            elif cat == "UTD":
                max_main_lines = _cfg_int("logging.utd_max_lines", None)
            else:
                max_main_lines = _cfg_int("logging.log_max_lines", None)

        if archive_dir is None:
            archive_dir = os.path.join(os.path.dirname(self.base_path), "archived")
        self.archive_dir = archive_dir
        self.max_main_bytes = max_main_bytes
        self.max_main_lines = max_main_lines
        configured_level = (
            config_int("logging.zstd_level", 3)
            if zstd_level is None
            else int(zstd_level)
        )
        self.zstd_level = max(1, min(22, configured_level))

    def write_record(self, record: dict) -> None:
        self.write_line(json.dumps(record, ensure_ascii=False, sort_keys=True))

    def write_line(self, line: str) -> None:
        data = (line.rstrip("\n") + "\n").encode("utf-8", errors="ignore")
        with self._local_lock:
            with self._acquire_lock():
                meta = self._read_meta()
                if self._should_rotate(meta, len(data)):
                    self._rotate_active()
                    meta = {"uncompressed_bytes": 0, "lines": 0}
                self._append_compressed(data)
                meta["uncompressed_bytes"] = int(meta.get("uncompressed_bytes", 0)) + len(data)
                meta["lines"] = int(meta.get("lines", 0)) + 1
                self._write_meta(meta)

    def stats(self) -> dict:
        meta = self._read_meta()
        try:
            active_compressed_bytes = os.path.getsize(self.base_path)
        except Exception:
            active_compressed_bytes = 0
        return {
            "active_path": self.base_path,
            "active_compressed_bytes": int(active_compressed_bytes),
            "active_uncompressed_bytes": int(meta.get("uncompressed_bytes", 0)),
            "active_lines": int(meta.get("lines", 0)),
        }

    def _should_rotate(self, meta: dict, next_uncompressed_bytes: int) -> bool:
        try:
            if os.path.getsize(self.base_path) <= 0:
                return False
        except Exception:
            return False
        if self.max_main_lines and int(meta.get("lines", 0)) >= self.max_main_lines:
            return True
        if self.max_main_bytes:
            current = int(meta.get("uncompressed_bytes", 0))
            if current > 0 and current + next_uncompressed_bytes > self.max_main_bytes:
                return True
        return False

    def _append_compressed(self, data: bytes) -> None:
        cctx = self._zstd.ZstdCompressor(level=self.zstd_level)
        with open(self.base_path, "ab") as fh:
            fh.write(cctx.compress(data))

    def _read_meta(self) -> dict:
        try:
            if os.path.getsize(self.base_path) <= 0:
                return {"uncompressed_bytes": 0, "lines": 0}
        except Exception:
            return {"uncompressed_bytes": 0, "lines": 0}
        try:
            with open(self.meta_path, "r", encoding="utf-8") as fh:
                meta = json.load(fh)
            return {
                "uncompressed_bytes": max(0, int(meta.get("uncompressed_bytes", 0))),
                "lines": max(0, int(meta.get("lines", 0))),
            }
        except Exception:
            stats = self._scan_active_stream()
            self._write_meta(stats)
            return stats

    def _write_meta(self, meta: dict) -> None:
        tmp_path = self.meta_path + ".tmp"
        payload = {
            "format": "jsonl.zst",
            "active_path": os.path.basename(self.base_path),
            "uncompressed_bytes": int(meta.get("uncompressed_bytes", 0)),
            "lines": int(meta.get("lines", 0)),
        }
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_path, self.meta_path)

    def _scan_active_stream(self) -> dict:
        if not os.path.exists(self.base_path):
            return {"uncompressed_bytes": 0, "lines": 0}
        total = 0
        lines = 0
        dctx = self._zstd.ZstdDecompressor()
        try:
            with open(self.base_path, "rb") as fh:
                try:
                    reader = dctx.stream_reader(fh, read_across_frames=True)
                except TypeError:
                    reader = dctx.stream_reader(fh)
                with reader:
                    while True:
                        chunk = reader.read(131072)
                        if not chunk:
                            break
                        total += len(chunk)
                        lines += chunk.count(b"\n")
        except Exception:
            return {"uncompressed_bytes": 0, "lines": 0}
        return {"uncompressed_bytes": total, "lines": lines}

    def _rotate_active(self) -> None:
        try:
            if os.path.getsize(self.base_path) <= 0:
                return
        except Exception:
            return
        seg_dir = self._create_archive_segment_dir()
        target = os.path.join(seg_dir, os.path.basename(self.base_path))
        os.replace(self.base_path, target)
        self._write_meta({"uncompressed_bytes": 0, "lines": 0})

    def _create_archive_segment_dir(self) -> str:
        _ensure_dir(self.archive_dir)
        epoch = time.time()
        for offset in range(86_400):
            name = time.strftime("%Y%m%d_%H%M%S", time.localtime(epoch + offset))
            candidate = os.path.join(self.archive_dir, name)
            try:
                os.mkdir(candidate)
                return candidate
            except FileExistsError:
                continue
        raise OSError(f"Unable to create archive segment under {self.archive_dir}")

    def _acquire_lock(self):
        class _Locker:
            def __init__(self, p: str) -> None:
                self.p = p
                self.fh = None

            def __enter__(self):
                _ensure_dir(os.path.dirname(self.p))
                self.fh = open(self.p, "a+")
                if _fcntl is not None:
                    _fcntl.flock(self.fh.fileno(), _fcntl.LOCK_EX)
                return self

            def __exit__(self, exc_type, exc, tb):
                try:
                    if _fcntl is not None and self.fh is not None:
                        _fcntl.flock(self.fh.fileno(), _fcntl.LOCK_UN)
                finally:
                    try:
                        if self.fh:
                            self.fh.close()
                    except Exception:
                        pass

        return _Locker(self.lock_path)


# ---------- Logging handler integration ----------

import logging


class RollingJsonlHandler(logging.Handler):
    """
    logging.Handler that writes formatted JSON lines to a bounded rolling JSONL file.
    """
    def __init__(self, path: str) -> None:
        super().__init__(level=logging.INFO)
        self._writer = RollingJsonlWriter(path)
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self._writer.write_line(msg)
        except Exception:
            # Avoid crashing logging subsystem
            pass


class RollingZstdJsonlHandler(logging.Handler):
    """
    logging.Handler that writes formatted JSON lines to immediate zstd JSONL.
    """
    def __init__(self, path: str) -> None:
        super().__init__(level=logging.INFO)
        self._writer = RollingZstdJsonlWriter(path)
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self._writer.write_line(msg)
        except Exception:
            # Avoid crashing logging subsystem
            pass

__all__ = [
    "RollingJsonlWriter",
    "RollingJsonlHandler",
    "RollingZstdJsonlWriter",
    "RollingZstdJsonlHandler",
]
