from __future__ import annotations

from typing import Any, Dict, List, Tuple

from vdm_rt.io.actuators.virtual_keyboard.key_matrix import (
    KEY_MATRIX,
    X_CENTERS,
    Y_CENTERS,
    nearest_center_index,
)


class VirtualKeyboardEndpoint:
    """
    Witness surface for keyboard-like actuation.

    It renders exactly the keys implied by the actuator trace. It does not
    complete, normalize, or repair output.
    """

    def __init__(self) -> None:
        self.typed = ""

    def _project_xy(self, x: float, y: float) -> Tuple[int, int, str]:
        col = nearest_center_index(float(x), X_CENTERS)
        row = nearest_center_index(float(y), Y_CENTERS)
        return row, col, KEY_MATRIX[row][col]

    def _press_peaks(self, segment: List[Dict[str, Any]]) -> List[int]:
        if not segment:
            return []
        drives = [float(s.get("drive", 0.0) or 0.0) for s in segment]
        max_drive = max(drives) if drives else 0.0
        if max_drive <= 0.0:
            return []
        threshold = max(0.08, 0.42 * max_drive)
        candidates: List[int] = []
        for i, drive in enumerate(drives):
            left = drives[i - 1] if i > 0 else -1.0
            right = drives[i + 1] if i + 1 < len(drives) else -1.0
            if drive >= threshold and drive >= left and drive >= right:
                candidates.append(i)
        selected: List[int] = []
        for i in sorted(candidates, key=lambda idx: drives[idx], reverse=True):
            if all(abs(i - j) >= 3 for j in selected):
                selected.append(i)
        selected = sorted(selected)[:8]
        if not selected and max_drive >= threshold:
            selected = [int(max(range(len(drives)), key=lambda j: drives[j]))]
        return selected

    def handle(self, packet: Dict[str, Any], spatial_segment: List[Dict[str, Any]]) -> Dict[str, Any]:
        peaks = self._press_peaks(spatial_segment)
        chars: List[str] = []
        presses: List[Dict[str, Any]] = []
        for idx in peaks:
            lo = max(0, idx - 1)
            hi = min(len(spatial_segment), idx + 2)
            window = spatial_segment[lo:hi]
            weights = [max(1e-6, float(s.get("drive", 0.0) or 0.0)) for s in window]
            weight_sum = sum(weights) or 1.0
            x = sum(float(s.get("x", 0.0)) * w for s, w in zip(window, weights)) / weight_sum
            y = sum(float(s.get("y", 0.0)) * w for s, w in zip(window, weights)) / weight_sum
            row, col, char = self._project_xy(x, y)
            chars.append(char)
            presses.append(
                {
                    "peak_index": int(idx),
                    "tick": spatial_segment[idx].get("tick"),
                    "x": round(float(x), 6),
                    "y": round(float(y), 6),
                    "row": int(row),
                    "col": int(col),
                    "char": char,
                    "drive": round(float(spatial_segment[idx].get("drive", 0.0) or 0.0), 6),
                }
            )
        output_text = "".join(chars)
        for char in output_text:
            if char == "\b":
                self.typed = self.typed[:-1]
            else:
                self.typed += char
        return {
            "trace_kind": "keyboard_output_event",
            "payload": {
                "motor_trace_id": packet.get("motor_trace_id", ""),
                "channel_id": "keyboard.symbol_grid",
                "action_kind": "spatial_interval_transduction",
                "output_text": output_text,
                "output_len": len(output_text),
                "press_count": len(presses),
                "presses": presses,
                "typed_tail_logged_only": self.typed[-64:],
                "typed_tail_submitted_to_reafference": False,
            },
        }
