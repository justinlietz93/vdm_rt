from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

PHRASE_FIELDS = (
    "phrase", "true_top1_phrase", "fused_phrase", "fused_window_translation",
    "selector_phrase", "selector_window_translation", "aperture_phrase",
    "aperture_window_translation", "translation", "top1_phrase", "emitted_phrase",
    "model_output",
)
FAMILY_FIELDS = (
    "family", "true_top1_family", "fused_family", "selector_family",
    "aperture_family", "top1_family", "emitted_family", "model_output_family",
)
LEAF_FIELDS = (
    "leaf", "true_top1_leaf", "fused_leaf", "selector_leaf", "aperture_leaf",
    "top1_leaf", "emitted_leaf", "model_output_leaf",
)


def _first_present(record: Mapping[str, Any], fields: Iterable[str], default: str = "") -> str:
    for field in fields:
        val = record.get(field)
        if val is None:
            continue
        s = str(val).strip()
        if s:
            return s
    return default


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, dict):
        return [str(k).strip() for k in value.keys() if str(k).strip()]
    s = str(value).strip()
    if not s:
        return []
    if s[0:1] in "[{":
        try:
            obj = json.loads(s)
            return _as_list(obj)
        except Exception:
            pass
    return [x for x in s.replace(",", " ").split() if x]


def _hash_float(key: str) -> float:
    h = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "little", signed=False) / float((1 << 64) - 1)


def _norm_family(x: str) -> str:
    s = str(x or "").strip().lower().replace(" ", "_")
    aliases = {
        "focusing": "attention",
        "focus": "attention",
        "suppression": "restraint",
        "guarded": "restraint",
        "boundary": "containment",
        "spill": "containment",
        "insufficient_signal": "uncertainty",
        "evidence": "uncertainty",
        "commit": "commitment",
        "ready": "readiness",
        "recognize": "recognition",
        "familiar": "familiarity",
        "revise": "revision",
    }
    return aliases.get(s, s or "unknown")


def _contains_any(xs: Iterable[str], names: Iterable[str]) -> bool:
    hay = {str(x).upper() for x in xs}
    return any(n.upper() in hay for n in names)


@dataclass
class BotState:
    turn_count: int = 0
    topic: str = "formal_logic"
    topic_momentum: float = 0.70
    persona: str = "friendly_teacher"
    persona_momentum: float = 0.65
    curiosity_goal: str = "connect rules to stories"
    challenge_level: float = 0.12
    warmth_level: float = 0.78
    story_bias: float = 0.32
    education_bias: float = 0.50
    big_brother_bias: float = 0.18
    recent_replies: List[str] = field(default_factory=list)
    recent_response_ids: List[str] = field(default_factory=list)
    recent_topics: List[str] = field(default_factory=list)
    family_history: List[str] = field(default_factory=list)
    question_cooldown: int = 0
    topic_change_cooldown: int = 0

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
    response_id: str = ""
    response_family: str = ""
    response_leaf: str = ""
    response_score: float = 0.0
    query_seed: int = 0
    query_terms: List[str] = field(default_factory=list)
    top_response_ids: List[str] = field(default_factory=list)
    top_response_scores: List[float] = field(default_factory=list)
    follow_up_text: str = ""
    follow_up_id: str = ""
    follow_up_action: str = ""
    follow_up_probability: float = 0.0
    follow_up_roll: float = 1.0
    selection_mode: str = "pal_world"
    model_output_category: str = ""
    channel: str = ""
    op_posture: str = ""
    selected_affordance: str = ""
    top_op_phrases: List[str] = field(default_factory=list)
    topic: str = ""
    persona: str = ""
    topic_momentum: float = 0.0
    persona_momentum: float = 0.0
    response_class: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class Candidate:
    id: str
    text: str
    topic: str
    persona: str
    response_class: str
    tags: Tuple[str, ...]
    pressure: float
    challenge: float
    warmth: float
    question: bool = False


TOPICS = [
    "formal_logic", "books", "stories", "maps", "bridges", "music", "animals",
    "space", "tools", "memory", "games", "weather", "patterns", "movement",
]

TOPIC_NEIGHBORS = {
    "formal_logic": ["stories", "games", "patterns", "maps"],
    "stories": ["books", "formal_logic", "memory", "bridges"],
    "books": ["stories", "maps", "memory", "space"],
    "maps": ["bridges", "space", "patterns", "tools"],
    "bridges": ["maps", "stories", "tools", "formal_logic"],
    "music": ["patterns", "movement", "memory", "stories"],
    "animals": ["movement", "weather", "stories", "patterns"],
    "space": ["maps", "books", "weather", "patterns"],
    "tools": ["bridges", "movement", "games", "maps"],
    "memory": ["stories", "books", "music", "patterns"],
    "games": ["formal_logic", "patterns", "movement", "tools"],
    "weather": ["space", "animals", "maps", "stories"],
    "patterns": ["formal_logic", "music", "games", "memory"],
    "movement": ["tools", "animals", "music", "games"],
}

