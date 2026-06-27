from __future__ import annotations

import json
from vdm_fixed_char_actuator import FixedNeuronCharMap, FixedNeuronWritingActuator

m = FixedNeuronCharMap()
a = FixedNeuronWritingActuator(mapping=m)
char = m.char_to_neuron

rows = []

def tick(t, **scores):
    ns = {m.write_mode_neuron: scores.pop("WRITE_MODE", 0.0), m.send_neuron: scores.pop("SEND", 0.0)}
    ns[m.backspace_neuron] = scores.pop("BACKSPACE", 0.0)
    ns[m.clear_neuron] = scores.pop("CLEAR", 0.0)
    for k, v in scores.items():
        ns[char[k]] = v
    out = a.step(t, ns, intent_text="I think I hold attention here." if t == 6 else None, witness_event=(t == 6))
    rows.append(out.__dict__)

# write Hi! then send with an intent witness on the send tick
tick(0, WRITE_MODE=0.9, H=0.9)
tick(1, WRITE_MODE=0.0)
tick(2, WRITE_MODE=0.9, i=0.9)
tick(3, WRITE_MODE=0.0)
tick(4, WRITE_MODE=0.9, **{"!": 0.9})
tick(5, SEND=0.9)
tick(6, SEND=0.9)

for r in rows:
    print(json.dumps(r, ensure_ascii=False))
