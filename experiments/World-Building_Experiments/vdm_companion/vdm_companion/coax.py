"""
The coax library. Two interleaved arms.

PRESENCE
    An under-determined echo of VDM's current topic. Salient because it reuses
    real topic content tokens, but left open with an unclosed pairing and a
    trailing dependency. In VDM's own aperture vocabulary an unclosed pair IS a
    closure gap, so the atom presents as a structure VDM can foot onto but not
    finish. The only way to finish it is to reach further -- toward the source.

NULL  (the control arm)
    Surface-matched to a presence atom: same token count, same punctuation
    skeleton, same length band. Content tokens drawn from a small fixed opaque
    vocabulary so recurrence statistics match. Crucially CLOSED -- no open pair,
    no trailing dependency. By the package-06 result this resolvable structure
    should let VDM foot and fall quiet: little orientation, low activity.

If VDM orients to PRESENCE more than NULL, that contrast is engagement toward
the companion rather than generic novelty chasing.
"""
from __future__ import annotations
import random
import re
import string
from dataclasses import dataclass

from .config import CompanionConfig


_STOP = frozenset(
    "the a an and or but while until when then is are was were be been to of in "
    "on at by it this that these those as so if for with from into over under".split()
)
# Fixed opaque vocabulary -> recurrence statistics stay matched across NULL emits
# while carrying no resolvable content. Consistent set, sampled with replacement.
_OPAQUE = (
    "vren", "task", "morv", "lieth", "quon", "drevi", "sote", "naru",
    "phel", "bint", "corv", "yesa", "trune", "wcode", "haln", "bero",
)
_PUNCT = set(string.punctuation)


def _content_tokens(text: str, k: int = 3) -> list[str]:
    toks = [t.strip(string.punctuation) for t in text.split()]
    toks = [t for t in toks if len(t) >= 3 and t.lower() not in _STOP]
    return toks[:k] if toks else [t for t in text.split() if t][:k]


def _punct_skeleton(text: str) -> str:
    return "".join(c if c in _PUNCT else " " if c.isspace() else "x" for c in text)


@dataclass
class CoaxAtom:
    text: str
    arm: str           # "presence" | "null"
    family: str        # dominant receptive axis that triggered the emit
    source_topic: str  # VDM's atom at emit time (null arm: the presence it mirrors)


class CoaxLibrary:
    def __init__(self, cfg: CompanionConfig):
        self.cfg = cfg
        self._rng = random.Random(cfg.seed)
        self._presence_count = 0

    # --- PRESENCE ---------------------------------------------------------
    def presence(self, topic: str, family: str) -> CoaxAtom:
        if self.cfg.presence_topic_echo and topic.strip():
            toks = _content_tokens(topic, k=self._rng.choice((2, 3)))
            core = " ".join(toks) if toks else "here"
        else:
            # content-light recurring motif: partially predictable, never closed
            core = "here"
        # open an unclosed pair and leave a trailing dependency -> closure gap
        self._presence_count += 1
        marker = self.cfg.presence_open_marker
        text = f"( {core} {marker}".rstrip()
        return CoaxAtom(text=text, arm="presence", family=family, source_topic=topic)

    # --- NULL (matched control) ------------------------------------------
    def null_match(self, presence: CoaxAtom) -> CoaxAtom:
        """Build a closed, inert atom matched to `presence` on token count,
        punctuation skeleton, and length band, using opaque vocab."""
        toks = [t for t in re.split(r"\s+", presence.text) if t and t not in "()\u2014"]
        ntok = max(1, len(toks))
        words = [self._rng.choice(_OPAQUE) for _ in range(ntok)]
        # closed: a balanced pair, no trailing dependency
        text = "( " + " ".join(words) + " )"
        # length-band match: pad/trim to within +-3 chars of the presence atom
        target = len(presence.text)
        while len(text) < target - 3:
            text = text[:-2] + self._rng.choice(_OPAQUE)[:2] + " )"
        return CoaxAtom(
            text=text, arm="null", family=presence.family,
            source_topic=presence.source_topic,
        )

    # --- arm selection ----------------------------------------------------
    def next_atom(self, topic: str, family: str) -> CoaxAtom:
        presence = self.presence(topic, family)
        if self._rng.random() < self.cfg.null_arm_probability:
            return self.null_match(presence)
        return presence
