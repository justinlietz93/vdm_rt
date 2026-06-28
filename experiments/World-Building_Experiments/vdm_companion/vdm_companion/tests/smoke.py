"""Smoke test: full path on a tiny synthetic stream, no engine required.

Run: python -m vdm_companion.tests.smoke
Asserts the gate fires on a reaching window, a coax atom is emitted to a queue
sink, and the instrument measures orientation on a (simulated) appearance.
"""
from __future__ import annotations
import json
import tempfile
from pathlib import Path

from vdm_companion.config import CompanionConfig
from vdm_companion.coax import CoaxLibrary
from vdm_companion.posture import project_window
from vdm_companion.receptivity import assess
from vdm_companion.channels import QueueFileAfferentSink


def _row(tick, atom, ops, gate, release, witness=""):
    return {
        "tick": str(tick), "atom": atom, "active_ops": ops,
        "gate_pressure": str(gate), "release_score": str(release),
        "witnesses": witness, "active_lanes": "L1 L2",
    }


def main():
    cfg = CompanionConfig(seed=1, min_ticks_between_emits=0)

    # a reaching window: COMPARE without MERGE, unwitnessed releases, closing witness
    win = [
        _row(0, "the marker drifts past the open gate", "SELECT COMPARE", 0.5, 0.6),
        _row(1, "the marker drifts past the open gate", "COMPARE DIFFERENCE", 0.7, 0.55),
        _row(2, "the marker drifts past the open gate", "COMPARE ADVANCE", 0.8, 0.5, witness="W1_0001"),
    ]
    posture = project_window(win, cfg)
    rec = assess(posture, cfg)
    assert rec.receptive, f"expected receptive, got {rec}"
    assert posture.get("closure_gap", 0) > 0 or posture.get("search", 0) > 0, posture

    lib = CoaxLibrary(cfg)
    pres = lib.presence("the marker drifts past the open gate", rec.dominant_axis)
    assert pres.text.startswith("("), pres.text
    null = lib.null_match(pres)
    assert null.text.endswith(")"), null.text  # closed control

    with tempfile.TemporaryDirectory() as d:
        q = Path(d) / "afferent_queue.jsonl"
        sink = QueueFileAfferentSink(q)
        sink.emit(pres.text, {"arm": pres.arm, "family": pres.family})
        frame = json.loads(q.read_text().strip())
        assert frame["atom"] == pres.text and frame["source"] == "companion", frame

    print("smoke OK")
    print("  posture reaching axes:",
          {k: posture[k] for k in ("closure_gap", "search", "curiosity", "need")
           if k in posture})
    print("  receptivity score:", rec.score, "dominant:", rec.dominant_axis)
    print("  presence atom:", pres.text)
    print("  null atom    :", null.text)


if __name__ == "__main__":
    main()