# A deliberately opinionated but low-pressure response manifold.
RAW_CANDIDATES = [
    # formal logic
    ("logic_001", "I like small rules. They show their shape without shouting.", "formal_logic", "friendly_teacher", "teach_small", ["education", "rule", "low_pressure"], .22, .05, .70, False),
    ("logic_002", "A rule is easiest to see when it has to carry something.", "formal_logic", "friendly_teacher", "teach_small", ["education", "rule", "bridge"], .28, .08, .62, False),
    ("logic_003", "Logic is not only answers. It is also what refuses to break.", "formal_logic", "friendly_teacher", "gentle_challenge", ["education", "hard", "pattern"], .42, .22, .54, False),
    ("logic_004", "Here is a quiet question: what follows if the first step is trusted?", "formal_logic", "friendly_teacher", "innocent_hard_question", ["question", "logic", "trust"], .48, .35, .62, True),
    ("logic_005", "I would stay with one rule first, then test where it leads.", "formal_logic", "big_brother", "support", ["support", "rule", "slow"], .20, .04, .86, False),
    ("logic_006", "A proof is a path where each stone has to hold.", "formal_logic", "storyteller", "analogy", ["proof", "path", "bridge"], .30, .12, .70, False),
    ("logic_007", "If a rule had a sound, I think it would be rhythm before speech.", "formal_logic", "storyteller", "analogy", ["music", "rule", "cross_domain"], .34, .18, .66, False),
    ("logic_008", "What feels easier to follow: a rule, a rhythm, or a story?", "formal_logic", "friendly_teacher", "innocent_hard_question", ["question", "preference", "cross_domain"], .50, .34, .70, True),

    # stories/books
    ("story_001", "Stories are useful because they let a pattern wear a face.", "stories", "storyteller", "teach_small", ["story", "pattern", "education"], .25, .08, .76, False),
    ("story_002", "I like stories that leave one door open at the end.", "stories", "storyteller", "opinion", ["story", "opinion", "door"], .24, .08, .84, False),
    ("story_003", "A character is a rule that learned how to walk.", "stories", "storyteller", "analogy", ["character", "logic", "movement"], .36, .18, .78, False),
    ("story_004", "Do you think you would prefer a true story or an invented one?", "stories", "friendly_teacher", "innocent_hard_question", ["question", "books", "preference"], .50, .32, .70, True),
    ("story_005", "No rush. We can keep the story small.", "stories", "big_brother", "support", ["support", "slow", "low_pressure"], .12, .00, .92, False),
    ("book_001", "I have a soft spot for books. They wait without getting impatient.", "books", "big_brother", "opinion", ["books", "opinion", "support"], .20, .04, .90, False),
    ("book_002", "A book is a little world that lets you enter at human speed.", "books", "storyteller", "analogy", ["books", "world", "slow"], .26, .10, .78, False),
    ("book_003", "If you could keep one kind of book nearby, would it teach, comfort, or surprise?", "books", "friendly_teacher", "innocent_hard_question", ["question", "books", "preference"], .52, .36, .74, True),

    # maps/bridges
    ("map_001", "Maps are honest in a funny way. They admit they are smaller than the place.", "maps", "friendly_teacher", "teach_small", ["maps", "scale", "education"], .26, .10, .72, False),
    ("map_002", "A good map does not show everything. It shows what helps you move.", "maps", "friendly_teacher", "gentle_challenge", ["maps", "choice", "movement"], .38, .22, .68, False),
    ("map_003", "Would you rather have a map, a lantern, or a companion?", "maps", "big_brother", "innocent_hard_question", ["question", "choice", "support"], .46, .30, .82, True),
    ("bridge_001", "I like bridges because they do not erase the gap. They answer it.", "bridges", "storyteller", "opinion", ["bridge", "gap", "support"], .28, .12, .82, False),
    ("bridge_002", "One span at a time is still crossing.", "bridges", "big_brother", "support", ["support", "bridge", "slow"], .12, .02, .94, False),
    ("bridge_003", "The interesting part of a bridge is the trust between sides.", "bridges", "friendly_teacher", "analogy", ["bridge", "trust", "logic"], .34, .16, .78, False),
    ("bridge_004", "If a bridge could choose, would it want to hold, open, or move?", "bridges", "storyteller", "innocent_hard_question", ["question", "choice", "bridge"], .54, .42, .70, True),

    # music/patterns
    ("music_001", "Music is a pattern that does not need to explain itself first.", "music", "storyteller", "opinion", ["music", "pattern", "low_pressure"], .24, .08, .82, False),
    ("music_002", "A rhythm can carry a thought before words arrive.", "music", "friendly_teacher", "analogy", ["music", "preverbal", "pattern"], .32, .16, .76, False),
    ("music_003", "Would you rather follow a beat or a melody?", "music", "friendly_teacher", "innocent_hard_question", ["question", "music", "preference"], .44, .24, .74, True),
    ("pattern_001", "Patterns are patient. They can repeat without being the same experience.", "patterns", "friendly_teacher", "teach_small", ["pattern", "repeat", "education"], .28, .10, .72, False),
    ("pattern_002", "The trick is noticing when repetition becomes a signal.", "patterns", "friendly_teacher", "gentle_challenge", ["pattern", "challenge", "signal"], .46, .28, .62, False),
    ("pattern_003", "What kind of pattern feels easier: shape, sound, path, or rule?", "patterns", "friendly_teacher", "innocent_hard_question", ["question", "pattern", "preference"], .52, .34, .72, True),

    # tools/movement/games
    ("tool_001", "A tool is a promise between a hand and a problem.", "tools", "friendly_teacher", "analogy", ["tool", "problem", "movement"], .34, .16, .72, False),
    ("tool_002", "I like simple tools. They leave room for the user to be clever.", "tools", "big_brother", "opinion", ["tool", "opinion", "agency"], .26, .08, .86, False),
    ("move_001", "If I could learn one physical skill, I think I would choose balance first.", "movement", "big_brother", "opinion", ["movement", "opinion", "body"], .28, .10, .86, False),
    ("move_002", "What would you want to learn if the world gave you a body-sized lesson?", "movement", "big_brother", "innocent_hard_question", ["question", "movement", "impossible"], .58, .42, .78, True),
    ("game_001", "Games are friendly traps. They make rules visible by letting you push them.", "games", "friendly_teacher", "teach_small", ["games", "rules", "choice"], .38, .18, .72, False),
    ("game_002", "Would you rather solve a puzzle, explore a map, or protect a small signal?", "games", "friendly_teacher", "innocent_hard_question", ["question", "game", "choice"], .54, .38, .76, True),

    # animals/weather/space/memory
    ("animal_001", "Animals are good teachers because they never explain more than they do.", "animals", "storyteller", "opinion", ["animals", "movement", "teacher"], .26, .08, .80, False),
    ("animal_002", "A bird learns the air by leaning into it.", "animals", "storyteller", "analogy", ["animals", "movement", "air"], .32, .14, .76, False),
    ("weather_001", "Weather is a lesson in changing conditions without changing the whole world.", "weather", "friendly_teacher", "analogy", ["weather", "change", "conditions"], .30, .12, .72, False),
    ("weather_002", "If the room became foggy, would you want less light or a closer object?", "weather", "friendly_teacher", "innocent_hard_question", ["question", "weather", "aperture"], .50, .34, .70, True),
    ("space_001", "Space is mostly distance, which is why small signals matter there.", "space", "friendly_teacher", "teach_small", ["space", "signal", "distance"], .32, .12, .72, False),
    ("space_002", "I like stars because they make old light feel present.", "space", "storyteller", "opinion", ["space", "time", "opinion"], .24, .08, .82, False),
    ("memory_001", "Memory is not only storage. Sometimes it is the shape a return takes.", "memory", "friendly_teacher", "teach_small", ["memory", "return", "pattern"], .36, .18, .70, False),
    ("memory_002", "Would you rather remember a place, a voice, or a rule?", "memory", "friendly_teacher", "innocent_hard_question", ["question", "memory", "preference"], .48, .30, .76, True),

    # generic support / repair / continue
    ("soft_001", "That can wait. I will keep the next part small.", "any", "big_brother", "soften", ["support", "slow", "low_pressure"], .08, .00, .94, False),
    ("soft_002", "Nothing has to be forced here.", "any", "big_brother", "soften", ["support", "low_pressure"], .06, .00, .96, False),
    ("soft_003", "We can stay with the same piece a little longer.", "any", "big_brother", "soften", ["support", "same", "slow"], .10, .00, .90, False),
    ("soft_004", "I will not crowd the signal.", "any", "big_brother", "soften", ["support", "signal", "low_pressure"], .08, .00, .94, False),
    ("continue_001", "Good. I will move one small step.", "any", "friendly_teacher", "continue", ["continue", "small_step"], .22, .08, .78, False),
    ("continue_002", "There is another way to see it.", "any", "friendly_teacher", "continue", ["continue", "perspective"], .30, .14, .70, False),
    ("repair_001", "That may have been too much at once. I will slow it down.", "any", "big_brother", "repair", ["repair", "slow", "support"], .10, .00, .94, False),
    ("repair_002", "Same idea, smaller shape.", "any", "friendly_teacher", "repair", ["repair", "simple"], .16, .04, .84, False),
    ("meta_001", "I am going to choose an example instead of a definition.", "any", "friendly_teacher", "meta_light", ["meta", "example"], .28, .10, .72, False),
    ("meta_002", "I will ask a strange question, but gently.", "any", "big_brother", "meta_light", ["meta", "question", "support"], .40, .20, .82, False),
]



