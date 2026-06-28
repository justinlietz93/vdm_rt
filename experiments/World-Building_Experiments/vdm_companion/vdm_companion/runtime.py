"""
The companion runtime loop.

Cadence is per witness: each time VDM closes a witness, the window since the
previous witness is projected to a posture, the Logic gate assesses receptivity,
and -- if receptive and the refractory period has passed -- one coax atom is
pushed to the afferent sink. The diagram's "actuation intent between witness
events" is exactly this inter-witness window.

In closed-loop mode (live engine), the runtime watches for its own injected
atoms to appear as VDM's active topic and measures orientation over the
following window. That stream of orientations, split by arm, is the engagement
evidence.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from statistics import mean
from typing import Optional, Callable

from .config import CompanionConfig
from .channels import TraceSource, AfferentSink
from .coax import CoaxLibrary, CoaxAtom
from .posture import project_window
from .receptivity import assess, Receptivity
from .instrument import measure_orientation, summarize, Orientation, EngagementReport


@dataclass
class Decision:
    witness_tick: int
    topic: str
    posture_score: float
    receptive_mass: float
    shut_mass: float
    receptive: bool
    emitted: bool
    arm: Optional[str] = None
    atom: Optional[str] = None
    dominant_axis: Optional[str] = None


@dataclass
class _Pending:
    atom: str
    arm: str
    emit_tick: int
    appear_tick: Optional[int] = None
    measured: bool = False


@dataclass
class RunResult:
    decisions: list[Decision] = field(default_factory=list)
    report: Optional[EngagementReport] = None

    def to_dict(self) -> dict:
        return {
            "decisions": [asdict(d) for d in self.decisions],
            "report": self.report.to_dict() if self.report else None,
        }


class CompanionRuntime:
    def __init__(
        self,
        source: TraceSource,
        sink: Optional[AfferentSink],
        cfg: CompanionConfig,
        closed_loop: bool = True,
        on_emit: Optional[Callable[[CoaxAtom, int], None]] = None,
    ):
        self.source = source
        self.sink = sink
        self.cfg = cfg
        self.closed_loop = closed_loop
        self.coax = CoaxLibrary(cfg)
        self.on_emit = on_emit

    def _baseline_gate(self, rows: list[dict]) -> float:
        vals = []
        for r in rows:
            try:
                vals.append(float(r.get(self.cfg.col_gate, 0.0) or 0.0))
            except ValueError:
                pass
        return mean(vals) if vals else 0.0

    def run(self, max_ticks: Optional[int] = None) -> RunResult:
        cfg = self.cfg
        decisions: list[Decision] = []
        pending: list[_Pending] = []
        orientations: list[Orientation] = []
        window: list[dict] = []
        all_rows: list[dict] = []
        last_emit_tick = -10**9

        for row in self.source.ticks():
            tick = int(float(row[cfg.col_tick]))
            all_rows.append(row)
            window.append(row)

            # closed loop: detect appearance of our injected atoms + measure
            if self.closed_loop and pending:
                topic_now = row.get(cfg.col_atom, "")
                for p in pending:
                    if p.appear_tick is None and tick > p.emit_tick and topic_now == p.atom:
                        p.appear_tick = tick
                for p in pending:
                    if (p.appear_tick is not None and not p.measured
                            and tick >= p.appear_tick + cfg.orientation_window):
                        o = measure_orientation(
                            self.source, all_rows, p.atom, p.arm, p.appear_tick,
                            self._baseline_gate(all_rows), cfg,
                        )
                        orientations.append(o)
                        p.measured = True
                pending = [p for p in pending if not p.measured]

            # witness boundary => decision point
            wit = str(row.get(cfg.col_witnesses, "") or "").strip()
            is_witness = bool(wit) and wit.lower() not in ("[]", "none")
            if is_witness:
                posture = project_window(window, cfg)
                rec: Receptivity = assess(posture, cfg)
                topic = row.get(cfg.col_atom, "")
                refractory_ok = (tick - last_emit_tick) >= cfg.min_ticks_between_emits
                do_emit = rec.receptive and refractory_ok
                d = Decision(
                    witness_tick=tick, topic=topic,
                    posture_score=rec.score, receptive_mass=rec.receptive_mass,
                    shut_mass=rec.shut_mass, receptive=rec.receptive,
                    emitted=do_emit, dominant_axis=rec.dominant_axis,
                )
                if do_emit:
                    atom = self.coax.next_atom(topic, rec.dominant_axis)
                    if self.sink is not None:
                        self.sink.emit(atom.text, {
                            "arm": atom.arm, "family": atom.family,
                            "reply_to_topic": atom.source_topic, "at_tick": tick,
                        })
                    if self.on_emit:
                        self.on_emit(atom, tick)
                    pending.append(_Pending(atom.text, atom.arm, tick))
                    last_emit_tick = tick
                    d.arm, d.atom = atom.arm, atom.text
                decisions.append(d)
                window = []

            if max_ticks is not None and tick >= max_ticks:
                break

        report = summarize(orientations) if orientations else None
        return RunResult(decisions=decisions, report=report)
