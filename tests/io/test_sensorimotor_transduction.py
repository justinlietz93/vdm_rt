from __future__ import annotations

from vdm_rt.io.actuators.virtual_keyboard.adapter import (
    KeyboardSensorimotorAdapter,
    SpatialActuationTrace,
)
from vdm_rt.io.actuators.virtual_keyboard.route import VirtualKeyboardRoute
from vdm_rt.io.transduction.afference import AfferenceTransducer
from vdm_rt.io.transduction.efference_keyboard import KeyboardGridTransducer
from vdm_rt.io.transduction.reafference import ReafferenceTransducer
from vdm_rt.io.transduction.reafferent_index import ReafferentPostureIndex


def test_keyboard_transducer_maps_spatial_trace_at_io_boundary() -> None:
    transducer = KeyboardGridTransducer(posture_index=ReafferentPostureIndex())
    packet = {
        "tick": 4,
        "lane": "LANE_0007",
        "motor_trace_id": "m000001",
        "lane_pressure": {"LANE_0007": 1.0},
        "op_pressure": {"OP_0002": 0.8, "OP_0012": 0.4},
        "trace_window_rows": [
            {
                "tick": 4,
                "active_ops": "OP_0002 OP_0012",
                "commands": "OP_0002:LANE_0007",
                "gate_pressure": 1.2,
                "release_score": 0.9,
                "witness": "W7_0001",
            }
        ],
    }

    out = transducer.translate(
        packet,
        spatial_segment=[{"tick": 4, "x": 0.875, "y": -0.875, "drive": 1.0}],
    )

    assert out["channel_id"] == "keyboard.symbol_grid"
    assert out["key_row"] == 7
    assert out["key_col"] == 7
    assert "op_bin_pressure" not in out
    projection = out["research_projection_2048"]
    assert projection["submitted_to_reafference"] is False
    assert projection["axis_vector"]["release_pressure"] > 0
    assert projection["axis_vector"]["readiness"] > 0


def test_keyboard_actuator_owns_spatial_trace_not_transduction() -> None:
    assert SpatialActuationTrace.__module__ == "vdm_rt.io.actuators.virtual_keyboard.adapter"
    assert KeyboardSensorimotorAdapter.__module__ == "vdm_rt.io.actuators.virtual_keyboard.adapter"


def test_reafference_transducer_returns_ordered_repeated_raw_units() -> None:
    afference = AfferenceTransducer(n=64, group_size=1, salt="test")
    reafference = ReafferenceTransducer(afference)
    output_event = {
        "payload": {
            "motor_trace_id": "m000001",
            "output_text": "aa",
        }
    }

    events = reafference.events_from_output(output_event, tick=9)

    assert [event["atom"] for event in events] == ["a", "a"]
    assert [event["sequence_index"] for event in events] == [0, 1]
    assert events[0]["stim_indices"] != events[1]["stim_indices"]
    assert all(event["source"] == "reafference" for event in events)


class _UTE:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def push(self, event: dict) -> bool:
        self.records.append(dict(event))
        return True


class _Trace:
    def __init__(self) -> None:
        self.records: list[tuple[str, dict]] = []

    def record(self, trace_kind: str, record: dict) -> bool:
        self.records.append((trace_kind, dict(record)))
        return True


def test_virtual_keyboard_route_renders_witness_and_pushes_reafference() -> None:
    ute = _UTE()
    trace = _Trace()
    afference = AfferenceTransducer(n=64, group_size=1, salt="router")
    route = VirtualKeyboardRoute(
        ute=ute,
        reafference=ReafferenceTransducer(afference),
        sensorimotor_trace=trace,
    )
    event = {
        "tick": 3,
        "channel_id": "keyboard.symbol_grid",
        "motor_trace_id": "m000002",
        "witness": "W0_0001",
        "spatial_segment": [{"tick": 3, "x": -0.875, "y": 0.875, "drive": 1.0}],
    }

    routed = route(event)

    assert routed[0]["trace_kind"] == "keyboard_output_event"
    assert routed[0]["payload"]["output_text"] == "a"
    assert [rec["atom"] for rec in ute.records] == ["a"]
    assert [kind for kind, _ in trace.records] == [
        "keyboard_output_event",
        "reafference_pair",
    ]
