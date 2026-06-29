from __future__ import annotations

import json
from pathlib import Path

from vdm_rt.core.sensorimotor.efference import EfferenceTraceController


SEMANTIC_OP_TOKENS = {
    "SELECT",
    "HOLD",
    "RELEASE",
    "INHIBIT",
    "ADVANCE",
    "RETREAT",
    "SPLIT",
    "MERGE",
    "AMPLIFY",
    "DAMP",
    "COMPARE",
    "CORRECT",
    "COMMIT",
    "ABORT",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_core_sensorimotor_does_not_define_semantic_operation_labels() -> None:
    root = _repo_root()
    offenders: list[str] = []
    for path in sorted((root / "core" / "sensorimotor").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in SEMANTIC_OP_TOKENS:
            if token in text:
                offenders.append(f"{path.relative_to(root)} contains {token}")
    assert not offenders


def test_core_efference_packets_use_opaque_ids() -> None:
    controller = EfferenceTraceController(
        n=128,
        group_size=1,
        salt="test",
        release_threshold=0.0,
        cooldown=0,
        current_op_min=1,
        current_lane_min=1,
    )
    nodes = controller.op_groups["OP_0002"] + controller.lane_groups["LANE_0003"]

    out = controller.observe_nodes(nodes, tick=7, metrics={})

    assert out["emitted"]
    packet = out["emitted"][0]
    assert packet["lane"] == "LANE_0003"
    assert "OP_0002" in packet["op_pressure"]
    assert "LANE_0003" in packet["lane_pressure"]
    encoded = json.dumps(packet)
    for token in SEMANTIC_OP_TOKENS:
        assert token not in encoded