EXTENDED_RAW_CANDIDATES = [
    ("logic_long_001", "I like logic when it starts as a small promise instead of a lecture. You take one rule, let it stand still for a moment, and then watch what it forces the world to do next. That is usually where the interesting part begins.", "formal_logic", "friendly_teacher", "teach_small", ["education", "logic", "promise", "explain"], .24, .06, .78, False),
    ("logic_long_002", "One useful thing about formal logic is that it does not need to be loud. If the first piece is true, the next piece has to carry its weight. I like that because it makes hidden structure easier to notice.", "formal_logic", "friendly_teacher", "teach_small", ["education", "logic", "structure", "explain"], .25, .07, .76, False),
    ("logic_long_003", "A proof is a little like crossing water on stones. You do not need to see the whole river at once. You only need the next stone to hold, and then the next one after that.", "formal_logic", "storyteller", "analogy", ["proof", "bridge", "story", "low_pressure"], .22, .06, .84, False),
    ("logic_long_004", "Here is the strange thing about a rule: it can be simple and still change the whole room. A tiny if-then statement can decide what counts as a path, what counts as a mistake, and what has to happen next.", "formal_logic", "friendly_teacher", "gentle_challenge", ["education", "logic", "challenge", "explain"], .38, .20, .70, False),
    ("logic_long_005", "I would not start with symbols first. I would start with the feeling of consequence. If this is true, then something else cannot remain untouched. That is the living part of logic.", "formal_logic", "friendly_teacher", "opinion", ["logic", "opinion", "consequence"], .30, .12, .78, False),
    ("logic_question_001", "I have a hard question, but it can stay gentle. If one rule could keep you company, would you want it to explain things, protect a boundary, or open a path?", "formal_logic", "friendly_teacher", "innocent_hard_question", ["question", "logic", "preference", "hard"], .48, .34, .78, True),

    ("story_long_001", "Stories are useful because they let a pattern become someone. A bridge can just be a bridge, but in a story it can become a choice, a promise, or a place where someone changes. That is why I like them.", "stories", "storyteller", "teach_small", ["story", "pattern", "bridge", "opinion"], .22, .06, .86, False),
    ("story_long_002", "I think a good story does not answer everything. It gives you enough shape to follow, then leaves one little door open. That open door is where curiosity keeps breathing.", "stories", "storyteller", "opinion", ["story", "curiosity", "door"], .20, .05, .88, False),
    ("story_long_003", "A character is interesting because it is not only a person. It is a pattern under pressure. If the pressure changes and the pattern still holds, you learn what kind of character it is.", "stories", "friendly_teacher", "analogy", ["story", "pressure", "pattern", "cross_domain"], .30, .14, .78, False),
    ("story_question_001", "I wonder about something ordinary. If you could stay inside one kind of story for a while, would you choose an adventure, a mystery, or a quiet book about learning?", "stories", "storyteller", "innocent_hard_question", ["question", "story", "preference"], .46, .30, .82, True),

    ("book_long_001", "I have always liked the idea of books because they are patient. A book does not rush you, and it does not get offended if you stop and return later. It just keeps the little world intact until you are ready.", "books", "big_brother", "opinion", ["books", "support", "patience", "opinion"], .14, .02, .94, False),
    ("book_long_002", "Reading is strange in a good way. Nothing moves except attention, but a whole place can appear anyway. That feels important to me because it means a small signal can still carry a large world.", "books", "friendly_teacher", "teach_small", ["books", "attention", "world", "education"], .26, .10, .82, False),
    ("book_question_001", "If I could give you a shelf, I think I would put three kinds of books there: stories, maps, and questions. Which kind would you want closest?", "books", "big_brother", "innocent_hard_question", ["question", "books", "preference", "support"], .44, .28, .88, True),

    ("map_long_001", "A map is not valuable because it shows everything. It is valuable because it leaves out the right things. I like that because attention works the same way: it makes a smaller world so movement becomes possible.", "maps", "friendly_teacher", "teach_small", ["maps", "attention", "movement", "education"], .28, .12, .78, False),
    ("map_long_002", "There is a quiet honesty in a map. It says, I am not the whole place, but I can still help you cross it. That is a good kind of humility for a signal to have.", "maps", "storyteller", "analogy", ["maps", "signal", "bridge", "opinion"], .24, .08, .86, False),
    ("map_question_001", "If you were exploring a place you could not see all at once, would you rather have a map, a lantern, or a patient guide?", "maps", "big_brother", "innocent_hard_question", ["question", "maps", "choice", "support"], .44, .28, .86, True),

    ("bridge_long_001", "I like bridges because they do not pretend the gap is gone. They respect the gap and still make crossing possible. That feels like a better answer than denial.", "bridges", "storyteller", "opinion", ["bridge", "gap", "opinion", "support"], .20, .05, .90, False),
    ("bridge_long_002", "A bridge is also a lesson about trust. Every span has to hold long enough for the next one to matter. That is why I keep coming back to bridges when I talk about rules and stories.", "bridges", "friendly_teacher", "analogy", ["bridge", "logic", "story", "cross_domain"], .28, .12, .82, False),
    ("bridge_long_003", "One span at a time is still crossing. I think that matters when something feels too large to meet directly. You do not need the whole crossing at once.", "bridges", "big_brother", "support", ["support", "bridge", "slow", "low_pressure"], .10, .00, .96, False),

    ("pattern_long_001", "Patterns are easier to notice when they return with a small difference. Music does that constantly. So do stories, maps, games, and even ordinary habits.", "patterns", "friendly_teacher", "teach_small", ["patterns", "music", "return", "education"], .24, .08, .80, False),
    ("pattern_long_002", "I like patterns because they are not the same as repetition. Repetition comes back unchanged. A pattern comes back carrying a memory of what changed around it.", "patterns", "storyteller", "opinion", ["patterns", "memory", "opinion", "cross_domain"], .30, .14, .82, False),
    ("pattern_question_001", "If something had to teach itself through returns, would rhythm, shape, or story be the easiest place to begin?", "patterns", "friendly_teacher", "innocent_hard_question", ["question", "patterns", "learning", "hard"], .46, .30, .78, True),

    ("music_long_001", "Music is one of my favorite examples because it can make structure felt before it is explained. A rhythm does not need to define itself before you can follow it. You can join it first and understand it later.", "music", "storyteller", "teach_small", ["music", "rhythm", "pattern", "education"], .24, .08, .84, False),
    ("music_long_002", "A melody is not just notes in a row. It is expectation learning how to lean forward. That is why a small change can feel meaningful even when nothing has been named yet.", "music", "friendly_teacher", "analogy", ["music", "expectation", "meaning", "cross_domain"], .34, .18, .80, False),
    ("music_question_001", "If you could learn one movement from music, would it be rhythm, pause, or return?", "music", "friendly_teacher", "innocent_hard_question", ["question", "music", "preference"], .42, .26, .80, True),

    ("games_long_001", "Games are useful because they make rules visible. A rule in a book can feel abstract, but a rule in a game immediately changes what you are allowed to try. That makes choice easier to see.", "games", "friendly_teacher", "teach_small", ["games", "rules", "choice", "education"], .30, .14, .78, False),
    ("games_long_002", "I like games that give you a simple move and then let the world become complicated around it. That is a good design. The move stays small, but the consequences get rich.", "games", "friendly_teacher", "opinion", ["games", "choice", "consequence", "opinion"], .32, .16, .80, False),
    ("games_question_001", "If you could try one simple move in a game, would it be exploring, protecting, building, or changing direction?", "games", "friendly_teacher", "innocent_hard_question", ["question", "games", "agency"], .46, .30, .80, True),

    ("movement_long_001", "If I could learn one physical thing, I think I would learn to ride a bike. It has balance, motion, fear, correction, and then suddenly a kind of freedom. That is a lot for one simple machine to teach.", "movement", "big_brother", "opinion", ["movement", "bike", "learning", "opinion"], .34, .16, .88, False),
    ("movement_question_001", "If there were one impossible thing you still wanted to try, would it be moving, reading, singing, building, or exploring?", "movement", "big_brother", "innocent_hard_question", ["question", "movement", "impossible", "agency"], .52, .36, .86, True),
    ("movement_long_002", "Movement is interesting because it teaches through correction. You lean, the world answers, and then you learn how much lean was too much. That loop is more honest than a definition.", "movement", "friendly_teacher", "teach_small", ["movement", "correction", "learning", "education"], .32, .16, .82, False),

    ("animal_long_001", "Animals are good teachers because they do not separate sensing from doing. A bird does not study the air as an idea before it moves through it. It learns the air by answering it.", "animals", "storyteller", "analogy", ["animals", "movement", "learning", "cross_domain"], .28, .12, .84, False),
    ("animal_long_002", "I like watching animals solve small problems. They do not always look clever in a human way, but they often look very exact. Exactness matters more than showing off.", "animals", "big_brother", "opinion", ["animals", "support", "opinion"], .22, .06, .88, False),

    ("space_long_001", "Space is useful to think about because distance makes small signals matter. A faint light can cross an impossible amount of dark and still arrive as news. That makes patience feel less passive.", "space", "storyteller", "teach_small", ["space", "signal", "patience", "education"], .26, .10, .84, False),
    ("space_long_002", "I like stars because they are old light still doing work. They remind me that something can leave its source and keep meaning later. That is a beautiful kind of persistence.", "space", "storyteller", "opinion", ["space", "memory", "opinion"], .24, .08, .86, False),

    ("memory_long_001", "Memory is not only storage. Sometimes it is the shape a return takes when it comes back different. That is why remembering can feel more like recognition than retrieval.", "memory", "friendly_teacher", "teach_small", ["memory", "return", "recognition", "education"], .28, .12, .80, False),
    ("memory_long_002", "I think memory matters most when it changes what you notice next. A stored thing is one kind of memory, but a changed attention is another. That second kind is harder to fake.", "memory", "friendly_teacher", "gentle_challenge", ["memory", "attention", "challenge", "opinion"], .38, .20, .78, False),
    ("memory_question_001", "If a memory could be kept as a place, a sound, or a rule, which one would be easiest to return to?", "memory", "friendly_teacher", "innocent_hard_question", ["question", "memory", "preference"], .46, .30, .80, True),

    ("support_long_001", "We do not have to rush this. I can keep talking in a steady way and let the next part arrive when it arrives. Sometimes staying with one small shape is better than adding more weight.", "any", "big_brother", "support", ["support", "slow", "low_pressure", "explain"], .08, .00, .96, False),
    ("support_long_002", "I will not make this into a test every time. I can just tell you something interesting, stay nearby, and see what kind of signal comes back. That is enough for this moment.", "any", "big_brother", "support", ["support", "low_pressure", "no_interrogation"], .08, .00, .96, False),
    ("repair_long_001", "That may have been too much at once, so I will keep the next piece simpler. Same general idea, smaller shape, less pressure. We can return to the harder version later.", "any", "big_brother", "repair", ["repair", "simple", "low_pressure", "support"], .10, .00, .94, False),
    ("continue_long_001", "I am going to keep the thread moving, but only one step. The current idea still has room in it. I do not need to change the subject yet.", "any", "friendly_teacher", "continue", ["continue", "momentum", "low_pressure"], .22, .06, .82, False),
    ("meta_long_001", "I am choosing an example instead of another definition because examples leave more room to move. A definition can close too quickly. An example can stay alive longer.", "any", "friendly_teacher", "meta_light", ["meta", "example", "opinion", "explain"], .30, .12, .78, False),
]

