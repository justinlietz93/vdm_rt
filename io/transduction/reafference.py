from __future__ import annotations

from typing import Any, Dict, List

from vdm_rt.io.transduction.afference import AfferenceTransducer


def event_to_raw_units(event: Dict[str, Any]) -> str:
    payload = event.get("payload", {}) if isinstance(event, dict) else {}
    if not isinstance(payload, dict):
        return ""
    for key in ("raw_units", "output_units", "output_text", "char"):
        if key in payload:
            value = payload.get(key, "")
            return "" if value is None else str(value)
    return ""


class ReafferenceTransducer:
    """Converts self-generated output witness content into raw receptor events."""

    def __init__(self, afference: AfferenceTransducer, enabled: bool = True) -> None:
        self.afference = afference
        self.enabled = bool(enabled)

    def events_from_output(
        self,
        output_event: Dict[str, Any],
        *,
        tick: int,
    ) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        raw_units = event_to_raw_units(output_event)
        if raw_units == "":
            return []
        payload = output_event.get("payload", {}) if isinstance(output_event, dict) else {}
        motor_trace_id = ""
        if isinstance(payload, dict):
            motor_trace_id = str(payload.get("motor_trace_id", ""))
        return self.afference.text_events(
            raw_units,
            tick=int(tick),
            source="reafference",
            input_kind="self_output_raw",
            motor_trace_id=motor_trace_id,
        )
