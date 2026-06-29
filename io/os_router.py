from __future__ import annotations

from typing import Any, Dict, List


class OSRouter:
    """
    Placeholder for future OS command-execution routing.

    This file is intentionally inert in the current runtime. Keyboard, motor,
    audio, and reafference paths do not route through it. It should only become
    active when the model has an explicit command-execution signal and the
    sandbox execution endpoint is implemented.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.enabled = False

    def route(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []
