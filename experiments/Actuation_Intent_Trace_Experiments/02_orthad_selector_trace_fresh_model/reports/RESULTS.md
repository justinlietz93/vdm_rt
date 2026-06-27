# Orthad selector-trace fresh-model results

## Run identity

This package runs the VDM runtime from a fresh retained state and tests a selector-trace UTD surface.

Primary readable run:

```text
run: runs/selector_trace_fresh_1k_current
N = 1000
walkers = 1200
ticks = 260
seed = 11
curriculum = rich readable Orthad atoms
reafference = witness consequence only
final H5 = state_260.h5 (43,886 bytes)
mean tick = 0.104 s
```

Opaque companion run:

```text
run: runs/selector_trace_fresh_1k_current_opaque
N = 1000
walkers = 1200
ticks = 260
seed = 11
curriculum = same temporal grammar, opaque token surface
reafference = witness consequence only
final H5 = state_260.h5 (43,658 bytes)
mean tick = 0.107 s
```

## What changed from the named-motor run

The previous diagnostic UTD had semantic-looking output pools like `LATCH`, `STABLE`, `BOUNDARY`, and `COUPLING`.

This run uses selector operations plus anonymous lanes:

```text
operations:
  SELECT HOLD RELEASE INHIBIT ADVANCE RETREAT SPLIT MERGE
  AMPLIFY DAMP COMPARE CORRECT COMMIT ABORT

lanes:
  L0 L1 L2 L3 L4 L5 L6 L7
```

Void-walker contacts drive the operation and lane pools. Coactive operation/lane pressure updates a private articulation trace. The private trace is logged every tick in `trace_log.jsonl`. UTD emits only compact witness events like `W6_0014`; it does not emit the private trace string.

## Primary readable run summary

Source counts:

```text
curriculum:  227
reafference: 33
witnesses:   33
```

Witness lane distribution:

```text
{
  "L7": 3,
  "L6": 12,
  "L5": 8,
  "L0": 2,
  "L2": 5,
  "L4": 1,
  "L3": 2
}
```

Witness rate by input category:

```text
Q chart             11/57   rate=0.1930
B overlap            0/51   rate=0.0000
L boundary          11/50   rate=0.2200
overlap transfer    11/38   rate=0.2895
self_consequence     0/33   rate=0.0000
L cycle close        0/31   rate=0.0000
```

Top category-to-lane witness couplings:

```text
overlap transfer   -> L6  count=5
Q chart            -> L6  count=4
L boundary         -> L6  count=3
L boundary         -> L5  count=3
Q chart            -> L5  count=3
overlap transfer   -> L5  count=2
Q chart            -> L0  count=2
L boundary         -> L2  count=2
overlap transfer   -> L2  count=2
Q chart            -> L7  count=1
L boundary         -> L4  count=1
L boundary         -> L3  count=1
```

Top category operation/lane commands:

```text
L boundary         COMMIT   L6 count=37
Q chart            ADVANCE  L6 count=33
Q chart            ADVANCE  L5 count=31
overlap transfer   COMMIT   L6 count=30
B overlap          COMMIT   L6 count=28
Q chart            RELEASE  L6 count=28
overlap transfer   COMMIT   L2 count=26
B overlap          COMMIT   L5 count=25
L boundary         ADVANCE  L6 count=24
Q chart            RELEASE  L5 count=23
B overlap          ADVANCE  L6 count=23
B overlap          ADVANCE  L5 count=22
Q chart            COMMIT   L6 count=22
Q chart            SPLIT    L6 count=22
B overlap          COMMIT   L3 count=22
L cycle close      COMMIT   L6 count=20
B overlap          ADVANCE  L3 count=20
B overlap          RELEASE  L6 count=19
L boundary         COMMIT   L2 count=19
L boundary         RELEASE  L6 count=19
```

The readable run produced a private trace with repeated lane recruitment. The strongest witness rates were `overlap transfer` and `L boundary`; self-consequence did not dominate witness emission.

## Opaque companion summary

The opaque run preserved temporal/compositional structure while removing readable words:

```text
Q chart A              -> x7 m2 a0
B overlap AB           -> k4 r9 p1
L boundary AB          -> t6 h3 p1
overlap transfer AB BC -> r9 z5 p1 p2
L cycle close          -> t6 c8 q0
```

Source counts:

```text
curriculum:  233
reafference: 27
witnesses:   27
```

Witness lane distribution:

```text
{
  "L1": 16,
  "L7": 2,
  "L6": 3,
  "L5": 2,
  "L3": 2,
  "L2": 2
}
```

Witness rate by input category:

```text
Q chart              8/69   rate=0.1159
L boundary           5/46   rate=0.1087
overlap transfer     5/46   rate=0.1087
B overlap            4/44   rate=0.0909
L cycle close        5/28   rate=0.1786
self_consequence     0/27   rate=0.0000
```

Top category-to-lane witness couplings:

```text
L boundary         -> L1  count=4
overlap transfer   -> L1  count=4
B overlap          -> L1  count=4
Q chart            -> L1  count=2
L cycle close      -> L6  count=2
Q chart            -> L5  count=2
Q chart            -> L2  count=2
L cycle close      -> L1  count=2
Q chart            -> L7  count=1
L boundary         -> L3  count=1
L cycle close      -> L7  count=1
Q chart            -> L6  count=1
```

