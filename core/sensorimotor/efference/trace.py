from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

from vdm_rt.core.sensorimotor.basis import short_hash_text
from vdm_rt.core.sensorimotor.efference.basis import (
    DEFAULT_LANES,
    DEFAULT_OPERATIONS,
    FixedEfferenceBasis,
    reverse_index,
)


def center_of_mass(values: List[float]) -> Optional[float]:
    total = float(sum(values))
    if total <= 0.0:
        return None
    return float(sum(i * float(v) for i, v in enumerate(values)) / total)


class EfferenceTraceController:
    """
    Sparse, hardware-agnostic operation/lane trace.

    This object consumes observed node ids and produces abstract primitive
    actuation packets. It does not know keyboards, characters, files, wall time,
    OS devices, 2048 utterance banks, semantic operation names, or rendered
    witnesses.
    """

    def __init__(
        self,
        n: int,
        group_size: int = 8,
        salt: str = "sensorimotor:efference",
        release_threshold: float = 0.82,
        decay: float = 0.965,
        cooldown: int = 8,
        current_op_min: int = 2,
        current_lane_min: int = 2,
        max_segment: int = 2048,
    ) -> None:
        self.basis = FixedEfferenceBasis(
            n=int(n),
            group_size=int(group_size),
            salt=str(salt),
        )
        self.operations = tuple(DEFAULT_OPERATIONS)
        self.lanes = tuple(DEFAULT_LANES)
        self.op_groups = self.basis.op_groups()
        self.lane_groups = self.basis.lane_groups()
        self.node_to_ops = reverse_index(self.op_groups)
        self.node_to_lanes = reverse_index(self.lane_groups)

        self.release_threshold = float(release_threshold)
        self.decay = float(decay)
        self.cooldown = int(cooldown)
        self.current_op_min = int(current_op_min)
        self.current_lane_min = int(current_lane_min)
        self.max_segment = int(max(1, max_segment))

        self.op_energy = {op: 0.0 for op in self.operations}
        self.lane_energy = {lane: 0.0 for lane in self.lanes}
        self.lane_hold = {lane: 0.0 for lane in self.lanes}
        self.lane_inhibit = {lane: 0.0 for lane in self.lanes}
        self.lane_release = {lane: 0.0 for lane in self.lanes}
        self.lane_correct = {lane: 0.0 for lane in self.lanes}
        self.intent_segment: List[Dict[str, Any]] = []
        self.trace_rows: List[Dict[str, Any]] = []
        self.last_emit = -10**12
        self.witness_count = 0
        self.trace_count = 0

    def observe_nodes(
        self,
        nodes: Iterable[int],
        tick: int,
        metrics: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        for state in (
            self.op_energy,
            self.lane_energy,
            self.lane_hold,
            self.lane_inhibit,
            self.lane_release,
            self.lane_correct,
        ):
            for key in state:
                state[key] *= self.decay

        touched_ops: Counter[str] = Counter()
        touched_lanes: Counter[str] = Counter()
        for raw_node in nodes or []:
            try:
                node = int(raw_node)
            except Exception:
                continue
            for op in self.node_to_ops.get(node, []):
                touched_ops[op] += 1
            for lane in self.node_to_lanes.get(node, []):
                touched_lanes[lane] += 1

        for op, count in touched_ops.items():
            self.op_energy[op] += float(count)
        for lane, count in touched_lanes.items():
            self.lane_energy[lane] += float(count)

        active_ops = [op for op, count in touched_ops.items() if count >= self.current_op_min]
        active_lanes = [
            lane for lane, count in touched_lanes.items() if count >= self.current_lane_min
        ]
        commands = self._apply_commands(int(tick), active_ops, active_lanes, touched_ops, touched_lanes)

        strongest = max(self.lanes, key=lambda l: self.lane_hold[l] + self.lane_release[l])
        release_score = (
            self.lane_hold[strongest]
            + self.lane_release[strongest]
            - 0.35 * self.lane_inhibit[strongest]
        )
        release_ops = (self.operations[2], self.operations[12])
        commit_pressure = max(float(touched_ops.get(op, 0)) for op in release_ops)
        release_intent = any(op in active_ops for op in release_ops)
        gate_pressure = release_score + 0.10 * commit_pressure

        trace_row = {
            "tick": int(tick),
            "active_ops": " ".join(active_ops),
            "active_lanes": " ".join(active_lanes),
            "commands": " ".join(f"{c['op']}:{c['lane']}" for c in commands),
            "gate_pressure": round(float(gate_pressure), 6),
            "release_score": round(float(release_score), 6),
            "witness": "",
        }
        self.trace_rows.append(trace_row)
        if len(self.trace_rows) > self.max_segment:
            self.trace_rows = self.trace_rows[-self.max_segment :]

        emitted: List[Dict[str, Any]] = []
        if (
            release_intent
            and gate_pressure >= self.release_threshold
            and (int(tick) - self.last_emit) >= self.cooldown
        ):
            emitted.append(
                self._build_packet(
                    tick=int(tick),
                    lane=strongest,
                    gate_pressure=gate_pressure,
                    release_score=release_score,
                )
            )

        return {
            "active_ops": active_ops,
            "active_lanes": active_lanes,
            "commands": commands,
            "emitted": emitted,
            "top_ops": self.top_ops(6),
            "top_lanes": self.top_lanes(6),
            "top_trace": self.top_trace(4),
            "release_lane": strongest,
            "release_score": round(float(release_score), 4),
            "gate_pressure": round(float(gate_pressure), 4),
            "basis_id": self.basis.identity(),
            "full_selector_state": self.state_dict(),
        }

    def observe(self, nodes: Iterable[int], tick: int, metrics: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return self.observe_nodes(nodes, tick=tick, metrics=metrics)

    def _apply_commands(
        self,
        tick: int,
        active_ops: List[str],
        active_lanes: List[str],
        touched_ops: Counter[str],
        touched_lanes: Counter[str],
    ) -> List[Dict[str, Any]]:
        commands: List[Dict[str, Any]] = []
        if not active_ops or not active_lanes:
            return commands
        sorted_ops = sorted(active_ops, key=lambda op: touched_ops[op], reverse=True)
        sorted_lanes = sorted(active_lanes, key=lambda lane: touched_lanes[lane], reverse=True)
        for lane in sorted_lanes[:3]:
            for op in sorted_ops[:4]:
                amp = min(
                    1.0,
                    (
                        touched_ops[op] / max(1, self.current_op_min)
                        + touched_lanes[lane] / max(1, self.current_lane_min)
                    )
                    / 6.0,
                )
                cmd = {"tick": int(tick), "op": op, "lane": lane, "amp": round(float(amp), 4)}
                commands.append(cmd)
                self.intent_segment.append(cmd)
                if len(self.intent_segment) > self.max_segment:
                    self.intent_segment = self.intent_segment[-self.max_segment :]
                op_idx = self.operations.index(op) if op in self.operations else -1
                if op_idx in (0, 4, 6, 7, 8, 10):
                    self.lane_hold[lane] += 0.12 * amp
                if op_idx == 1:
                    self.lane_hold[lane] += 0.25 * amp
                if op_idx == 3:
                    self.lane_inhibit[lane] += 0.30 * amp
                if op_idx in (2, 12):
                    self.lane_release[lane] += 0.35 * amp
                if op_idx == 11:
                    self.lane_correct[lane] += 0.35 * amp
                if op_idx in (5, 9, 13):
                    self.lane_hold[lane] *= 0.65
                    self.lane_release[lane] *= 0.65
        return commands

    def _build_packet(
        self,
        tick: int,
        lane: str,
        gate_pressure: float,
        release_score: float,
    ) -> Dict[str, Any]:
        self.last_emit = int(tick)
        self.witness_count += 1
        self.trace_count += 1

        lane_index = self.lanes.index(lane) if lane in self.lanes else 0
        witness = f"W{lane_index}_{self.witness_count:04d}"
        segment = list(self.intent_segment)
        rows = list(self.trace_rows)
        if rows:
            rows[-1]["witness"] = witness

        lane_pressure = {lane_name: 0.0 for lane_name in self.lanes}
        op_pressure = {op: 0.0 for op in self.operations}
        for cmd in segment:
            cmd_lane = str(cmd.get("lane", ""))
            cmd_op = str(cmd.get("op", ""))
            amp = float(cmd.get("amp", 0.0) or 0.0)
            if cmd_lane in lane_pressure:
                lane_pressure[cmd_lane] += amp
            if cmd_op in op_pressure:
                op_pressure[cmd_op] += amp

        raw = "".join(f"{c.get('lane')}:{c.get('op')}@{c.get('amp')}|" for c in segment)
        packet = {
            "trace_kind": "primitive_actuation",
            "primitive_actuation_packet": True,
            "action_kind": "sensorimotor_release",
            "tick": int(tick),
            "witness": witness,
            "lane": lane,
            "motor_trace_id": f"m{self.trace_count:06d}",
            "basis_id": self.basis.identity(),
            "basis_kind": "abstract_op_lane_pressure",
            "lane_pressure": {k: round(float(v), 6) for k, v in lane_pressure.items()},
            "op_pressure": {k: round(float(v), 6) for k, v in op_pressure.items()},
            "dominant_ops": [
                [k, round(float(v), 6)]
                for k, v in sorted(op_pressure.items(), key=lambda kv: kv[1], reverse=True)[:6]
            ],
            "dominant_lanes": [
                [k, round(float(v), 6)]
                for k, v in sorted(lane_pressure.items(), key=lambda kv: kv[1], reverse=True)[:6]
            ],
            "release_pressure": round(
                float(
                    op_pressure.get(self.operations[2], 0.0)
                    + op_pressure.get(self.operations[12], 0.0)
                ),
                6,
            ),
            "gate_pressure": round(float(gate_pressure), 4),
            "release_score": round(float(release_score), 4),
            "hold": round(float(self.lane_hold[lane]), 4),
            "release": round(float(self.lane_release[lane]), 4),
            "inhibit": round(float(self.lane_inhibit[lane]), 4),
            "correct": round(float(self.lane_correct[lane]), 4),
            "intent_segment": segment,
            "intent_segment_len": len(segment),
            "intent_segment_hash": short_hash_text(raw),
            "trace_window_rows": rows,
            "trace_window_len": len(rows),
            "raw_intent_submitted_for_reafference": False,
        }

        self.intent_segment = []
        self.trace_rows = []
        self.lane_hold[lane] *= 0.35
        self.lane_release[lane] *= 0.20
        self.lane_inhibit[lane] *= 0.70
        return packet

    def top_ops(self, limit: int = 5) -> List[List[Any]]:
        return [
            [op, round(float(v), 4)]
            for op, v in sorted(self.op_energy.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        ]

    def top_lanes(self, limit: int = 5) -> List[List[Any]]:
        return [
            [lane, round(float(v), 4)]
            for lane, v in sorted(self.lane_energy.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        ]

    def top_trace(self, limit: int = 4) -> List[Dict[str, Any]]:
        rows = [
            {
                "lane": lane,
                "hold": round(float(self.lane_hold[lane]), 4),
                "release": round(float(self.lane_release[lane]), 4),
                "inhibit": round(float(self.lane_inhibit[lane]), 4),
                "correct": round(float(self.lane_correct[lane]), 4),
                "energy": round(float(self.lane_energy[lane]), 4),
            }
            for lane in self.lanes
        ]
        return sorted(rows, key=lambda r: r["hold"] + r["release"] + r["energy"], reverse=True)[:limit]

    def state_dict(self) -> Dict[str, Any]:
        return {
            "basis_id": self.basis.identity(),
            "lane_energy": {k: round(float(v), 6) for k, v in self.lane_energy.items()},
            "lane_hold": {k: round(float(v), 6) for k, v in self.lane_hold.items()},
            "lane_release": {k: round(float(v), 6) for k, v in self.lane_release.items()},
            "lane_inhibit": {k: round(float(v), 6) for k, v in self.lane_inhibit.items()},
            "lane_correct": {k: round(float(v), 6) for k, v in self.lane_correct.items()},
            "op_energy": {k: round(float(v), 6) for k, v in self.op_energy.items()},
            "last_emit": int(self.last_emit),
            "witness_count": int(self.witness_count),
            "trace_count": int(self.trace_count),
            "intent_segment_len": len(self.intent_segment),
            "trace_window_len": len(self.trace_rows),
        }
