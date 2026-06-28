"""
The Logic diamond: decide whether VDM is in a posture worth approaching, and if
so which coax family fits.

Receptive = VDM is reaching (curiosity / search / incompletion / closure_gap /
need / uncertainty / approach) and not shut (overload / saturation / withdrawal
/ avoidance / restraint / calm). The contrast, not the raw level, is what gates
emission: a system that is both curious and overloaded should be left alone.

The gate is deliberately conservative. A companion that speaks constantly is
just noise in the afferent field and teaches VDM nothing about choosing to
engage. Silence is the default; emission is earned by posture.
"""
from __future__ import annotations
from dataclasses import dataclass

from .config import CompanionConfig, RECEPTIVE_AXES, SHUT_AXES
from .posture import axis_mass


@dataclass
class Receptivity:
    receptive: bool
    score: float          # receptive_mass - shut_mass
    receptive_mass: float
    shut_mass: float
    dominant_axis: str    # strongest receptive axis, used to pick a coax family


def assess(posture: dict[str, float], cfg: CompanionConfig) -> Receptivity:
    rec = axis_mass(posture, RECEPTIVE_AXES)
    shut = axis_mass(posture, SHUT_AXES)
    score = rec - shut
    dominant = max(
        RECEPTIVE_AXES, key=lambda a: posture.get(a, 0.0), default="curiosity"
    )
    return Receptivity(
        receptive=score >= cfg.receptive_threshold,
        score=round(score, 6),
        receptive_mass=round(rec, 6),
        shut_mass=round(shut, 6),
        dominant_axis=dominant,
    )
