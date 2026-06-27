# Fixed-Neuron Written Message Channel Spec

## Purpose

Give VDM a literal motor surface for writing. The model must hold a write intent and spike fixed character neurons to type.

## Surface

- 4 fixed control neurons
- 96 fixed character neurons
- 100 total actuator neurons

## Controls

```text
0 WRITE_MODE
1 SEND
2 BACKSPACE
3 CLEAR
```

## Character neurons

```text
4..98  printable ASCII chr(32)..chr(126)
99     newline
```

The mapping is deterministic and never shuffled inside a run.

## Character act

```text
if WRITE_MODE >= threshold:
    if mapped CHAR_X >= threshold and wins margin:
        append X
```

## Stasis buffer

The buffer persists across ticks. The model can write characters without submitting. Submission requires SEND.

## Reafference composition

If written submission occurs with a normal intent witness:

```text
<intent witness>
[written_message]
<message>
```

If only written submission occurs:

```text
[written_message]
<message>
```

## Integration requirement

Runtime must expose the 100 actuator neuron scores per tick from the actual fixed efferent surface. This package enforces the channel law only.
