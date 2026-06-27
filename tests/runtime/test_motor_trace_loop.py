from __future__ import annotations

from types import SimpleNamespace

from vdm_rt.runtime.helpers.ingest import process_messages
from vdm_rt.runtime.loop import main as loop_main


class _Trace:
    def __init__(self) -> None:
        self.records: list[tuple[str, dict]] = []

    def record_stimulation(self, record: dict) -> bool:
        self.records.append(("stimulation", dict(record)))
        return True

    def record_efferent_dynamics(self, record: dict) -> bool:
        self.records.append(("efferent_dynamics", dict(record)))
        return True

    def record_actuator_trace(self, record: dict) -> bool:
        self.records.append(("actuator_trace", dict(record)))
        return True

    def record_witness_event(self, record: dict) -> bool:
        self.records.append(("witness_event", dict(record)))
        return True


class _UTE:
    def __init__(self, messages: list[dict]) -> None:
        self._messages = list(messages)

    def poll(self):
        out = self._messages
        self._messages = []
        return out


class _Connectome:
    def __init__(self) -> None:
        self.stimulated: list[tuple[list[int], float]] = []

    def stimulate_indices(self, indices, amp=None) -> None:
        self.stimulated.append((list(indices), float(amp)))


class _Obs:
    def __init__(self, nodes) -> None:
        self.nodes = list(nodes)


class _Fold:
    def fold(self, *_args, **_kwargs) -> None:
        return None

    def snapshot(self) -> dict:
        return {}


class _Engine:
    _heat_map = None
    _exc_map = None
    _inh_map = None
    _cold_map = None

    def __init__(self) -> None:
        self._memory_field = _Fold()
        self._memory_map = _Fold()
        self._trail_map = _Fold()

    def step(self, *_args, **_kwargs) -> None:
        return None

    def snapshot(self) -> dict:
        return {}


class _Actuator:
    def __init__(self) -> None:
        self.seen_nodes: list[list[int]] = []

    def observe_nodes(self, nodes, tick: int, metrics: dict) -> dict:
        self.seen_nodes.append(list(nodes))
        return {
            "active_ops": ["RELEASE"],
            "active_lanes": ["L2"],
            "top_trace": [{"lane": "L2", "hold": 1.0, "release": 0.7}],
            "emitted": [
                {
                    "witness": "W2_0001",
                    "lane": "L2",
                    "gate_pressure": 1.7,
                }
            ],
        }


class _UTD:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def emit_motor_event(self, event: dict) -> bool:
        self.events.append(dict(event))
        return True


def test_process_messages_uses_only_explicit_receptor_indices() -> None:
    nx = SimpleNamespace(N=8)
    messages = [
        {
            "type": "text",
            "atom": "Q chart A",
            "stim_indices": [2, "3", 9, -1, "bad", 2],
        },
        {
            "atom": "ignored text without explicit indices",
        },
    ]

    text_count, stim_idxs, tick_rev_map = process_messages(nx, messages)

    assert text_count == 1
    assert stim_idxs == {2, 3}
    assert tick_rev_map == {2: "Q chart A", 3: "Q chart A"}


def test_run_loop_records_sensorimotor_handoff_rows(monkeypatch) -> None:
    def fake_tick_fold(nx, metrics, drive, td_signal, step, tick_rev_map, **_kwargs):
        nx._last_obs_batch = [_Obs([4, 5, 5])]
        nx._last_adc_metrics = {}
        return metrics, set()

    monkeypatch.setattr(loop_main, "_tick_fold", fake_tick_fold)
    monkeypatch.setattr(loop_main, "_compute_step_and_metrics", lambda *_args, **_kwargs: ({}, {}))
    monkeypatch.setattr(loop_main, "_run_scouts_once", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(loop_main, "_maybe_start_status_http", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(loop_main, "_maybe_publish_status_redis", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(loop_main, "_save_tick_checkpoint", lambda *_args, **_kwargs: None)

    trace = _Trace()
    actuator = _Actuator()
    utd = _UTD()
    connectome = _Connectome()
    nx = SimpleNamespace(
        N=8,
        dt=0.0,
        stim_amp=0.7,
        log_every=100,
        bus=None,
        bus_drain=0,
        connectome=connectome,
        ute=_UTE([{"source": "curriculum", "atom": "Q chart A", "stim_indices": [2, 3]}]),
        utd=utd,
        motor_trace=trace,
        motor_actuator=actuator,
        history=[],
        logger=SimpleNamespace(info=lambda *_args, **_kwargs: None),
        _engine=_Engine(),
        _void_scout=None,
        _evt_metrics=False,
        _phase={"phase": 0},
        _poll_control=lambda: None,
    )

    loop_main.run_loop(nx, t0=0.0, step=0, duration_s=-1)

    assert connectome.stimulated == [([2, 3], 0.7)]
    assert actuator.seen_nodes == [[4, 5, 5]]
    kinds = [kind for kind, _record in trace.records]
    assert kinds == [
        "stimulation",
        "efferent_dynamics",
        "actuator_trace",
        "witness_event",
    ]
    assert trace.records[0][1]["stim_count"] == 2
    assert trace.records[1][1]["obs_nodes_count"] == 3
    assert trace.records[2][1]["emitted_count"] == 1
    assert utd.events == [
        {
            "tick": 0,
            "witness": "W2_0001",
            "lane": "L2",
            "gate_pressure": 1.7,
        }
    ]
