from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union, Any

# Fixed character surface:
# - printable ASCII 32..126 includes space, punctuation, digits, uppercase, lowercase
# - newline is added as a writing character because messages need line breaks
PRINTABLE_ASCII_WITH_NEWLINE: Tuple[str, ...] = tuple(chr(i) for i in range(32, 127)) + ("\n",)


@dataclass(frozen=True)
class FixedNeuronCharMap:
    """Fixed efferent neuron map for writing.

    The mapping is literal and stable. It is intentionally not learned here.

    Controls:
      WRITE_MODE: arm writing while held
      SEND: submit buffer while held
      BACKSPACE: remove last buffered char while held
      CLEAR: clear buffer while held

    Characters:
      printable ASCII 32..126 plus newline, assigned contiguously.
    """

    write_mode_neuron: int = 0
    send_neuron: int = 1
    backspace_neuron: int = 2
    clear_neuron: int = 3
    first_char_neuron: int = 4
    alphabet: Tuple[str, ...] = PRINTABLE_ASCII_WITH_NEWLINE

    def __post_init__(self) -> None:
        ids = [self.write_mode_neuron, self.send_neuron, self.backspace_neuron, self.clear_neuron]
        ids.extend(self.first_char_neuron + i for i in range(len(self.alphabet)))
        if len(ids) != len(set(ids)):
            raise ValueError("FixedNeuronCharMap contains duplicate neuron ids")
        if not self.alphabet:
            raise ValueError("alphabet cannot be empty")

    @property
    def char_to_neuron(self) -> Dict[str, int]:
        return {ch: self.first_char_neuron + i for i, ch in enumerate(self.alphabet)}

    @property
    def neuron_to_char(self) -> Dict[int, str]:
        return {self.first_char_neuron + i: ch for i, ch in enumerate(self.alphabet)}

    @property
    def total_neurons_required(self) -> int:
        return self.first_char_neuron + len(self.alphabet)

    def as_rows(self) -> Sequence[Tuple[str, int, str]]:
        rows = [
            ("WRITE_MODE", self.write_mode_neuron, "control"),
            ("SEND", self.send_neuron, "control"),
            ("BACKSPACE", self.backspace_neuron, "control"),
            ("CLEAR", self.clear_neuron, "control"),
        ]
        for ch, nid in self.char_to_neuron.items():
            label = "NEWLINE" if ch == "\n" else ("SPACE" if ch == " " else ch)
            rows.append((label, nid, "character"))
        return rows


@dataclass(frozen=True)
class TickInput:
    tick: int
    neuron_scores: Mapping[int, float]
    intent_text: Optional[str] = None
    witness_event: bool = False


@dataclass(frozen=True)
class TickOutput:
    tick: int
    write_mode_active: bool
    appended_char: Optional[str]
    submitted_message: Optional[str]
    reafferent_text: Optional[str]
    buffer_text: str
    selected_char_neuron: Optional[int]
    selected_char_score: float
    send_active: bool
    backspace_active: bool
    clear_active: bool
    event: str


