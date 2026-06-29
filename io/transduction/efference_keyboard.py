from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from vdm_rt.io.transduction.efference_ops import label_selector_trace_row
from vdm_rt.io.transduction.reafferent_index import ReafferentPostureIndex
from vdm_rt.io.actuators.virtual_keyboard.key_matrix import (
    KEY_MATRIX,
    X_CENTERS,
    Y_CENTERS,
    nearest_center_index,
)


LANE_NAMES = tuple(f"LANE_{i:04d}" for i in range(8))


def _hash_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:16]


def _center_of_mass(values: List[float]) -> Optional[float]:
    total = float(sum(values))
    if total <= 0.0:
        return None
    return float(sum(i * float(v) for i, v in enumerate(values)) / total)


def _nearest_index(value: Optional[float], count: int, fallback: int = 0) -> int:
    if value is None:
        return max(0, min(int(count) - 1, int(fallback)))
    try:
        return max(0, min(int(count) - 1, int(round(float(value)))))
    except Exception:
        return max(0, min(int(count) - 1, int(fallback)))


def _spatial_center(segment: List[Dict[str, Any]]) -> tuple[Optional[float], Optional[float]]:
    if not segment:
        return None, None
    weights = [max(0.0, float(row.get("drive", 0.0) or 0.0)) for row in segment]
    total = sum(weights)
    if total <= 0.0:
        return None, None
    x = sum(float(row.get("x", 0.0) or 0.0) * w for row, w in zip(segment, weights)) / total
    y = sum(float(row.get("y", 0.0) or 0.0) * w for row, w in zip(segment, weights)) / total
    return float(x), float(y)


class KeyboardGridTransducer:
    """Translate actuator spatial traces into keyboard grid packets."""

    def __init__(self, posture_index: ReafferentPostureIndex | None = None) -> None:
        self.posture_index = posture_index

    def translate(
        self,
        packet: Dict[str, Any],
        spatial_segment: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        out = dict(packet or {})
        lane_pressure = {
            lane: float((out.get("lane_pressure") or {}).get(lane, 0.0) or 0.0)
            for lane in LANE_NAMES
        }
        row = _center_of_mass([lane_pressure[lane] for lane in LANE_NAMES])
        strongest = str(out.get("lane", "LANE_0000"))
        fallback_row = LANE_NAMES.index(strongest) if strongest in LANE_NAMES else 0
        spatial_segment = list(spatial_segment or [])
        x, y = _spatial_center(spatial_segment)
        row_idx = (
            nearest_center_index(float(y), Y_CENTERS)
            if y is not None
            else _nearest_index(row, len(KEY_MATRIX), fallback=fallback_row % len(KEY_MATRIX))
        )
        col_idx = nearest_center_index(float(x), X_CENTERS) if x is not None else 0

        out.update(
            {
                "channel_id": "keyboard.symbol_grid",
                "actuation_type": "keyboard_grid_press",
                "action_kind": "spatial_press",
                "row": None if y is None else round(float(y), 6),
                "col": None if x is None else round(float(x), 6),
                "key_row": int(row_idx),
                "key_col": int(col_idx),
                "key_char": KEY_MATRIX[row_idx][col_idx],
                "key_code": f"R{row_idx}C{col_idx}",
                "motor_surface": "keyboard_8x8_symbol_grid",
                "spatial_segment": spatial_segment,
                "spatial_segment_len": int(len(spatial_segment)),
                "spatial_segment_hash": _hash_text(str(spatial_segment)),
                "keyboard_output_raw_atom_submitted_for_reafference": True,
            }
        )
        if self.posture_index is not None:
            labeled_rows = [
                label_selector_trace_row(row)
                for row in list(out.get("trace_window_rows") or [])
                if isinstance(row, dict)
            ]
            out["research_projection_2048"] = self.posture_index.project_and_query(
                labeled_rows
            )
            out["translator_submitted_for_reafference"] = False
        return out
