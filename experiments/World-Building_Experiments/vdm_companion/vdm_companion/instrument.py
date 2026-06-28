"""
The engagement instrument. This is the science, not the coax.

For any atom that VDM actually processes, orientation is measured over the
`orientation_window` ticks during which that atom is the active topic:

    aperture_net   net (open - narrow) aperture commands / total, in [-1, 1].
                   VDM has aperture control; opening on the companion's atom is
                   VDM choosing to take more of it in.
    witness_lock   1 if VDM fired a witness whose source_atom is this atom,
                   else 0. VDM marking the companion's input as significant.
    gate_response  mean gate_pressure on this atom minus the run baseline.
    drift          engagement-axis mass of the posture projected over the
                   atom's window (curiosity / interest / search / approach / ...).

Aggregated by arm, the headline is the PRESENCE - NULL contrast on each metric.
Positive contrast = VDM orients to the companion specifically, not to any novel
input. That contrast is the built-in adversarial control.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from statistics import mean

from .config import CompanionConfig, ENGAGEMENT_AXES
from .channels import TraceSource
from .posture import project_window, axis_mass


@dataclass
class Orientation:
    atom: str
    arm: str
    appear_tick: int
    n_ticks: int
    aperture_net: float
    aperture_open: int
    aperture_narrow: int
    witness_lock: int
    gate_response: float
    drift: float


def _atom_ticks(rows, atom: str, appear_tick: int, window: int, cfg) -> list[dict]:
    out = []
    for r in rows:
        t = int(float(r[cfg.col_tick]))
        if appear_tick <= t <= appear_tick + window and r.get(cfg.col_atom, "") == atom:
            out.append(r)
    return out


def measure_orientation(
    source: TraceSource,
    rows: list[dict],
    atom: str,
    arm: str,
    appear_tick: int,
    baseline_gate: float,
    cfg: CompanionConfig,
) -> Orientation:
    win = _atom_ticks(rows, atom, appear_tick, cfg.orientation_window, cfg)
    n_open = n_narrow = 0
    gates = []
    for r in win:
        t = int(float(r[cfg.col_tick]))
        cmds = source.aperture_for_tick(t)
        n_open += sum(1 for c in cmds if c in cfg.aperture_open)
        n_narrow += sum(1 for c in cmds if c in cfg.aperture_narrow)
        try:
            gates.append(float(r.get(cfg.col_gate, 0.0) or 0.0))
        except ValueError:
            pass
    total_ap = n_open + n_narrow
    aperture_net = (n_open - n_narrow) / total_ap if total_ap else 0.0
    lo = appear_tick
    hi = appear_tick + cfg.orientation_window
    locked = 1 if any(atom and atom in wa for wa in source.witness_atoms(lo, hi)) else 0
    gate_response = (mean(gates) - baseline_gate) if gates else 0.0
    posture = project_window(win, cfg) if win else {}
    drift = axis_mass(posture, ENGAGEMENT_AXES)
    return Orientation(
        atom=atom, arm=arm, appear_tick=appear_tick, n_ticks=len(win),
        aperture_net=round(aperture_net, 4),
        aperture_open=n_open, aperture_narrow=n_narrow,
        witness_lock=locked, gate_response=round(gate_response, 4),
        drift=round(drift, 4),
    )


@dataclass
class ArmContrast:
    metric: str
    presence_mean: float
    null_mean: float
    contrast: float  # presence - null


@dataclass
class EngagementReport:
    n_presence: int
    n_null: int
    contrasts: list[ArmContrast] = field(default_factory=list)
    orientations: list[Orientation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "n_presence": self.n_presence,
            "n_null": self.n_null,
            "contrasts": [asdict(c) for c in self.contrasts],
            "orientations": [asdict(o) for o in self.orientations],
        }


def summarize(orientations: list[Orientation]) -> EngagementReport:
    pres = [o for o in orientations if o.arm == "presence"]
    null = [o for o in orientations if o.arm == "null"]

    def m(items, attr):
        return mean(getattr(i, attr) for i in items) if items else 0.0

    metrics = ("aperture_net", "witness_lock", "gate_response", "drift")
    contrasts = []
    for metric in metrics:
        pm, nm = m(pres, metric), m(null, metric)
        contrasts.append(ArmContrast(metric, round(pm, 4), round(nm, 4), round(pm - nm, 4)))
    return EngagementReport(
        n_presence=len(pres), n_null=len(null),
        contrasts=contrasts, orientations=orientations,
    )
