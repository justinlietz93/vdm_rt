# Selector-trace control suite results

## Run purpose

This run tested whether the selector-trace behavior from the readable sentence experiment survives controls that alter the receptor surface.

Three schedules were compared:

1. **Readable semantic reference**: original English sentences.
2. **Opaque-token control**: same schedule and token structure, but every word was replaced with a deterministic opaque token such as `u108`.
3. **Shuffled-word control**: same words per sentence, but deterministic within-sentence word order shuffling.

Each control started from a fresh 1k VDM state and used bursted save/reload continuation.

Common settings:

```text
N = 1000
walkers = 1200
hops = 2
seed = 20260627
ticks = 1400
ticks 0-999 = stable similar sentence field
ticks 1000-1399 = probe mixture
release_threshold = 0.5
```

## Phase-level result

| Run | Phase | Ticks | Witness ticks | Witness rate | Mean gate pressure | Mean release score |
|---|---:|---:|---:|---:|---:|---:|
| readable_semantic | stable | 1000 | 5 | 0.0050 | -0.3727 | -0.4525 |
| readable_semantic | probe | 400 | 4 | 0.0100 | -0.2827 | -0.3672 |
| opaque_token | stable | 1000 | 119 | 0.1190 | 1.2889 | 1.0497 |
| opaque_token | probe | 400 | 49 | 0.1225 | 1.2527 | 1.0007 |
| shuffled_words | stable | 1000 | 64 | 0.0640 | 0.4724 | 0.3946 |
| shuffled_words | probe | 400 | 29 | 0.0725 | 0.3796 | 0.2961 |

## Post-1000 probe result

| Run | Kind | Ticks | Witness ticks | Witness rate | Mean distance from stable-late centroid | Top operation deltas versus base-repeat |
|---|---:|---:|---:|---:|---:|---|
| readable_semantic | base_repeat | 174 | 2 | 0.0115 | 29.28 | baseline |
| readable_semantic | concrete_unrelated | 51 | 2 | 0.0392 | 29.45 | MERGE +1.14; COMMIT +0.49; RETREAT +0.48; CORRECT +0.45; SPLIT +0.43 |
| readable_semantic | paraphrase_same | 63 | 0 | 0.0000 | 27.49 | COMPARE +1.69; INHIBIT +1.43; MERGE +1.37; AMPLIFY +0.50; HOLD +0.12 |
| readable_semantic | social_affective | 52 | 0 | 0.0000 | 28.69 | INHIBIT +1.07; CORRECT +0.74; SELECT +0.50; SPLIT +0.47; HOLD +0.38 |
| readable_semantic | symbolic_inversion | 60 | 0 | 0.0000 | 28.46 | MERGE +0.88; INHIBIT +0.82; COMPARE +0.66; ADVANCE +0.30; DAMP +0.18 |
| opaque_token | base_repeat | 174 | 21 | 0.1207 | 41.06 | baseline |
| opaque_token | concrete_unrelated | 51 | 5 | 0.0980 | 41.52 | COMPARE +0.89; AMPLIFY +0.72; CORRECT +0.41; ADVANCE +0.11; ABORT -0.04 |
| opaque_token | paraphrase_same | 63 | 8 | 0.1270 | 38.79 | RETREAT +1.35; COMPARE +1.27; CORRECT +0.72; AMPLIFY +0.30; MERGE +0.22 |
| opaque_token | social_affective | 52 | 11 | 0.2115 | 40.62 | AMPLIFY +0.81; RELEASE +0.51; MERGE +0.47; COMPARE +0.46; INHIBIT +0.36 |
| opaque_token | symbolic_inversion | 60 | 4 | 0.0667 | 39.78 | COMPARE +0.70; SELECT +0.26; RELEASE +0.14; AMPLIFY +0.07; RETREAT +0.05 |
| shuffled_words | base_repeat | 174 | 12 | 0.0690 | 40.56 | baseline |
| shuffled_words | concrete_unrelated | 51 | 3 | 0.0588 | 40.36 | ABORT +0.88; SELECT +0.40; ADVANCE +0.08; RETREAT +0.02; CORRECT -0.07 |
| shuffled_words | paraphrase_same | 63 | 4 | 0.0635 | 39.93 | CORRECT +0.93; HOLD +0.52; ADVANCE -0.00; COMMIT -0.07; ABORT -0.09 |
| shuffled_words | social_affective | 52 | 4 | 0.0769 | 38.98 | CORRECT +0.94; HOLD +0.79; SELECT +0.62; ADVANCE +0.46; COMPARE +0.43 |
| shuffled_words | symbolic_inversion | 60 | 6 | 0.1000 | 40.22 | ABORT +0.50; MERGE +0.48; HOLD +0.34; SPLIT +0.29; ADVANCE +0.28 |

## Witness lanes

Readable semantic reference:

```text
L5: 2
L1: 2
L2: 2
L0: 1
L4: 1
L3: 1
```

Opaque-token control:

```text
L0: 50
L1: 42
L4: 39
L7: 20
L3: 8
L6: 8
L2: 1
```

Shuffled-word control:

```text
L5: 71
L0: 10
L6: 6
L7: 4
L2: 1
L4: 1
```

## Interpretation

The controls changed the behavior strongly.

The readable sentence run stayed highly restrained. It formed a low-release posture where concrete-unrelated inputs produced the clearest witness releases after the probe phase began, while paraphrase, social/affective, and symbolic inversion mostly moved the trace without opening the mouth.

The opaque-token control became much more release-active. The same temporal schedule with opaque tokens produced a high witness rate throughout the stable phase and probe phase. That means recurrent symbolic surface structure alone can strongly drive the selector gate. The opaque run did not preserve the restrained readable posture.

The shuffled-word control landed between readable and opaque. It kept the same words but destroyed the original sentence order. It produced more witnesses than readable English and concentrated witness release heavily on L5. That suggests word recurrence without normal order creates a more persistent release-prone lane posture.

The strongest operational read is:

```text
readable English:
  restrained trace, sparse release, class-specific probe effects

opaque tokens:
  high release pressure, broad multi-lane witness activity

shuffled words:
  intermediate release, dominant L5 lane, order-damaged posture
```

This makes the selector-trace layer more useful, not less. It shows that the trace is sensitive to the receptor surface, not only to high-level class labels. The next step should keep the selector-trace architecture but tighten the UTE side so sentence controls separate token recurrence, word order, and semantic relation more cleanly.

## Most useful next tests

1. **Readable lowercase normalized control**: remove capitalization and punctuation without changing word order.
2. **Bag-of-words repeated control**: same words, fixed alphabetic order per sentence.
3. **Opaque isomorphic relation control**: replace semantic words with symbolic tags by role, not by arbitrary word ID.
4. **Class-balanced block design**: after tick 1000, present each probe class in short controlled blocks instead of random mixture.
5. **Trace correction rule upgrade**: make `CORRECT` actively delay release, increase compare window, and allow lane switching.

The immediate finding is that the readable sentence result is not reducible to “any repeated strings cause the same trace.” The opaque and shuffled controls produced different motor postures and very different witness rates.
