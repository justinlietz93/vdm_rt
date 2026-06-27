# VDM selector-trace sentence shift run

## Question

Run a fresh VDM selector-trace model on a small set of sentences whose symbolic/semantic meaning is similar, then begin introducing a couple semantically different sentences after tick 1000.

## Input schedule

Seed: `20260627`

Stable curriculum, ticks `0..999`, randomly sampled from eight related sentences:

1. The bridge holds while the signal crosses.
2. The gate opens after the bridge holds.
3. A stable boundary lets the signal pass.
4. The crossing waits until the boundary is steady.
5. A latch keeps the path stable before transfer.
6. The held path admits the next signal.
7. The bridge marks the crossing and then releases.
8. The boundary holds while the signal moves across.

Shift curriculum begins at tick `1000`, using the same base sentence pool plus two novel sentences sampled with probability `0.25`:

1. The cup falls and shatters on the kitchen floor.
2. A child laughs beside a sleeping dog.

The raw sentence text was sent as receptor-side input. Metadata such as `base`, `novel`, `phase`, and `input_id` was only logged outside the model.

## Completed run used for the analysis

Path: `runs/sentence_shift_complete_300N_w360_h2_thr05_1049`

Runtime shape:

```text
N = 300
walkers = 360
hops = 2
seed = 20260627
ticks completed = 1049
stable ticks = 1000
shift ticks observed = 49
novel-shift ticks observed = 11
selector release threshold = 0.5
fresh model state = yes
final H5 = state_1049.h5, 22 KB
```

The completed N=300 run is the clean analyzed run. I also attempted N=1000 runs; those reached stable-curriculum partial windows before the container slowed heavily. They are included under `runs/` as pilot data.

## High-level rates

| group | ticks | witnesses | witness rate | mean gate pressure | mean release score | mean VT coverage | mean VT entropy | mean SIE-v2 valence |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| stable semantic curriculum | 1000 | 115 | 0.1150 | 0.7041 | 0.5530 | 0.5798 | 4.2721 | 0.6176 |
| introduced semantic shift | 49 | 6 | 0.1224 | 0.7453 | 0.5902 | 0.6069 | 4.3791 | 0.6079 |
| base sentences overall | 1038 | 119 | 0.1146 | 0.7036 | 0.5527 | 0.5810 | 4.2761 | 0.6172 |
| novel-shift sentences | 11 | 2 | 0.1818 | 0.9303 | 0.7394 | 0.5924 | 4.3707 | 0.6086 |

The shift sentences raised gate pressure and release score more clearly than they raised raw witness count. The most interesting signal in this run is therefore not only “more output,” but stronger pre-release pressure in the selector trace.

## Input-level witness rates

| input | ticks | witnesses | rate |
|---|---:|---:|---:|
| B00 — The bridge holds while the signal crosses. | 114 | 11 | 0.0965 |
| B01 — The gate opens after the bridge holds. | 122 | 9 | 0.0738 |
| B02 — A stable boundary lets the signal pass. | 126 | 19 | 0.1508 |
| B03 — The crossing waits until the boundary is steady. | 147 | 21 | 0.1429 |
| B04 — A latch keeps the path stable before transfer. | 131 | 13 | 0.0992 |
| B05 — The held path admits the next signal. | 132 | 18 | 0.1364 |
| B06 — The bridge marks the crossing and then releases. | 131 | 14 | 0.1069 |
| B07 — The boundary holds while the signal moves across. | 135 | 14 | 0.1037 |
| N00 — The cup falls and shatters on the kitchen floor. | 4 | 0 | 0.0000 |
| N01 — A child laughs beside a sleeping dog. | 7 | 2 | 0.2857 |

Within the stable sentence family, the two strongest witness rates were the explicit boundary / steady-boundary sentences:

```text
A stable boundary lets the signal pass.        0.1508
The crossing waits until the boundary is steady. 0.1429
```

## Selector distribution shift

Stable base curriculum top active ops:

```text
DAMP, CORRECT, COMPARE, RETREAT, MERGE, SPLIT, SELECT, ADVANCE, COMMIT, RELEASE
```

Novel-shift ticks top active ops:

```text
COMPARE, CORRECT, DAMP, RETREAT, AMPLIFY, COMMIT, MERGE, ADVANCE, ABORT, SELECT, RELEASE
```

The novel shift did not create a totally new op alphabet. It changed pressure inside the existing selector surface. The most visible change was higher `AMPLIFY / COMMIT / ABORT` presence in the novel ticks and stronger release pressure.

Stable witness lanes:

```text
L0: 26
L6: 23
L1: 21
L3: 13
L5: 11
L7: 8
L2: 7
L4: 6
```

Shift-base witness lanes:

```text
L2: 1
L3: 1
L0: 1
L1: 1
```

Novel-shift witness lanes:

```text
L1: 1
L4: 1
```

The stable curriculum concentrated witness release mostly through L0/L6/L1. The first novel windows emitted through L1/L4 while raising gate pressure across several lanes.

## First shift ticks

See `first80_after_shift_annotated.txt` for the readable tick-by-tick trace after tick 1000.

The first novel sentence appears immediately at tick 1002:

```text
1002 [introduced_semantic_shift/novel_shift/N01]
A child laughs beside a sleeping dog.
-> ... | WIT W1_0116
```

The first cup/shatter sentence appears at tick 1003 and produces high gate pressure across subsequent repeats, with no witness in the small observed sample:

```text
N00 mean gate pressure = 1.1222
N00 mean release score = 0.8972
N00 witnesses = 0 / 4
```

That pattern is useful: novelty can raise pre-release pressure without immediately releasing a witness.

## Read

This run makes the selector-trace idea more useful than the named-primitive mouth for this kind of test.

The named Orthad mouth made the model's reaction symbolically legible right away. The selector trace instead shows a physiology-like control surface: `COMPARE / CORRECT / DAMP / RETREAT` became dominant across the stable curriculum, and novel sentences moved the release pressure without needing a hand-labeled semantic output primitive.

The important place to look next is the trace vector before emission:

```text
gate_pressure
release_score
lane distribution
operation distribution
witness lane
latency from input to witness
```

The sentence shift appears first as a pressure/trace change, then sometimes as a witness. That is a better motor-learning target than trying to make the output label itself carry the meaning.
