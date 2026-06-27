# Real Test Run Results
This is the actual actuator validation run, not just a pytest count.
## Fixed surface
- Controls: **4** fixed neurons: WRITE_MODE, SEND, BACKSPACE, CLEAR
- Characters: **96** fixed character neurons
- Total fixed efferent surface: **100 neurons**
- Character set: printable ASCII `chr(32)..chr(126)` plus newline

## Mapping checks
- `space` -> neuron `4`
- `0` -> neuron `20`
- `A` -> neuron `37`
- `a` -> neuron `69`
- `~` -> neuron `98`
- `newline` -> neuron `99`

## Demo run: write `Hi!` then SEND with intent witness
- Appended chars: `['H', 'i', '!']`
- Submitted message: `Hi!`
- Reafferent text:

```text
I think I hold attention here.
[written_message]
Hi!
```
- PASS: `True`

Files:
- `results/demo_hi/hi_input_trace.jsonl`
- `results/demo_hi/hi_output.jsonl`
- `results/demo_hi/fixed_neuron_map.csv`

## Full surface validation
- Append events: **96**
- Submitted message length: **96**
- Message exactly matches printable ASCII + newline: **True**
- First 10 chars repr: `' !"#$%&\'()'`
- Last 10 chars repr: `'vwxyz{|}~\n'`
- PASS: `True`

Files:
- `results/full_surface_validation/full_alphabet_input_trace.jsonl`
- `results/full_surface_validation/full_alphabet_output.jsonl`
- `results/full_surface_validation/fixed_neuron_map.csv`
- `results/full_surface_validation/expected_message.json`

## Unit tests
```text
.....                                                                    [100%]
5 passed in 0.20s
```
