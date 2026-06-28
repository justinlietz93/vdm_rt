from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional


@dataclass(frozen=True)
class Rule:
    family: str
    reply_text: str
    action: str
    aperture_hint: str
    stimulus_policy: str
    reafferent_gain_hint: float


DEFAULT_RULES: Dict[str, Rule] = {
    "attention": Rule("attention", "Hold attention here. Keep the signal narrow and steady.", "hold_attention", "hold_narrow", "repeat_same_point", 0.22),
    "containment": Rule("containment", "Keep it contained. Let the next signal stay small.", "contain", "narrow", "reduce_amplitude", 0.20),
    "restraint": Rule("restraint", "Hold restraint. Do not force the next step.", "restrain", "hold", "slow_down", 0.18),
    "conflict": Rule("conflict", "Reduce force. Keep the boundary stable.", "deescalate", "narrow", "lower_conflict", 0.16),
    "recognition": Rule("recognition", "Preserve continuity. Treat this as familiar.", "preserve_continuity", "hold", "continue_thread", 0.24),
    "comparison": Rule("comparison", "Compare one relation at a time. Keep both sides visible.", "compare", "hold", "present_pair", 0.22),
    "readiness": Rule("readiness", "Advance one small step. Keep the path controlled.", "advance", "open_small", "advance_one_step", 0.24),
    "uncertainty": Rule("uncertainty", "Slow down. Repeat the last shape once.", "stabilize_uncertainty", "narrow", "repeat_last", 0.18),
    "completion": Rule("completion", "Close the loop. Preserve the result.", "close_loop", "hold", "mark_complete", 0.22),
    "novelty": Rule("novelty", "Mark this as new. Explore one edge only.", "explore_lightly", "open_small", "single_edge_probe", 0.20),
    "avoidance": Rule("avoidance", "Withdraw one step. Keep contact light.", "withdraw_lightly", "narrow", "reduce_contact", 0.16),
    "overload": Rule("overload", "Narrow the aperture. Let less through.", "reduce_load", "narrow", "reduce_input", 0.14),
    "unknown": Rule("unknown", "Stay steady. Continue one tick.", "steady", "hold", "continue", 0.18),
}

CANONICAL_FAMILY_ALIASES: Dict[str, str] = {
    "focus": "attention",
    "attention_focus": "attention",
    "attend": "attention",
    "contain": "containment",
    "boundary": "containment",
    "containment_restraint": "containment",
    "restraint_containment": "containment",
    "pressure": "restraint",
    "suppression": "restraint",
    "suppress": "restraint",
    "inhibit": "restraint",
    "fight": "conflict",
    "fighting": "conflict",
    "mismatch": "conflict",
    "tension": "conflict",
    "familiarity": "recognition",
    "faint_recognition": "recognition",
    "recognition_familiarity": "recognition",
    "compare": "comparison",
    "difference": "comparison",
    "relation": "comparison",
    "commitment": "readiness",
    "ready": "readiness",
    "advance": "readiness",
    "question": "uncertainty",
    "uncertain": "uncertainty",
    "doubt": "uncertainty",
    "closure": "completion",
    "complete": "completion",
    "novel": "novelty",
    "new": "novelty",
    "search": "novelty",
    "avoid": "avoidance",
    "withdraw": "avoidance",
    "retreat": "avoidance",
    "overflow": "overload",
    "spillover": "overload",
    "overload": "overload",
}

KEYWORD_TO_FAMILY: List[tuple[str, str]] = [
    ("hold attention", "attention"),
    ("attention", "attention"),
    ("focus", "attention"),
    ("contained", "containment"),
    ("contain", "containment"),
    ("inside the limit", "containment"),
    ("boundary", "containment"),
    ("hold down", "restraint"),
    ("pressure", "restraint"),
    ("suppress", "restraint"),
    ("inhibit", "restraint"),
    ("fighting", "conflict"),
    ("fight", "conflict"),
    ("conflict", "conflict"),
    ("mismatch", "conflict"),
    ("met this before", "recognition"),
    ("familiar", "recognition"),
    ("recognize", "recognition"),
    ("compare", "comparison"),
    ("difference", "comparison"),
    ("between", "comparison"),
    ("accept this path", "readiness"),
    ("commit", "readiness"),
    ("ready", "readiness"),
    ("do i", "uncertainty"),
    ("might", "uncertainty"),
    ("maybe", "uncertainty"),
    ("complete", "completion"),
    ("closed", "completion"),
    ("closure", "completion"),
    ("new", "novelty"),
    ("novel", "novelty"),
    ("search", "novelty"),
    ("avoid", "avoidance"),
    ("withdraw", "avoidance"),
    ("retreat", "avoidance"),
    ("spilling out", "overload"),
    ("spill", "overload"),
    ("too much", "overload"),
]

QUESTION_MARKERS = ("do i", "might", "maybe", "uncertain", "?", "could", "unsure")


def canonical_family(raw: Optional[str], phrase: str = "", axes: Optional[Iterable[str]] = None) -> str:
    """Return a canonical coarse family using explicit family, phrase, then axes."""
    if raw:
        key = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
        if key in DEFAULT_RULES:
            return key
        if key in CANONICAL_FAMILY_ALIASES:
            return CANONICAL_FAMILY_ALIASES[key]
        for part in key.split("/"):
            if part in DEFAULT_RULES:
                return part
            if part in CANONICAL_FAMILY_ALIASES:
                return CANONICAL_FAMILY_ALIASES[part]

    p = (phrase or "").strip().lower()
    for needle, fam in KEYWORD_TO_FAMILY:
        if needle in p:
            return fam

    if axes:
        for axis in axes:
            key = str(axis).strip().lower().replace(" ", "_").replace("-", "_")
            if key in DEFAULT_RULES:
                return key
            if key in CANONICAL_FAMILY_ALIASES:
                return CANONICAL_FAMILY_ALIASES[key]

    return "unknown"


def is_uncertain_phrase(phrase: str, family: str) -> bool:
    p = (phrase or "").lower()
    return family == "uncertainty" or any(marker in p for marker in QUESTION_MARKERS)


def get_rule(family: str, rules: Mapping[str, Rule] = DEFAULT_RULES) -> Rule:
    return rules.get(family, rules["unknown"])
