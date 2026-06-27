from __future__ import annotations

import json

import zstandard as zstd

from vdm_rt.io.ute import UTE
from vdm_rt.io.utd import UTD
from vdm_rt.io.motor_trace import MotorTraceLog


def _jsonl_zst(path):
    dctx = zstd.ZstdDecompressor()
    with path.open("rb") as fh:
        try:
            reader = dctx.stream_reader(fh, read_across_frames=True)
        except TypeError:
            reader = dctx.stream_reader(fh)
        with reader:
            return [json.loads(line) for line in reader.read().decode("utf-8").splitlines()]


def test_ute_records_motor_trace_input_and_preserves_queue(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("vdm_rt.io.motor_trace.time.time", lambda: 101.0)
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
    rows = _jsonl_zst(tmp_path / "motor_traces.jsonl.zst")
    expected = dict(rec)
    expected["trace_kind"] = "ute_input"
    expected["wall_time_s"] = 101.0
    expected["ts"] = 101.0
    expected["run_elapsed_s"] = 0.0
    assert rows == [expected]
    assert not (tmp_path / "ute_input_stream.jsonl").exists()
    assert not (tmp_path / "ute_input_stream.jsonl.zst").exists()


def test_ute_record_input_classifies_reafference_without_queueing(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("vdm_rt.io.motor_trace.time.time", lambda: 112.5)
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
    rows = _jsonl_zst(tmp_path / "motor_traces.jsonl.zst")
    expected = dict(rec)
    expected["trace_kind"] = "afferent_reaction"
    expected["wall_time_s"] = 112.5
    expected["ts"] = 112.5
    expected["run_elapsed_s"] = 0.0
    assert rows == [expected]
    assert not (tmp_path / "ute_input_stream.jsonl").exists()
    assert not (tmp_path / "ute_input_stream.jsonl.zst").exists()


def test_utd_records_raw_motor_event_without_wrapper(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("vdm_rt.io.motor_trace.time.time", lambda: 112.5)
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

    rows = _jsonl_zst(tmp_path / "motor_traces.jsonl.zst")
    expected = dict(event)
    expected["trace_kind"] = "utd_actuation"
    expected["wall_time_s"] = 112.5
    expected["ts"] = 112.5
    expected["run_elapsed_s"] = 12.5
    assert rows == [expected]
    assert rows[0]["tick"] == event["tick"]
    assert "type" not in rows[0]
    assert "event" not in rows[0]
    assert not (tmp_path / "utd_events.jsonl").exists()
    assert not (tmp_path / "utd_events.jsonl.zst").exists()


def test_motor_trace_records_reserved_sensorimotor_trace_kinds(monkeypatch, tmp_path) -> None:
    ticks = iter([200.0, 201.0, 202.0, 203.0])
    monkeypatch.setattr("vdm_rt.io.motor_trace.time.time", lambda: next(ticks))
    trace = MotorTraceLog(str(tmp_path), run_start_wall_time_s=100.0)

    assert trace.record_efferent_dynamics({"tick": 2, "primitive": "RELEASE"}) is True
    assert trace.record_stimulation({"tick": 2, "stim_count": 9}) is True
    assert trace.record_actuator_trace({"tick": 2, "trace_id": "T2", "top_ops": [["RELEASE", 2.0]]}) is True
    assert trace.record_witness_event({"tick": 2, "witness": "W7_0001"}) is True

    rows = _jsonl_zst(tmp_path / "motor_traces.jsonl.zst")
    assert [row["trace_kind"] for row in rows] == [
        "efferent_dynamics",
        "stimulation",
        "actuator_trace",
        "witness_event",
    ]
    assert [row["run_elapsed_s"] for row in rows] == [100.0, 101.0, 102.0, 103.0]
