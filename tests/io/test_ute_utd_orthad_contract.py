from __future__ import annotations

import json

import zstandard as zstd

from vdm_rt.io.ute import UTE
from vdm_rt.io.utd import UTD


def _jsonl_zst(path):
    dctx = zstd.ZstdDecompressor()
    with path.open("rb") as fh:
        try:
            reader = dctx.stream_reader(fh, read_across_frames=True)
        except TypeError:
            reader = dctx.stream_reader(fh)
        with reader:
            return [json.loads(line) for line in reader.read().decode("utf-8").splitlines()]


def test_ute_records_raw_orthad_input_stream_and_preserves_queue(tmp_path) -> None:
    ute = UTE(str(tmp_path), queue_maxsize=4, poll_max_items=4)
    rec = {
        "tick": 0,
        "source": "curriculum",
        "category": "Q chart",
        "cycle_index": 0,
        "atom_index": 0,
        "atom": "Q chart A",
        "stim_count": 9,
        "stim_hash": "abc123",
    }

    assert ute.push(rec) is True

    assert ute.poll() == [rec]
    assert _jsonl_zst(tmp_path / "ute_input_stream.jsonl.zst") == [rec]
    assert not (tmp_path / "ute_input_stream.jsonl").exists()


def test_ute_record_input_writes_without_queueing(tmp_path) -> None:
    ute = UTE(str(tmp_path), queue_maxsize=4, poll_max_items=4)
    rec = {
        "tick": 1,
        "source": "reafference",
        "category": "self_consequence",
        "cycle_index": -1,
        "atom_index": -1,
        "atom": "heard witness W7_0001",
        "stim_count": 6,
        "stim_hash": "def456",
    }

    assert ute.record_input(rec) is True

    assert ute.poll() == []
    assert _jsonl_zst(tmp_path / "ute_input_stream.jsonl.zst") == [rec]
    assert not (tmp_path / "ute_input_stream.jsonl").exists()


def test_utd_records_raw_motor_event_without_wrapper(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("vdm_rt.io.utd.time.time", lambda: 112.5)
    utd = UTD(str(tmp_path), run_start_wall_time_s=100.0)
    event = {
        "tick": 0,
        "witness": "W7_0001",
        "lane": "L7",
        "gate_pressure": 1.2345,
        "hold": 0.9,
        "release": 0.4,
        "inhibit": 0.0,
        "correct": 0.0,
        "source_input": "curriculum",
        "source_atom": "Q chart A",
        "top_ops": [["RELEASE", 2.0]],
        "top_lanes": [["L7", 2.0]],
    }

    assert utd.emit_motor_event(event) is True

    rows = _jsonl_zst(tmp_path / "utd_events.jsonl.zst")
    expected = dict(event)
    expected["wall_time_s"] = 112.5
    expected["ts"] = 112.5
    expected["run_elapsed_s"] = 12.5
    assert rows == [expected]
    assert rows[0]["tick"] == event["tick"]
    assert "type" not in rows[0]
    assert "event" not in rows[0]
    assert not (tmp_path / "utd_events.jsonl").exists()
