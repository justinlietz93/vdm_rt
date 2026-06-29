from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
from typing import Any, Dict, Iterable, List

from vdm_rt.io.transduction.efference_keyboard import KeyboardGridTransducer
from vdm_rt.io.transduction.reafferent_index import ReafferentPostureIndex


SPATIAL_FEATURES = (
    "keyboard_channel",
    "x_pos",
    "x_neg",
    "y_pos",
    "y_neg",
    "press",
    "hold",
    "release",
    "sustain",
    "separate",
)


def _u64(label: str) -> int:
    return int.from_bytes(
        hashlib.blake2b(str(label).encode("utf-8"), digest_size=8).digest(),
        "little",
        signed=False,
    )


def _group(label: str, n: int, size: int, salt: str) -> List[int]:
    out: List[int] = []
    seen: set[int] = set()
    j = 0
    while len(out) < max(1, int(size)):
        idx = int(_u64(f"{salt}|{label}|{j}") % max(1, int(n)))
        j += 1
        if idx in seen:
            continue
        seen.add(idx)
        out.append(idx)
    return out


class SpatialActuationTrace:
    """Actuator-side spatial trace over fixed external coordinate channels."""

    def __init__(
        self,
        n: int,
        group_size: int = 12,
        salt: str = "keyboard:spatial",
        decay: float = 0.94,
        max_segment: int = 2048,
    ) -> None:
        self.n = int(n)
        self.group_size = int(group_size)
        self.salt = str(salt)
        self.decay = float(decay)
        self.max_segment = int(max(1, max_segment))
        self.groups = {
            name: _group(f"keyboard_spatial:{name}", self.n, self.group_size, self.salt)
            for name in SPATIAL_FEATURES
        }
        self.node_to_features: Dict[int, List[str]] = defaultdict(list)
        for name, nodes in self.groups.items():
            for node in nodes:
                self.node_to_features[int(node)].append(name)
        self.state = {name: 0.0 for name in SPATIAL_FEATURES}
        self.samples_since_witness: List[Dict[str, Any]] = []

    def observe(self, tick: int, nodes: Iterable[int]) -> Dict[str, Any]:
        for key in self.state:
            self.state[key] *= self.decay
        touched: Counter[str] = Counter()
        for raw_node in nodes or []:
            try:
                node = int(raw_node)
            except Exception:
                continue
            for name in self.node_to_features.get(node, []):
                touched[name] += 1
        for name, count in touched.items():
            self.state[name] += float(count)

        xp = self.state["x_pos"]
        xn = self.state["x_neg"]
        yp = self.state["y_pos"]
        yn = self.state["y_neg"]
        x = (xp - xn) / max(1e-9, xp + xn)
        y = (yp - yn) / max(1e-9, yp + yn)
        sample = {
            "tick": int(tick),
            "x": round(float(max(-1.0, min(1.0, x))), 6),
            "y": round(float(max(-1.0, min(1.0, y))), 6),
            "channel": round(float(self.state["keyboard_channel"]), 6),
            "press": round(float(self.state["press"]), 6),
            "hold": round(float(self.state["hold"]), 6),
            "release": round(float(self.state["release"]), 6),
            "sustain": round(float(self.state["sustain"]), 6),
            "separate": round(float(self.state["separate"]), 6),
            "drive": round(
                float(
                    (self.state["press"] + self.state["release"] + 0.35 * self.state["sustain"])
                    * (1.0 + 0.15 * self.state["keyboard_channel"])
                ),
                6,
            ),
            "touched": dict(touched),
        }
        self.samples_since_witness.append(sample)
        if len(self.samples_since_witness) > self.max_segment:
            self.samples_since_witness = self.samples_since_witness[-self.max_segment :]
        return sample

    def consume_segment(self) -> List[Dict[str, Any]]:
        segment = list(self.samples_since_witness)
        self.samples_since_witness = []
        return segment

    def state_dict(self) -> Dict[str, Any]:
        return {"state": {k: round(float(v), 6) for k, v in self.state.items()}}


class KeyboardSensorimotorAdapter:
    """
    IO-owned virtual-keyboard actuator bridge.

    The selector is duck-typed and passed in by the composition root. This
    module does not import or inspect core internals.
    """

    def __init__(
        self,
        selector: Any,
        n: int,
        seed: int = 0,
        spatial_group_size: int = 12,
        spatial_decay: float = 0.94,
        posture_index: ReafferentPostureIndex | None = None,
    ) -> None:
        self.selector = selector
        self.spatial = SpatialActuationTrace(
            n=int(n),
            group_size=int(spatial_group_size),
            salt=f"keyboard:spatial:{int(seed)}",
            decay=float(spatial_decay),
        )
        self.transducer = KeyboardGridTransducer(posture_index=posture_index)

    def observe_nodes(
        self,
        nodes: Iterable[int],
        tick: int,
        metrics: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        node_list = [int(n) for n in nodes or []]
        spatial_sample = self.spatial.observe(int(tick), node_list)
        selector_out = self.selector.observe_nodes(node_list, tick=int(tick), metrics=metrics or {})
        emitted = []
        for packet in selector_out.get("emitted") or []:
            if not isinstance(packet, dict):
                continue
            segment = self.spatial.consume_segment()
            emitted.append(self.transducer.translate(packet, spatial_segment=segment))
        out = dict(selector_out)
        out["spatial_sample"] = spatial_sample
        out["spatial_state"] = self.spatial.state_dict()["state"]
        out["emitted"] = emitted
        return out