@dataclass
class FixedNeuronWritingActuator:
    """Fixed-neuron written-message actuator.

    This class only enforces the motor-channel law. VDM must produce the neuron
    activations. Characters are not decoded from semantics. A mapped character
    neuron firing while WRITE_MODE is held appends that exact character.
    """

    mapping: FixedNeuronCharMap = field(default_factory=FixedNeuronCharMap)
    write_threshold: float = 0.70
    char_threshold: float = 0.70
    char_margin: float = 0.05
    send_threshold: float = 0.80
    backspace_threshold: float = 0.80
    clear_threshold: float = 0.88
    write_hold_ticks: int = 1
    char_hold_ticks: int = 1
    send_hold_ticks: int = 2
    backspace_hold_ticks: int = 2
    clear_hold_ticks: int = 3
    release_threshold: float = 0.35
    max_buffer_chars: int = 4096

    buffer_text: str = ""
    _write_hold: int = 0
    _send_hold: int = 0
    _backspace_hold: int = 0
    _clear_hold: int = 0
    _held_char_neuron: Optional[int] = None
    _held_char_count: int = 0
    _latched_char_neuron: Optional[int] = None
    _send_latched: bool = False
    _backspace_latched: bool = False
    _clear_latched: bool = False

    def snapshot(self) -> Dict[str, Any]:
        return {
            "buffer_text": self.buffer_text,
            "write_hold": self._write_hold,
            "send_hold": self._send_hold,
            "backspace_hold": self._backspace_hold,
            "clear_hold": self._clear_hold,
            "held_char_neuron": self._held_char_neuron,
            "held_char_count": self._held_char_count,
            "latched_char_neuron": self._latched_char_neuron,
            "send_latched": self._send_latched,
            "backspace_latched": self._backspace_latched,
            "clear_latched": self._clear_latched,
        }

    def restore(self, state: Mapping[str, Any]) -> None:
        self.buffer_text = str(state.get("buffer_text", ""))
        self._write_hold = int(state.get("write_hold", 0))
        self._send_hold = int(state.get("send_hold", 0))
        self._backspace_hold = int(state.get("backspace_hold", 0))
        self._clear_hold = int(state.get("clear_hold", 0))
        self._held_char_neuron = _maybe_int(state.get("held_char_neuron"))
        self._held_char_count = int(state.get("held_char_count", 0))
        self._latched_char_neuron = _maybe_int(state.get("latched_char_neuron"))
        self._send_latched = bool(state.get("send_latched", False))
        self._backspace_latched = bool(state.get("backspace_latched", False))
        self._clear_latched = bool(state.get("clear_latched", False))

    def step(
        self,
        tick: int,
        neuron_scores: Mapping[int, float],
        *,
        intent_text: Optional[str] = None,
        witness_event: bool = False,
    ) -> TickOutput:
        scores = {int(k): float(v) for k, v in neuron_scores.items()}

        write_score = scores.get(self.mapping.write_mode_neuron, 0.0)
        send_score = scores.get(self.mapping.send_neuron, 0.0)
        backspace_score = scores.get(self.mapping.backspace_neuron, 0.0)
        clear_score = scores.get(self.mapping.clear_neuron, 0.0)

        write_mode_active = self._held(write_score, "write")
        send_active = self._held(send_score, "send")
        backspace_active = self._held(backspace_score, "backspace")
        clear_active = self._held(clear_score, "clear")

        # Release latches when pressure falls low enough.
        if send_score < self.release_threshold:
            self._send_latched = False
        if backspace_score < self.release_threshold:
            self._backspace_latched = False
        if clear_score < self.release_threshold:
            self._clear_latched = False

        appended_char: Optional[str] = None
        submitted_message: Optional[str] = None
        event = "none"

        if clear_active and not self._clear_latched:
            self.buffer_text = ""
            self._clear_latched = True
            self._held_char_neuron = None
            self._held_char_count = 0
            self._latched_char_neuron = None
            event = "clear"
        elif backspace_active and not self._backspace_latched:
            if self.buffer_text:
                self.buffer_text = self.buffer_text[:-1]
                event = "backspace"
            self._backspace_latched = True
        elif send_active and not self._send_latched and self.buffer_text:
            submitted_message = self.buffer_text
            self.buffer_text = ""
            self._send_latched = True
            self._held_char_neuron = None
            self._held_char_count = 0
            self._latched_char_neuron = None
            event = "send"
        else:
            selected_neuron, selected_score, second_score = self._select_char(scores)
            if write_mode_active and selected_neuron is not None:
                if selected_score >= self.char_threshold and (selected_score - second_score) >= self.char_margin:
                    if selected_neuron == self._held_char_neuron:
                        self._held_char_count += 1
                    else:
                        self._held_char_neuron = selected_neuron
                        self._held_char_count = 1

                    if (
                        self._held_char_count >= self.char_hold_ticks
                        and self._latched_char_neuron != selected_neuron
                        and len(self.buffer_text) < self.max_buffer_chars
                    ):
                        appended_char = self.mapping.neuron_to_char[selected_neuron]
                        self.buffer_text += appended_char
                        self._latched_char_neuron = selected_neuron
                        event = "append"
                else:
                    self._held_char_neuron = None
                    self._held_char_count = 0
            else:
                self._held_char_neuron = None
                self._held_char_count = 0

            # Release repeated-char latch when that exact char drops.
            if self._latched_char_neuron is not None:
                if scores.get(self._latched_char_neuron, 0.0) < self.release_threshold:
                    self._latched_char_neuron = None

        selected_neuron, selected_score, _ = self._select_char(scores)
        reafferent_text = self._compose_reafferent(intent_text, witness_event, submitted_message)
        return TickOutput(
            tick=int(tick),
            write_mode_active=bool(write_mode_active),
            appended_char=appended_char,
            submitted_message=submitted_message,
            reafferent_text=reafferent_text,
            buffer_text=self.buffer_text,
            selected_char_neuron=selected_neuron,
            selected_char_score=float(selected_score),
            send_active=bool(send_active),
            backspace_active=bool(backspace_active),
            clear_active=bool(clear_active),
            event=event,
        )

    def _held(self, score: float, control: str) -> bool:
        if control == "write":
            if score >= self.write_threshold:
                self._write_hold += 1
            else:
                self._write_hold = 0
            return self._write_hold >= self.write_hold_ticks
        if control == "send":
            if score >= self.send_threshold:
                self._send_hold += 1
            else:
                self._send_hold = 0
            return self._send_hold >= self.send_hold_ticks
        if control == "backspace":
            if score >= self.backspace_threshold:
                self._backspace_hold += 1
            else:
                self._backspace_hold = 0
            return self._backspace_hold >= self.backspace_hold_ticks
        if control == "clear":
            if score >= self.clear_threshold:
                self._clear_hold += 1
            else:
                self._clear_hold = 0
            return self._clear_hold >= self.clear_hold_ticks
        raise ValueError(f"unknown control {control!r}")

    def _select_char(self, scores: Mapping[int, float]) -> Tuple[Optional[int], float, float]:
        best_id: Optional[int] = None
        best = float("-inf")
        second = float("-inf")
        for nid in self.mapping.neuron_to_char:
            s = float(scores.get(nid, 0.0))
            if s > best:
                second = best
                best = s
                best_id = nid
            elif s > second:
                second = s
        if best_id is None:
            return None, 0.0, 0.0
        if second == float("-inf"):
            second = 0.0
        return best_id, float(best), float(second)

    @staticmethod
    def _compose_reafferent(
        intent_text: Optional[str],
        witness_event: bool,
        submitted_message: Optional[str],
    ) -> Optional[str]:
        parts = []
        if witness_event and intent_text:
            parts.append(str(intent_text))
        if submitted_message is not None:
            parts.append("[written_message]\n" + submitted_message)
        if not parts:
            return None
        return "\n".join(parts)


def _maybe_int(x: Any) -> Optional[int]:
    if x is None:
        return None
    try:
        return int(x)
    except Exception:
        return None
