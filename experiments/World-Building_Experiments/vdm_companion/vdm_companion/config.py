"""Companion configuration. All thresholds are tunable against real runs."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence


# Aperture command sets, derived from the real occlusion-probe vocab.
# Opening toward an atom = VDM choosing to take more of it in.
APERTURE_OPEN: frozenset[str] = frozenset(
    {"AP_OPEN_OR_RELAX", "AP_WIDEN", "AP_RELAX", "AP_REOPEN_STEP",
     "AP_LEVEL_TOWARD:whole", "AP_LEVEL_TOWARD:span"}
)
APERTURE_NARROW: frozenset[str] = frozenset(
    {"AP_NARROW", "AP_CLOSE", "AP_CLOSE_CONFIRMED",
     "AP_LEVEL_TOWARD:char", "AP_LEVEL_TOWARD:punct"}
)

# Posture axes that indicate VDM is reaching rather than resting.
# High on these + low on the "shut" axes = receptive to a companion.
RECEPTIVE_AXES: Sequence[str] = (
    "curiosity", "interest", "search", "incompletion", "closure_gap",
    "need", "uncertainty", "approach", "attention", "novelty",
)
SHUT_AXES: Sequence[str] = (
    "overload", "saturation", "withdrawal", "avoidance", "restraint", "calm",
)
# Axes the engagement instrument watches for post-injection drift.
ENGAGEMENT_AXES: Sequence[str] = (
    "curiosity", "interest", "search", "approach", "engagement", "attention",
)


@dataclass
class CompanionConfig:
    # --- receptivity gate ---
    receptive_threshold: float = 0.18
    """Min (receptive_mass - shut_mass) for the Logic gate to open."""
    min_ticks_between_emits: int = 12
    """Refractory period so the companion does not flood the field."""
    require_inter_witness: bool = True
    """Only consider emitting inside a window that has closed at least one
    witness, i.e. VDM has actually been doing something, not idling."""

    # --- coax arms ---
    null_arm_probability: float = 0.5
    """Fraction of emits that are surface-matched inert NULL atoms (control)."""
    presence_topic_echo: bool = True
    """If True, PRESENCE atoms echo VDM's current topic with a closure gap.
    If False, they use a recurring content-light presence motif."""
    presence_open_marker: str = "and then"
    """Trailing dependency on a presence atom. Combined with an unclosed pair it
    forms the closure gap. Default avoids the em-dash; set to '\u2014' if you
    want the dangling-dash form instead."""

    # --- posture projection ---
    tau: float = 10.0
    """Recency decay for the trace-window posture projection (ticks)."""
    use_reaching_overlay: bool = True
    """Merge the additive reaching overlay (curiosity/search/closure_gap/... and
    saturation/overload/calm) onto Justin's conservative base projection."""

    # --- instrument ---
    orientation_window: int = 8
    """Ticks after an injected atom first appears, over which orientation is
    measured (aperture net-open, witness lock, gate response, posture drift)."""

    # --- reproducibility ---
    seed: int = 0

    # Engine-specific column names. Defaults match the shipped runs.
    col_tick: str = "tick"
    col_atom: str = "atom"
    col_gate: str = "gate_pressure"
    col_release: str = "release_score"
    col_witnesses: str = "witnesses"
    aperture_open: frozenset[str] = field(default_factory=lambda: APERTURE_OPEN)
    aperture_narrow: frozenset[str] = field(default_factory=lambda: APERTURE_NARROW)
