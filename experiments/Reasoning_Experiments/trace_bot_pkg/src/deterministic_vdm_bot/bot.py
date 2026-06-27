from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .rules import DEFAULT_RULES, Rule, canonical_family, get_rule, is_uncertain_phrase


PHRASE_FIELDS = (
    "phrase",
    "true_top1_phrase",
    "fused_phrase",
    "selector_phrase",
    "aperture_phrase",
    "translation",
    "top1_phrase",
)

FAMILY_FIELDS = (
    "family",
    "true_top1_family",
    "fused_family",
    "selector_family",
    "aperture_family",
    "top1_family",
)

LEAF_FIELDS = (
    "leaf",
    "true_top1_leaf",
    "fused_leaf",
    "selector_leaf",
    "aperture_leaf",
    "top1_leaf",
)

AXES_FIELDS = (
    "dominant_axes",
    "true_dominant_axes",
    "axes",
)


@dataclass
class BotState:
    turn_count: int = 0
    last_family: str = ""
    family_streak: int = 0
    last_rule_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BotPacket:
    tick: Optional[int]
    input_phrase: str
    input_family: str
    input_leaf: str
    reply_text: str
    action: str
    aperture_hint: str
    stimulus_policy: str
    reafferent_gain_hint: float
    state_family: str
    state_streak: int
    is_uncertain: bool
    rule_id: str
    prefix: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def _first_present(record: Mapping[str, Any], fields: Iterable[str], default: str = "") -> str:
    for field in fields:
        val = record.get(field)
        if val is None:
            continue
        s = str(val).strip()
        if s:
            return s
    return default


def _parse_axes(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, tuple):
        return [str(x) for x in value]
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        if s.startswith("["):
            try:
                obj = json.loads(s)
                if isinstance(obj, list):
                    return [str(x) for x in obj]
            except Exception:
                pass
        return [x.strip() for x in s.replace(";", ",").split(",") if x.strip()]
    return [str(value)]


def _first_axes(record: Mapping[str, Any]) -> List[str]:
    for field in AXES_FIELDS:
        if field in record:
            axes = _parse_axes(record.get(field))
            if axes:
                return axes
    return []


def _tick(record: Mapping[str, Any]) -> Optional[int]:
    val = record.get("tick")
    if val is None:
        val = record.get("t")
    try:
        return int(val) if val is not None and str(val).strip() != "" else None
    except Exception:
        return None


class DeterministicConversationBot:
    """Fixed-rule social/reafferent surface for VDM posture translations."""

    def __init__(self, rules: Optional[Mapping[str, Rule]] = None) -> None:
        self.rules: Mapping[str, Rule] = rules if rules is not None else DEFAULT_RULES
        self.state = BotState()

    def reset(self) -> None:
        self.state = BotState()

    def normalize(self, record: Mapping[str, Any]) -> Dict[str, Any]:
        phrase = _first_present(record, PHRASE_FIELDS)
        raw_family = _first_present(record, FAMILY_FIELDS)
        leaf = _first_present(record, LEAF_FIELDS)
        axes = _first_axes(record)
        family = canonical_family(raw_family, phrase=phrase, axes=axes)
        return {
            "tick": _tick(record),
            "phrase": phrase,
            "family": family,
            "leaf": leaf,
            "axes": axes,
        }

    def step(self, record: Mapping[str, Any]) -> BotPacket:
        norm = self.normalize(record)
        phrase = norm["phrase"]
        family = norm["family"]
        leaf = norm["leaf"]
        tick = norm["tick"]
        uncertain = is_uncertain_phrase(phrase, family)

        if family == self.state.last_family:
            streak = self.state.family_streak + 1
        else:
            streak = 1

        self.state.turn_count += 1
        self.state.last_family = family
        self.state.family_streak = streak

        effective_family = "uncertainty" if uncertain and family not in ("conflict", "overload") else family
        rule = get_rule(effective_family, self.rules)
        rule_id = f"{rule.family}:{rule.action}"
        self.state.last_rule_id = rule_id

        prefix = ""
        if streak >= 4:
            prefix = "Stable pattern. "
        elif self.state.turn_count > 1 and streak == 1:
            prefix = "Shift detected. "
        elif uncertain and rule.family != "uncertainty":
            prefix = "Uncertain posture. "

        reply_text = prefix + rule.reply_text

        return BotPacket(
            tick=tick,
            input_phrase=phrase,
            input_family=family,
            input_leaf=leaf,
            reply_text=reply_text,
            action=rule.action,
            aperture_hint=rule.aperture_hint,
            stimulus_policy=rule.stimulus_policy,
            reafferent_gain_hint=float(rule.reafferent_gain_hint),
            state_family=family,
            state_streak=streak,
            is_uncertain=uncertain,
            rule_id=rule_id,
            prefix=prefix,
        )

    def neutral_packet(self, tick: Optional[int] = None, reason: str = "lag_warmup") -> BotPacket:
        rule = get_rule("unknown", self.rules)
        return BotPacket(
            tick=tick,
            input_phrase="",
            input_family="unknown",
            input_leaf="",
            reply_text="Stay steady. Continue one tick.",
            action=f"steady:{reason}",
            aperture_hint=rule.aperture_hint,
            stimulus_policy=rule.stimulus_policy,
            reafferent_gain_hint=float(rule.reafferent_gain_hint),
            state_family="unknown",
            state_streak=0,
            is_uncertain=False,
            rule_id="unknown:steady",
            prefix="",
        )