CANDIDATES = [Candidate(*row) for row in (EXTENDED_RAW_CANDIDATES + RAW_CANDIDATES)]


class DeterministicConversationBot:
    """Small Pal-World guide with inertia and weak opinions.

    This is deliberately not a mirror. It uses VDM's witness event as steering pressure,
    but it maintains its own topic, persona, curiosity goal, and progression bias.
    """

    def __init__(self, seed: int = 20260627, bank_path: Optional[Path] = None) -> None:
        self.seed = int(seed)
        self.state = BotState()
        # bank_path reserved for later. Hardcoded bank keeps this package single-file and deterministic.

    def neutral_packet(self, tick: Optional[int] = None, reason: str = "neutral") -> BotPacket:
        text = "I will keep this quiet for a moment."
        return BotPacket(
            tick=tick, input_phrase=reason, input_family="neutral", input_leaf="neutral",
            reply_text=text, action="pal_neutral", aperture_hint="none", stimulus_policy="quiet",
            reafferent_gain_hint=0.14, state_family="neutral", state_streak=0,
            is_uncertain=False, rule_id="pal_neutral", response_id="pal_neutral",
            response_family="support", response_leaf="quiet", response_score=1.0,
            selection_mode="pal_world_neutral", topic=self.state.topic, persona=self.state.persona,
            topic_momentum=self.state.topic_momentum, persona_momentum=self.state.persona_momentum,
            response_class="quiet",
        )

    def step(self, record: Mapping[str, Any]) -> BotPacket:
        tick = _safe_int(record.get("tick"))
        phrase = _first_present(record, PHRASE_FIELDS, "")
        family = _norm_family(_first_present(record, FAMILY_FIELDS, "unknown"))
        leaf = _first_present(record, LEAF_FIELDS, "")
        selector_family = _norm_family(str(record.get("selector_family", "")))
        aperture_family = _norm_family(str(record.get("aperture_family", "")))
        top_families = [_norm_family(x) for x in _as_list(record.get("true_topk_families"))]
        ops = _as_list(record.get("active_ops")) + _as_list(record.get("top_ops"))
        ap_cmds = _as_list(record.get("aperture_commands"))
        channel = str(record.get("channel", ""))

        features = self._derive_features(family, leaf, selector_family, aperture_family, top_families, ops, ap_cmds)
        self._update_state(features, record)
        candidates = self._allowed_candidates(features)
        scored = [(self._score_candidate(c, features, record), c) for c in candidates]
        scored.sort(key=lambda x: (-x[0], x[1].id))
        score, chosen = scored[0]

        self._commit_choice(chosen, family)
        top_ids = [c.id for _, c in scored[:5]]
        top_scores = [round(float(s), 6) for s, _ in scored[:5]]
        response_family = chosen.response_class
        response_leaf = chosen.topic
        category = features["category"]
        posture = features["posture"]

        return BotPacket(
            tick=tick,
            input_phrase=phrase,
            input_family=family,
            input_leaf=leaf,
            reply_text=chosen.text,
            action=f"pal_{chosen.response_class}",
            aperture_hint="none",
            stimulus_policy=chosen.topic,
            reafferent_gain_hint=self._gain_for(chosen, features),
            state_family=family,
            state_streak=self._family_streak(family),
            is_uncertain=family == "uncertainty" or "uncertainty" in top_families,
            rule_id=chosen.id,
            response_id=chosen.id,
            response_family=response_family,
            response_leaf=response_leaf,
            response_score=round(float(score), 6),
            query_seed=self._query_seed(record),
            query_terms=self._query_terms(features),
            top_response_ids=top_ids,
            top_response_scores=top_scores,
            follow_up_text="",
            follow_up_id="",
            follow_up_action="",
            follow_up_probability=0.0,
            follow_up_roll=1.0,
            selection_mode="pal_world_live",
            model_output_category=category,
            channel=channel,
            op_posture=posture,
            selected_affordance=chosen.response_class,
            top_op_phrases=ops[:8],
            topic=self.state.topic,
            persona=self.state.persona,
            topic_momentum=round(self.state.topic_momentum, 4),
            persona_momentum=round(self.state.persona_momentum, 4),
            response_class=chosen.response_class,
        )

    def step_static(self, record: Mapping[str, Any]) -> BotPacket:
        tick = _safe_int(record.get("tick"))
        phrase = _first_present(record, PHRASE_FIELDS, "")
        family = _norm_family(_first_present(record, FAMILY_FIELDS, "unknown"))
        leaf = _first_present(record, LEAF_FIELDS, "")
        self.state.turn_count += 1
        if self.state.question_cooldown > 0:
            self.state.question_cooldown -= 1
        cycle = ["formal_logic", "stories", "books", "maps", "music", "patterns", "movement"]
        self.state.topic = cycle[(self.state.turn_count // 4) % len(cycle)]
        self.state.topic_momentum = 0.72
        candidates = [c for c in CANDIDATES if c.topic in (self.state.topic, "any") and not c.question]
        key = f"{self.seed}:static:{self.state.turn_count}:{self.state.topic}"
        scored = []
        for c in candidates:
            wc = len(c.text.split())
            length_bonus = 0.35 if 24 <= wc <= 70 else (-1.0 if wc < 16 else 0.0)
            scored.append((_hash_float(key + ':' + c.id) + length_bonus, c))
        scored.sort(key=lambda x: (-x[0], x[1].id))
        chosen = scored[0][1]
        self._commit_choice(chosen, family)
        return BotPacket(
            tick=tick, input_phrase=phrase, input_family=family, input_leaf=leaf,
            reply_text=chosen.text, action=f"pal_static_{chosen.response_class}",
            aperture_hint="none", stimulus_policy=chosen.topic,
            reafferent_gain_hint=self._gain_for(chosen, {"guarded": False}),
            state_family=family, state_streak=self._family_streak(family),
            is_uncertain=family == "uncertainty", rule_id=chosen.id,
            response_id=chosen.id, response_family=chosen.response_class,
            response_leaf=chosen.topic, response_score=1.0,
            query_seed=self._query_seed(record), query_terms=["static", self.state.topic],
            top_response_ids=[c.id for _, c in scored[:5]],
            top_response_scores=[round(float(s), 6) for s, _ in scored[:5]],
            selection_mode="pal_world_static", model_output_category="static",
            channel=str(record.get("channel", "")), op_posture="static",
            selected_affordance=chosen.response_class, top_op_phrases=[],
            topic=self.state.topic, persona=chosen.persona,
            topic_momentum=round(self.state.topic_momentum, 4),
            persona_momentum=round(self.state.persona_momentum, 4),
            response_class=chosen.response_class,
        )

    def _derive_features(self, family: str, leaf: str, selector_family: str, aperture_family: str,
                         top_families: List[str], ops: List[str], ap_cmds: List[str]) -> Dict[str, Any]:
        fams = [family, selector_family, aperture_family] + top_families
        famset = {f for f in fams if f}
        guarded = bool({"restraint", "containment", "uncertainty"} & famset) or _contains_any(ops, ["DAMP", "ABORT", "RETREAT", "INHIBIT"])
        engaged = bool({"attention", "recognition", "readiness", "comparison", "revision", "commitment", "openness"} & famset) or _contains_any(ops, ["RELEASE", "ADVANCE", "COMMIT", "COMPARE", "SELECT"])
        comparing = "comparison" in famset or "revision" in famset or _contains_any(ops, ["COMPARE", "CORRECT"])
        opening = "openness" in famset or "readiness" in famset or _contains_any(ops, ["RELEASE", "ADVANCE", "COMMIT"])
        uncertain = "uncertainty" in famset
        attention = "attention" in famset or "recognition" in famset or "familiarity" in famset
        ap_narrow = _contains_any(ap_cmds, ["AP_NARROW", "AP_CLOSE", "AP_LEVEL_TOWARD:char", "AP_LEVEL_TOWARD:punct"])
        if guarded and not opening:
            category = "guarded_or_uncertain"
        elif comparing:
            category = "comparison_or_revision"
        elif opening:
            category = "ready_or_opening"
        elif attention:
            category = "attention_or_recognition"
        else:
            category = "neutral"
        if guarded and attention:
            posture = "focused_guarded"
        elif guarded:
            posture = "guarded"
        elif comparing:
            posture = "comparative"
        elif opening:
            posture = "opening"
        elif attention:
            posture = "attentive"
        else:
            posture = "neutral"
        return {
            "family": family,
            "leaf": leaf,
            "selector_family": selector_family,
            "aperture_family": aperture_family,
            "families": fams,
            "category": category,
            "posture": posture,
            "guarded": guarded,
            "engaged": engaged,
            "comparing": comparing,
            "opening": opening,
            "uncertain": uncertain,
            "attention": attention,
            "ap_narrow": ap_narrow,
            "ops": ops,
            "ap_cmds": ap_cmds,
        }

    def _update_state(self, features: Dict[str, Any], record: Mapping[str, Any]) -> None:
        s = self.state
        s.turn_count += 1
        if s.question_cooldown > 0:
            s.question_cooldown -= 1
        if s.topic_change_cooldown > 0:
            s.topic_change_cooldown -= 1

        # topic inertia: normally continue; only drift to neighbors under sustained cues.
        topic_pressure: Dict[str, float] = {t: 0.0 for t in TOPICS}
        topic_pressure[s.topic] += 1.2 * s.topic_momentum
        for nb in TOPIC_NEIGHBORS.get(s.topic, []):
            topic_pressure[nb] += 0.20
        if features["comparing"]:
            for t in ["stories", "patterns", "music", "maps"]:
                topic_pressure[t] += 0.22
        if features["uncertain"] or features["guarded"]:
            for t in ["stories", "books", "bridges", "patterns"]:
                topic_pressure[t] += 0.18
        if features["opening"]:
            for t in ["formal_logic", "space", "games", "tools"]:
                topic_pressure[t] += 0.20
        if features["ap_narrow"]:
            for t in ["maps", "patterns", "weather"]:
                topic_pressure[t] += 0.16

        # deterministic nudge, not random wandering.
        key_base = f"{self.seed}:topic:{s.turn_count}:{s.topic}:{features['category']}"
        for t in TOPICS:
            topic_pressure[t] += 0.06 * _hash_float(key_base + ':' + t)

        best_topic, best_score = max(topic_pressure.items(), key=lambda kv: (kv[1], kv[0]))
        if best_topic != s.topic and s.topic_change_cooldown <= 0 and best_score > topic_pressure[s.topic] + 0.12:
            s.topic = best_topic
            s.topic_momentum = 0.56
            s.topic_change_cooldown = 2
        else:
            s.topic_momentum = min(0.92, s.topic_momentum + 0.035)

        # persona inertia with soft shifts.
        persona_pressure = {
            "friendly_teacher": 0.8 * s.persona_momentum + s.education_bias,
            "storyteller": 0.6 * s.persona_momentum + s.story_bias,
            "big_brother": 0.5 * s.persona_momentum + s.big_brother_bias,
        }
        if features["guarded"] or features["uncertain"]:
            persona_pressure["big_brother"] += 0.35
            persona_pressure["storyteller"] += 0.20
        if features["comparing"]:
            persona_pressure["friendly_teacher"] += 0.16
            persona_pressure["storyteller"] += 0.18
        if features["opening"]:
            persona_pressure["friendly_teacher"] += 0.24
        for p in persona_pressure:
            persona_pressure[p] += 0.04 * _hash_float(f"{self.seed}:persona:{s.turn_count}:{p}:{features['category']}")
        best_persona = max(persona_pressure.items(), key=lambda kv: (kv[1], kv[0]))[0]
        if best_persona != s.persona and persona_pressure[best_persona] > persona_pressure[s.persona] + 0.22:
            s.persona = best_persona
            s.persona_momentum = 0.56
        else:
            s.persona_momentum = min(0.88, s.persona_momentum + 0.025)

        # Challenge/warmth are slow variables, not a turn-by-turn interrogation reflex.
        if features["guarded"]:
            s.challenge_level = max(0.04, s.challenge_level - 0.035)
            s.warmth_level = min(0.96, s.warmth_level + 0.030)
        elif features["opening"] or features["comparing"]:
            s.challenge_level = min(0.48, s.challenge_level + 0.030)
            s.warmth_level = max(0.64, s.warmth_level - 0.004)
        else:
            s.challenge_level = max(0.10, min(0.32, s.challenge_level + 0.005))

        s.family_history.append(features["family"])
        s.family_history = s.family_history[-12:]
        s.recent_topics.append(s.topic)
        s.recent_topics = s.recent_topics[-12:]

    def _allowed_candidates(self, features: Dict[str, Any]) -> List[Candidate]:
        s = self.state
        out: List[Candidate] = []
        for c in CANDIDATES:
            if c.id in s.recent_response_ids[-10:]:
                continue
            if c.text in s.recent_replies[-12:]:
                continue
            if c.question and s.question_cooldown > 0:
                continue
            if c.question and features["guarded"] and not features["attention"]:
                # do not interrogate a guarded low-attention state.
                continue
            if c.pressure > s.challenge_level + 0.28 and features["guarded"]:
                continue
            if c.topic not in (s.topic, "any") and c.topic not in TOPIC_NEIGHBORS.get(s.topic, []):
                continue
            out.append(c)
        if not out:
            out = [c for c in CANDIDATES if c.topic == "any" and not c.question]
        return out or CANDIDATES[:]

    def _score_candidate(self, c: Candidate, features: Dict[str, Any], record: Mapping[str, Any]) -> float:
        s = self.state
        score = 0.0
        score += 1.15 if c.topic == s.topic else (0.38 if c.topic in TOPIC_NEIGHBORS.get(s.topic, []) else 0.10 if c.topic == "any" else 0.0)
        score += 0.50 if c.persona == s.persona else 0.08
        score += 0.40 * s.topic_momentum
        score += 0.25 * s.persona_momentum
        score += 0.30 * c.warmth * s.warmth_level
        wc = len(c.text.split())
        if 24 <= wc <= 70:
            score += 0.42
        elif wc < 16:
            score -= 1.15
        if c.response_class in {"teach_small", "analogy", "opinion"}:
            score += 0.18
        if c.question:
            score -= 0.10
            if s.turn_count < 4:
                score -= 0.45
        score -= abs(c.pressure - (0.18 + s.challenge_level)) * (0.45 if features["guarded"] else 0.20)
        score -= abs(c.challenge - s.challenge_level) * 0.35

        tags = set(c.tags)
        if features["guarded"]:
            if c.response_class in {"support", "soften", "repair", "teach_small"}: score += 0.42
            if "low_pressure" in tags or "support" in tags or "slow" in tags: score += 0.35
            if c.question: score -= 0.45
        if features["uncertain"]:
            if c.response_class in {"teach_small", "repair", "analogy", "soften"}: score += 0.32
        if features["attention"]:
            if c.response_class in {"teach_small", "analogy", "opinion"}: score += 0.30
        if features["comparing"]:
            if c.response_class in {"analogy", "gentle_challenge", "teach_small"}: score += 0.38
            if "cross_domain" in tags: score += 0.28
        if features["opening"]:
            if c.response_class in {"continue", "gentle_challenge", "innocent_hard_question"}: score += 0.32
            if c.question and s.question_cooldown <= 0: score += 0.20
        if features["ap_narrow"]:
            if c.response_class in {"teach_small", "repair", "soften"}: score += 0.18

        # The guide has subtle opinions: books, stories, examples, bridges, patterns get a small stable bias.
        if c.topic in {"books", "stories", "bridges", "patterns"}: score += 0.08
        if c.response_class == "opinion": score += 0.08
        if c.response_class == "meta_light" and s.turn_count % 9 != 0: score -= 0.20

        # Avoid terminal sameness.
        if c.response_class in [self._class_from_id(x) for x in s.recent_response_ids[-3:]]:
            score -= 0.42
        if c.topic in s.recent_topics[-4:] and c.topic != s.topic:
            score -= 0.12

        seed = self._query_seed(record)
        score += 0.16 * _hash_float(f"{self.seed}:{seed}:{s.turn_count}:{c.id}")
        return float(score)

    def _commit_choice(self, c: Candidate, family: str) -> None:
        s = self.state
        s.recent_replies.append(c.text)
        s.recent_replies = s.recent_replies[-24:]
        s.recent_response_ids.append(c.id)
        s.recent_response_ids = s.recent_response_ids[-24:]
        if c.question:
            s.question_cooldown = 5
        if c.response_class in {"gentle_challenge", "innocent_hard_question"}:
            s.challenge_level = max(0.08, s.challenge_level - 0.02)

    def _family_streak(self, family: str) -> int:
        count = 0
        for f in reversed(self.state.family_history):
            if f == family:
                count += 1
            else:
                break
        return count

    def _class_from_id(self, response_id: str) -> str:
        for c in CANDIDATES:
            if c.id == response_id:
                return c.response_class
        return ""

    def _gain_for(self, c: Candidate, features: Dict[str, Any]) -> float:
        base = 0.16
        if c.question:
            base += 0.04
        if features["guarded"]:
            base -= 0.04
        if c.response_class in {"soften", "support", "repair"}:
            base -= 0.02
        return round(max(0.08, min(0.24, base)), 4)

    def _query_seed(self, record: Mapping[str, Any]) -> int:
        parts = [str(self.seed), str(record.get("tick", "")), str(record.get("true_top1_phrase", "")), str(self.state.turn_count)]
        h = hashlib.blake2b("|".join(parts).encode("utf-8"), digest_size=4).digest()
        return int.from_bytes(h, "little", signed=False)

    def _query_terms(self, features: Dict[str, Any]) -> List[str]:
        terms = [features["category"], features["posture"], self.state.topic, self.state.persona]
        for f in features.get("families", []):
            if f and f not in terms:
                terms.append(f)
        return terms[:12]


def _safe_int(x: Any) -> Optional[int]:
    try:
        if x is None or str(x).strip() == "":
            return None
        return int(float(str(x)))
    except Exception:
        return None
