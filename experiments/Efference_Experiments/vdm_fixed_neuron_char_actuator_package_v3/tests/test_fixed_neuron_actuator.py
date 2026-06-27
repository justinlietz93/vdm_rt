from vdm_fixed_char_actuator import FixedNeuronCharMap, FixedNeuronWritingActuator


def scores(mapping, **kw):
    out = {}
    for k, v in kw.items():
        if k == "WRITE_MODE":
            out[mapping.write_mode_neuron] = v
        elif k == "SEND":
            out[mapping.send_neuron] = v
        elif k == "BACKSPACE":
            out[mapping.backspace_neuron] = v
        elif k == "CLEAR":
            out[mapping.clear_neuron] = v
        else:
            out[mapping.char_to_neuron[k]] = v
    return out


def test_full_printable_ascii_and_newline_mapping():
    m = FixedNeuronCharMap()
    assert len(m.alphabet) == 96
    assert m.char_to_neuron[" "] == 4
    assert m.char_to_neuron["!"] == 5
    assert m.char_to_neuron["0"] == 20
    assert m.char_to_neuron["A"] == 37
    assert m.char_to_neuron["a"] == 69
    assert m.char_to_neuron["~"] == 98
    assert m.char_to_neuron["\n"] == 99
    assert m.total_neurons_required == 100


def test_write_mode_required_for_character_append():
    m = FixedNeuronCharMap()
    a = FixedNeuronWritingActuator(mapping=m, char_hold_ticks=1, write_hold_ticks=1)
    out = a.step(0, scores(m, H=0.95))
    assert out.appended_char is None
    assert out.buffer_text == ""
    out = a.step(1, scores(m, WRITE_MODE=0.9, H=0.95))
    assert out.appended_char == "H"
    assert out.buffer_text == "H"


def test_full_case_punctuation_number_message_send():
    m = FixedNeuronCharMap()
    a = FixedNeuronWritingActuator(mapping=m, char_hold_ticks=1, write_hold_ticks=1, send_hold_ticks=2)
    t = 0
    for ch in "Aa0!?":
        out = a.step(t, scores(m, WRITE_MODE=0.9, **{ch: 0.95}))
        assert out.appended_char == ch
        t += 1
        a.step(t, scores(m))  # release repeated-char latch
        t += 1
    assert a.buffer_text == "Aa0!?"
    out = a.step(t, scores(m, SEND=0.9))
    assert out.submitted_message is None
    out = a.step(t + 1, scores(m, SEND=0.9), intent_text="Intent.", witness_event=True)
    assert out.submitted_message == "Aa0!?"
    assert out.reafferent_text == "Intent.\n[written_message]\nAa0!?"
    assert out.buffer_text == ""


def test_latch_prevents_unbounded_repeated_character():
    m = FixedNeuronCharMap()
    a = FixedNeuronWritingActuator(mapping=m, char_hold_ticks=1, write_hold_ticks=1)
    for t in range(5):
        a.step(t, scores(m, WRITE_MODE=0.9, x=0.95))
    assert a.buffer_text == "x"
    a.step(6, scores(m, WRITE_MODE=0.9, x=0.0))
    a.step(7, scores(m, WRITE_MODE=0.9, x=0.95))
    assert a.buffer_text == "xx"


def test_backspace_clear_and_snapshot_restore():
    m = FixedNeuronCharMap()
    a = FixedNeuronWritingActuator(mapping=m, char_hold_ticks=1, write_hold_ticks=1, backspace_hold_ticks=1, clear_hold_ticks=1)
    a.step(0, scores(m, WRITE_MODE=0.9, h=0.9))
    a.step(1, scores(m, WRITE_MODE=0.0))
    a.step(2, scores(m, WRITE_MODE=0.9, i=0.9))
    assert a.buffer_text == "hi"
    state = a.snapshot()
    b = FixedNeuronWritingActuator(mapping=m, char_hold_ticks=1, write_hold_ticks=1, backspace_hold_ticks=1, clear_hold_ticks=1)
    b.restore(state)
    assert b.buffer_text == "hi"
    out = b.step(3, scores(m, BACKSPACE=0.9))
    assert out.buffer_text == "h"
    b.step(4, scores(m, BACKSPACE=0.0))
    out = b.step(5, scores(m, CLEAR=0.9))
    assert out.buffer_text == ""