The opaque run shifted the dominant lane basin from L5/L6/L2 toward L1. The trace surface still produced witness events from a fresh state under the same grammar skeleton.

## Early readable IO window

See `runs/selector_trace_fresh_1k_current/first120_io.txt` for the first 120 ticks. The first 20 lines:

```text
000 [curriculum/Q chart] Q chart A -> RELEASE:L7 ADVANCE:L7 INHIBIT:L7 SELECT:L7 | WIT W7_0001
001 [reafference/self_consequence] heard witness W7_0001 -> RELEASE:L2 ABORT:L2 DAMP:L2 CORRECT:L2
002 [curriculum/Q chart] Q chart A -> SELECT:L1 ADVANCE:L1 CORRECT:L1 INHIBIT:L1
003 [curriculum/Q chart] Q chart A -> RELEASE:L0 ADVANCE:L0 MERGE:L0 ABORT:L0
004 [curriculum/B overlap] B overlap AB -> SELECT:L6 ADVANCE:L6 RELEASE:L6 AMPLIFY:L6
005 [curriculum/B overlap] B overlap AB -> ADVANCE:L5 RELEASE:L5 AMPLIFY:L5 COMMIT:L5
006 [curriculum/B overlap] B overlap AB -> ADVANCE:L7 DAMP:L7 SELECT:L7 RELEASE:L7
007 [curriculum/B overlap] B overlap AB -> COMMIT:L7 ADVANCE:L7 HOLD:L7 SPLIT:L7
008 [curriculum/L boundary] L boundary AB -> COMMIT:L0 COMPARE:L0 ADVANCE:L0 INHIBIT:L0 | WIT W6_0002
009 [reafference/self_consequence] heard witness W6_0002 -> SPLIT:L7 ADVANCE:L7 COMMIT:L7 ABORT:L7
010 [curriculum/L boundary] L boundary AB -> COMMIT:L4 ADVANCE:L4 MERGE:L4 RETREAT:L4
011 [curriculum/L boundary] L boundary AB -> COMMIT:L6 MERGE:L6 INHIBIT:L6 AMPLIFY:L6
012 [curriculum/Q chart] Q chart B -> COMMIT:L6 SPLIT:L6 RELEASE:L6 ADVANCE:L6
013 [curriculum/L boundary] L boundary AB -> MERGE:L6 COMMIT:L6 AMPLIFY:L6 ADVANCE:L6
014 [curriculum/Q chart] Q chart B -> COMMIT:L5 CORRECT:L5 RELEASE:L5 MERGE:L5
015 [curriculum/Q chart] Q chart B -> COMMIT:L2 ADVANCE:L2 AMPLIFY:L2 RELEASE:L2
016 [curriculum/overlap transfer] overlap transfer AB BC -> ADVANCE:L2 COMMIT:L2 DAMP:L2 ABORT:L2 | WIT W5_0003
017 [reafference/self_consequence] heard witness W5_0003 -> COMMIT:L5 ABORT:L5 SPLIT:L5 RELEASE:L5
018 [curriculum/overlap transfer] overlap transfer AB BC -> COMMIT:L2 SPLIT:L2 AMPLIFY:L2 ABORT:L2
019 [curriculum/B overlap] B overlap BC -> COMMIT:L5 RELEASE:L5 MERGE:L5 ADVANCE:L5

```

## Files to inspect first

```text
runs/selector_trace_fresh_1k_current/first120_io.txt
runs/selector_trace_fresh_1k_current/trace_log.jsonl
runs/selector_trace_fresh_1k_current/utd_events.jsonl
runs/selector_trace_fresh_1k_current/ute_input_stream.jsonl
runs/selector_trace_fresh_1k_current/tick_rows.csv
runs/selector_trace_fresh_1k_current/state_260.h5

runs/selector_trace_fresh_1k_current_opaque/first120_io.txt
runs/selector_trace_fresh_1k_current_opaque/trace_log.jsonl
runs/selector_trace_fresh_1k_current_opaque/utd_events.jsonl
runs/selector_trace_fresh_1k_current_opaque/ute_input_stream.jsonl
runs/selector_trace_fresh_1k_current_opaque/tick_rows.csv
runs/selector_trace_fresh_1k_current_opaque/state_260.h5
```

## Implementation notes

The selector trace is private motor control state. It is logged, not emitted.

The witness event is the UTD-side external action. When reafference is enabled, only the witness consequence returns through UTE as `heard witness ...`.

This keeps these layers separate:

```text
external UTE input
private selector trace
UTD witness event
UTE self-consequence of witness
```

## Where this points next

1. Sweep selector thresholds and cooldowns on the current-tick coactivation runner.
2. Add an offline trace-shape analyzer: lane persistence, release latency, category-conditioned lane reuse, and witness-after-input delay.
3. Run longer windows from the same fresh-start path once the slow-path boundary is handled.
4. Compare readable, opaque, and randomized-order streams using the same trace analyzer.
5. Replace text witness strings with a small device witness vocabulary or glyph surface after trace-shape behavior stabilizes.
