from __future__ import annotations

from typing import Any, Dict, List

from vdm_rt.io.actuators.virtual_keyboard.endpoint import VirtualKeyboardEndpoint


class VirtualKeyboardRoute:
    """Explicit virtual-keyboard endpoint route; not owned by UTD or OSRouter."""

    channel_id = "keyboard.symbol_grid"

    def __init__(
        self,
        *,
        keyboard: VirtualKeyboardEndpoint | None = None,
        ute: Any = None,
        reafference: Any = None,
        sensorimotor_trace: Any = None,
    ) -> None:
        self.keyboard = keyboard or VirtualKeyboardEndpoint()
        self.ute = ute
        self.reafference = reafference
        self.sensorimotor_trace = sensorimotor_trace

    def __call__(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        output_event = self.keyboard.handle(event, list(event.get("spatial_segment") or []))
        self._record("keyboard_output_event", output_event)
        reafferent_events: List[Dict[str, Any]] = []
        if self.reafference is not None:
            reafferent_events = self.reafference.events_from_output(
                output_event,
                tick=int(event.get("tick", 0) or 0),
            )
            for rec in reafferent_events:
                self._push_ute(rec)
        self._record(
            "reafference_pair",
            {
                "tick": int(event.get("tick", 0) or 0),
                "motor_trace_id": str(event.get("motor_trace_id", "")),
                "witness": str(event.get("witness", "")),
                "output_event": output_event,
                "reafference_count": int(len(reafferent_events)),
                "raw_output_content_submitted_to_reafference": bool(reafferent_events),
            },
        )
        return [output_event] + reafferent_events

    def _push_ute(self, record: Dict[str, Any]) -> None:
        push = getattr(self.ute, "push", None)
        if push is None:
            return
        try:
            push(dict(record))
        except Exception:
            return

    def _record(self, trace_kind: str, record: Dict[str, Any]) -> None:
        method = getattr(self.sensorimotor_trace, "record", None)
        if method is None:
            return
        try:
            method(str(trace_kind), dict(record or {}))
        except Exception:
            return
