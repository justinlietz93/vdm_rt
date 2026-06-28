"""
Channels: how the companion reads VDM's pushed stream and how it pushes atoms
back. Both directions are push-only and audit-free, consistent with the socket
engine's no-scan constraint -- the companion never interrogates the engine, it
only consumes appended log lines and appends input atoms.

TraceSource (read side)
    ticks()                -> ordered tick-row dicts (the clock)
    aperture_for_tick(t)   -> normalized aperture commands emitted at tick t
    witness_atoms(lo, hi)  -> set of source_atom strings that fired a witness
                              in [lo, hi]  (for the witness-lock metric)

AfferentSink (write side)
    emit(atom, meta)       -> place one atom into VDM's input stream

Two sources (replay over a finished run dir; live tail of an active run) and two
sinks (queue-file that VDM's ute can consume; socket push to the live engine).
"""
from __future__ import annotations
import csv
import json
import os
import time
from pathlib import Path
from typing import Iterator, Optional


def _norm_aperture_cmd(c: str) -> str:
    # keep the :sublevel suffix; config open/narrow sets reference
    # AP_LEVEL_TOWARD:whole / AP_LEVEL_TOWARD:char directly.
    return c


# ---------------------------------------------------------------------------
# Read side
# ---------------------------------------------------------------------------
class TraceSource:
    def ticks(self) -> Iterator[dict]:
        raise NotImplementedError

    def aperture_for_tick(self, tick: int) -> list[str]:
        raise NotImplementedError

    def witness_atoms(self, lo: int, hi: int) -> set[str]:
        raise NotImplementedError


class ReplayTraceSource(TraceSource):
    """Reads a finished run directory into memory. Used to validate the
    read/posture/logic/instrument path on real logs and to compute the
    orientation metric over real atoms."""

    def __init__(self, run_dir: str | os.PathLike):
        d = Path(run_dir)
        self._rows = list(csv.DictReader((d / "tick_rows.csv").open(encoding="utf-8")))
        self._ap: dict[int, list[str]] = {}
        ap_path = d / "aperture_events.jsonl"
        if ap_path.exists():
            for line in ap_path.open(encoding="utf-8"):
                if not line.strip():
                    continue
                e = json.loads(line)
                self._ap[int(e["tick"])] = [_norm_aperture_cmd(c) for c in e.get("aperture_commands", [])]
        # witness source atoms by tick, from utd_events and/or witness_events
        self._wit: list[tuple[int, str]] = []
        for fn in ("utd_events.jsonl",):
            p = d / fn
            if p.exists():
                for line in p.open(encoding="utf-8"):
                    if line.strip():
                        e = json.loads(line)
                        self._wit.append((int(e["tick"]), str(e.get("source_atom", ""))))
        wp = d / "witness_events.csv"
        if wp.exists():
            for r in csv.DictReader(wp.open(encoding="utf-8")):
                self._wit.append((int(float(r["tick"])), str(r.get("source_atom", r.get("text", "")))))

    def ticks(self) -> Iterator[dict]:
        yield from self._rows

    def aperture_for_tick(self, tick: int) -> list[str]:
        return self._ap.get(tick, [])

    def witness_atoms(self, lo: int, hi: int) -> set[str]:
        return {a for (t, a) in self._wit if lo <= t <= hi and a}


class FileTailTraceSource(TraceSource):
    """Tails an active run directory. Primary clock is tick_rows.csv; aperture
    and witness files are tailed alongside and indexed by tick as they arrive.
    Push-compatible: VDM appends, the companion reads new bytes, nothing scans."""

    def __init__(self, run_dir: str | os.PathLike, poll_s: float = 0.05):
        self.d = Path(run_dir)
        self.poll_s = poll_s
        self._ap: dict[int, list[str]] = {}
        self._wit: list[tuple[int, str]] = []
        self._ap_pos = 0
        self._wit_pos = 0

    def _drain_aux(self) -> None:
        ap = self.d / "aperture_events.jsonl"
        if ap.exists():
            with ap.open(encoding="utf-8") as f:
                f.seek(self._ap_pos)
                for line in f:
                    if line.strip():
                        e = json.loads(line)
                        self._ap[int(e["tick"])] = list(e.get("aperture_commands", []))
                self._ap_pos = f.tell()
        ut = self.d / "utd_events.jsonl"
        if ut.exists():
            with ut.open(encoding="utf-8") as f:
                f.seek(self._wit_pos)
                for line in f:
                    if line.strip():
                        e = json.loads(line)
                        self._wit.append((int(e["tick"]), str(e.get("source_atom", ""))))
                self._wit_pos = f.tell()

    def ticks(self) -> Iterator[dict]:
        path = self.d / "tick_rows.csv"
        while not path.exists():
            time.sleep(self.poll_s)
        with path.open(encoding="utf-8") as f:
            header = f.readline().rstrip("\n").split(",")
            buf_pos = f.tell()
            while True:
                f.seek(buf_pos)
                line = f.readline()
                if not line or not line.endswith("\n"):
                    self._drain_aux()
                    time.sleep(self.poll_s)
                    continue
                buf_pos = f.tell()
                self._drain_aux()
                # csv with quoted fields: parse this single record robustly
                row = next(csv.DictReader([",".join(header), line]))
                yield row

    def aperture_for_tick(self, tick: int) -> list[str]:
        return self._ap.get(tick, [])

    def witness_atoms(self, lo: int, hi: int) -> set[str]:
        return {a for (t, a) in self._wit if lo <= t <= hi and a}


# ---------------------------------------------------------------------------
# Write side
# ---------------------------------------------------------------------------
class AfferentSink:
    def emit(self, atom: str, meta: dict) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class QueueFileAfferentSink(AfferentSink):
    """Appends one JSON atom per emit to a queue file that VDM's ute layer
    consumes. Frame matches the ute_input_stream shape (an `atom` plus metadata),
    so the engine ingests companion atoms exactly like environment atoms."""

    def __init__(self, queue_path: str | os.PathLike):
        self.path = Path(queue_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, atom: str, meta: dict) -> None:
        frame = {"atom": atom, "source": "companion", **meta}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(frame, ensure_ascii=False) + "\n")
            f.flush()


class SocketAfferentSink(AfferentSink):
    """Pushes atoms to the live VDM socket engine.

    CONTRACT (wire to vdm_rt_socket_engine's push-only input channel):
        one newline-terminated JSON frame per atom:
            {"atom": <str>, "source": "companion", ...meta}
        sent on a connected TCP stream. This matches the push-only socket layer
        that enforces no-scan at the OS level: the companion only ever writes.
    If your engine frames differently (length-prefix, msgpack), swap _encode."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765, timeout: float = 2.0):
        import socket
        self._socket = socket
        self._sock = socket.create_connection((host, port), timeout=timeout)

    def _encode(self, atom: str, meta: dict) -> bytes:
        return (json.dumps({"atom": atom, "source": "companion", **meta},
                           ensure_ascii=False) + "\n").encode("utf-8")

    def emit(self, atom: str, meta: dict) -> None:
        self._sock.sendall(self._encode(atom, meta))

    def close(self) -> None:
        try:
            self._sock.close()
        except Exception:
            pass
