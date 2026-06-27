# VDM Fixed-Neuron Character Actuator

This package implements the writing channel as a literal fixed efferent neuron map.

It does not accept abstract character scores. Characters are bound to fixed neuron IDs.
The model writes by holding `WRITE_MODE` and spiking/holding the mapped character neuron.

## Fixed neuron map

Controls:

| control | neuron |
|---|---:|
| WRITE_MODE | 0 |
| SEND | 1 |
| BACKSPACE | 2 |
| CLEAR | 3 |

Characters:

- Printable ASCII `chr(32)` through `chr(126)`
- Plus newline `\n`
- Assigned contiguously beginning at neuron `4`
- Total required surface: 100 fixed actuator neurons

Examples:

| character | neuron |
|---|---:|
| space | 4 |
| `!` | 5 |
| `0` | 20 |
| `A` | 37 |
| `a` | 69 |
| `~` | 98 |
| newline | 99 |

## Tick law

At each tick, the channel reads fixed neuron activations.

1. `WRITE_MODE` must be held above threshold to arm writing.
2. While armed, the strongest mapped character neuron may append its exact character.
3. `SEND` submits the stasis buffer.
4. `BACKSPACE` removes the last buffered character.
5. `CLEAR` empties the buffer.

If `SEND` and the normal intent witness happen on the same tick, reafference is composed as:

```text
<intent witness>
[written_message]
<buffer text>
```

The combined text is intended to go through the same UTE reafferent pathway.

## Run tests

```bash
cd vdm_fixed_neuron_char_actuator_package
PYTHONPATH=src python -m pytest -q
```

## Demo

```bash
cd vdm_fixed_neuron_char_actuator_package
PYTHONPATH=src python scripts/run_demo.py
```

## Run on JSONL ticks

Input rows must contain `tick` and `neuron_scores`. `neuron_scores` may be an object keyed by neuron id or a list where index = neuron id.

```json
{"tick":0,"neuron_scores":{"0":0.9,"41":0.95}}
{"tick":1,"neuron_scores":{"0":0.0}}
{"tick":2,"neuron_scores":{"0":0.9,"77":0.95}}
{"tick":3,"neuron_scores":{"1":0.9}}
{"tick":4,"neuron_scores":{"1":0.9},"intent_text":"I think I hold attention here.","witness_event":true}
```

Command:

```bash
PYTHONPATH=src python -m vdm_fixed_char_actuator.cli \
  --input examples/hi_fixed_neuron_trace.jsonl \
  --output /tmp/char_actuator_output.jsonl \
  --mapping-csv /tmp/fixed_neuron_map.csv
```


## Actual validation results

The real run results are in:

```text
results/ACTUAL_TEST_RUN_RESULTS.md
results/RUN_SUMMARY.json
results/demo_hi/
results/full_surface_validation/
results/pytest/
```

The full-surface validation appends every printable ASCII character plus newline through the fixed neuron map, sends the buffer, and checks that the submitted message exactly matches the expected 96-character alphabet.

## Where the test run results are

- Root summary: `TEST_RESULTS.md`
- Actual run summary: `results/ACTUAL_TEST_RUN_RESULTS.md`
- Machine summary: `results/RUN_SUMMARY.json`
- Demo trace/output: `results/demo_hi/`
- Full alphabet validation: `results/full_surface_validation/`
- Pytest output: `results/pytest/pytest_stdout.txt`
