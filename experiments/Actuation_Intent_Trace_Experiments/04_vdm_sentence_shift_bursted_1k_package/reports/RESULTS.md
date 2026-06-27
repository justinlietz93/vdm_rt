# Results: bursted 1k sentence-shift selector-trace run

## Run identity

```text
fresh model state
N = 1000
walkers = 1200
hops = 2
ticks = 1200
release_threshold = 0.5
stable curriculum = ticks 0-999
introduced semantic shift = ticks 1000-1199
```

Inputs were raw sentence strings mapped deterministically to receptor indices. The stable set used sentences with closely related symbolic/semantic structure around bridge, boundary, signal, crossing, latch, transfer, release, and path stability. After tick 1000, two semantically different sentences were introduced into the random schedule:

```text
The cup falls and shatters on the kitchen floor.
A child laughs beside a sleeping dog.
```

The model did not receive the metadata labels. Labels are only in the logs.

## Burst integrity

The run was executed through repeated stop/save/reload bursts. Every accepted burst performed:

```text
run segment
save H5
embed continuation state into H5
build fresh runtime objects
load H5
restore embedded continuation state
compare state signature
continue only if signatures match
```

Result:

```text
rows = 1200
UTD witness events = 13
all_h5_reload_signatures_ok = true
final H5 = runs/release05_final/state_1200.h5
```

## Phase summary

```text
stable_semantic_curriculum:
  ticks = 1000
  witnesses = 12
  mean_gate_pressure = -0.2624
  max_gate_pressure = 1.3262
  mean_release_score = -0.3459
  max_release_score = 1.0262

introduced_semantic_shift:
  ticks = 200
  witnesses = 1
  mean_gate_pressure = -0.2499
  max_gate_pressure = 0.5178
  mean_release_score = -0.3376
  max_release_score = 0.2773
```

## Novel sentence summary

```text
novel_shift inputs:
  ticks = 57
  witnesses = 0
  mean_gate_pressure = -0.3032
  max_gate_pressure = 0.3920
  mean_release_score = -0.3996
  max_release_score = 0.2253
```

The novel sentences did not produce immediate witness release in this run. They did change selector physiology: compared with the stable phase, the introduced-shift window increased MERGE and CORRECT operation rates while lowering COMMIT, AMPLIFY, and DAMP.

## Operation-rate shift

Rates are operation appearances per tick.

```text
introduced_semantic_shift - stable_semantic_curriculum:
  MERGE    +0.161
  CORRECT  +0.124
  RETREAT  +0.057
  INHIBIT  +0.054
  COMPARE  +0.047
  RELEASE  +0.015
  SELECT   +0.009
  SPLIT    +0.005
  ADVANCE  -0.012
  HOLD     -0.021
  ABORT    -0.023
  COMMIT   -0.027
  AMPLIFY  -0.030
  DAMP     -0.038
```

Novel-only ticks showed the same basic direction against base ticks:

```text
novel_shift - base:
  MERGE    +0.260
  CORRECT  +0.077
  ADVANCE  +0.064
  INHIBIT  +0.052
  RETREAT  +0.035
  COMPARE  +0.028
  RELEASE  +0.021
  ABORT    +0.020
  DAMP     -0.072
  AMPLIFY  -0.073
```

## Witness examples

The stable curriculum produced 12 witnesses before the semantic shift and 1 witness after the shift began. Witnesses came from base sentences, mostly boundary/crossing/latch/path inputs.

Examples:

```text
tick 14
input: The crossing waits until the boundary is steady.
witness: W0_0001
commands: RELEASE:L0 INHIBIT:L0 COMMIT:L0 ...

tick 285
input: A stable boundary lets the signal pass.
witness: W5_0004
commands: SPLIT:L5 HOLD:L5 ADVANCE:L5 RELEASE:L5 ...

tick 538
input: The boundary holds while the signal moves across.
witness: W0_0006
commands: RELEASE:L0 COMMIT:L0 INHIBIT:L0 ADVANCE:L0 ...

tick 1077
input: A latch keeps the path stable before transfer.
witness: W1_0013
commands: INHIBIT:L0 ABORT:L0 RELEASE:L0 RETREAT:L0 ...
```

## Read

The bursted 1k selector-trace run shows a quieter but more physiologically useful output path than the named Orthad actuator mouth. The useful signal is not only witness count. It is the trace response before witness release.

The stable sentence curriculum formed occasional release events around boundary/crossing/latch/path sentences. When semantically different sentences entered the stream, the selector manifold shifted toward MERGE/CORRECT/RETREAT/INHIBIT/COMPARE while suppressing the stronger release/witness pattern. That is a useful response shape for this test: novelty disturbed the trace and changed control physiology without immediately becoming public output.
