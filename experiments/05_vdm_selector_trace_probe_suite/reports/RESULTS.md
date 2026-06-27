# RESULTS - VDM Selector Trace Probe Suite

Fresh 1k VDM run with a selector-trace UTD layer. The run was intentionally kept at the current abstraction: anonymous lanes, selector operations, private trace metrics, sparse witness release. No prose decoder.

## Run configuration

```text
N = 1000
walkers = 1200
hops = 2
seed = 20260627
schedule_seed = 424242
ticks = 1400
ticks 0-999 = stable similar sentence curriculum
ticks 1000-1399 = mixed probe classes
release_threshold = 0.5
final_state = state_1400.h5
bursts = 26
rows = 1400
all_h5_reload_signatures_ok = True
```

## Probe classes

- `base_repeat`: original stable-world sentences after tick 1000.
- `paraphrase_same`: same general bridge/boundary/signal meaning, different words.
- `symbolic_inversion`: same symbol family, but relation changed or broken.
- `concrete_unrelated`: object-event scenes outside the bridge/boundary world.
- `social_affective`: social/agentive scenes outside the bridge/boundary world.

The model received only raw text. The class labels are outside-model metadata.

## Witness events

|   tick | kind               | input_id   | text                                              | witnesses   | release_lane   |   gate_pressure |   release_score |
|-------:|:-------------------|:-----------|:--------------------------------------------------|:------------|:---------------|----------------:|----------------:|
|      0 | base_stable        | B03        | The crossing waits until the boundary is steady.  | W5_0001     | L5             |          0.5596 |          0.2596 |
|    181 | base_stable        | B01        | The gate opens after the bridge holds.            | W0_0002     | L0             |          0.5803 |          0.0803 |
|    253 | base_stable        | B01        | The gate opens after the bridge holds.            | W4_0003     | L4             |          0.5631 |          0.1631 |
|    387 | base_stable        | B01        | The gate opens after the bridge holds.            | W1_0004     | L1             |          0.5498 |          0.3498 |
|    471 | base_stable        | B05        | The held path admits the next signal.             | W1_0005     | L1             |          0.5085 |          0.3085 |
|   1099 | concrete_unrelated | C05        | The orange peel curls beside the metal spoon.     | W2_0006     | L2             |          0.5688 |          0.2688 |
|   1139 | base_repeat        | B06        | The bridge marks the crossing and then releases.  | W5_0007     | L5             |          0.5529 |          0.1529 |
|   1179 | base_repeat        | B07        | The boundary holds while the signal moves across. | W3_0008     | L3             |          0.6161 |          0.4161 |
|   1191 | concrete_unrelated | C00        | The cup falls and shatters on the kitchen floor.  | W2_0009     | L2             |          0.7079 |          0.4079 |

Read: the stable phase produced 5 witnesses in 1000 ticks. The probe phase produced 4 witnesses in 400 ticks. Two probe witnesses came from concrete-unrelated sentences, and two came from base repeats after the probe mixture had already perturbed the posture.

## Trace distance by class

| phase             | kind               |   ticks |   witnesses |   witness_rate |   mean_dist_late |   median_dist_late |   mean_zdist_late |   mean_gate |   max_gate |   mean_release_score |   max_release_score |
|:------------------|:-------------------|--------:|------------:|---------------:|-----------------:|-------------------:|------------------:|------------:|-----------:|---------------------:|--------------------:|
| probe_mixture     | base_repeat        |     174 |           2 |         0.0115 |          31.4183 |            30.7063 |           10.6624 |     -0.2565 |     0.6161 |              -0.3444 |              0.4161 |
| probe_mixture     | concrete_unrelated |      51 |           2 |         0.0392 |          31.1733 |            28.6095 |           10.9738 |     -0.2494 |     0.7079 |              -0.3376 |              0.4312 |
| probe_mixture     | paraphrase_same    |      63 |           0 |         0.0000 |          29.7187 |            27.7487 |           10.8498 |     -0.2526 |     0.3291 |              -0.3335 |              0.2291 |
| probe_mixture     | social_affective   |      52 |           0 |         0.0000 |          30.7504 |            29.8864 |           10.5694 |     -0.2847 |     0.3210 |              -0.3616 |              0.2210 |
| probe_mixture     | symbolic_inversion |      60 |           0 |         0.0000 |          30.7465 |            29.8306 |           10.1545 |     -0.4172 |     0.2000 |              -0.4988 |              0.1338 |
| stable_curriculum | base_stable        |    1000 |           5 |         0.0050 |          24.2843 |            21.0514 |            7.8058 |     -0.3727 |     0.5803 |              -0.4525 |              0.4256 |

Read: trace distance is the movement of the full selector vector away from the stable-late centroid. It uses operation energy plus lane energy/hold/inhibit/release/correct. This is the main readout because witness release is sparse by design.

## Operation shifts against post-1000 base repeats

### paraphrase_same
| op      |    mean |   delta_vs_post_base |
|:--------|--------:|---------------------:|
| COMPARE | 24.4277 |               1.6850 |
| INHIBIT | 78.9927 |               1.4254 |
| MERGE   | 26.0768 |               1.3732 |
| AMPLIFY | 21.5989 |               0.5013 |
| HOLD    | 11.8351 |               0.1188 |
| DAMP    | 15.8462 |               0.0480 |
| RELEASE | 15.4761 |              -0.0602 |
| RETREAT | 20.1083 |              -0.1346 |

### symbolic_inversion
| op      |    mean |   delta_vs_post_base |
|:--------|--------:|---------------------:|
| MERGE   | 25.5847 |               0.8811 |
| INHIBIT | 78.3833 |               0.8160 |
| COMPARE | 23.4045 |               0.6618 |
| ADVANCE | 21.1177 |               0.3016 |
| DAMP    | 15.9739 |               0.1757 |
| COMMIT  | 14.6954 |              -0.1540 |
| HOLD    | 11.3843 |              -0.3320 |
| RETREAT | 19.9036 |              -0.3393 |

### concrete_unrelated
| op      |    mean |   delta_vs_post_base |
|:--------|--------:|---------------------:|
| MERGE   | 25.8427 |               1.1391 |
| COMMIT  | 15.3361 |               0.4868 |
| RETREAT | 20.7250 |               0.4821 |
| CORRECT | 16.7059 |               0.4508 |
| SPLIT   | 12.1201 |               0.4259 |
| ABORT   | 18.2868 |               0.3428 |
| INHIBIT | 77.8734 |               0.3061 |
| SELECT  | 19.0521 |               0.2450 |

### social_affective
| op      |    mean |   delta_vs_post_base |
|:--------|--------:|---------------------:|
| INHIBIT | 78.6416 |               1.0743 |
| CORRECT | 16.9918 |               0.7368 |
| SELECT  | 19.3076 |               0.5004 |
| SPLIT   | 12.1605 |               0.4663 |
| HOLD    | 12.1002 |               0.3839 |
| RETREAT | 20.3171 |               0.0742 |
| ABORT   | 17.8562 |              -0.0878 |
| COMPARE | 22.5102 |              -0.2325 |

## Initial interpretation

The stable field again settled into a high-inhibition, sparse-release posture. During the probe phase, concrete-unrelated sentences produced the clearest witness release in this run: `C05` at tick 1099 and `C00` at tick 1191, both on lane L2. That means the new object-event class found a release-capable lane path rather than merely raising diffuse pressure.

Paraphrases stayed close to the base control posture in outward behavior: no witnesses, with higher `COMPARE / INHIBIT / MERGE` relative to post-1000 base repeats. Symbolic inversions were especially restrained: no witnesses, lower gate pressure, and increased `MERGE / INHIBIT / COMPARE` relative to post-1000 base. Social/affective inputs raised `CORRECT / INHIBIT / SELECT / SPLIT` relative to post-1000 base, but stayed closed at the witness layer.

The useful signal is the split between trace movement and witness release: some classes move the control surface without opening the mouth. That is exactly why this layer is worth testing before moving up another abstraction.

## Files

- `data/input_sets.json`: exact input sets.
- `data/probe_schedule.jsonl`: exact tick schedule.
- `runs/semantic_probe_1k_1400_thr05/trace_log.jsonl`: per-tick selector trace including full state.
- `runs/semantic_probe_1k_1400_thr05/tick_rows.csv`: compact tick table.
- `runs/semantic_probe_1k_1400_thr05/witness_events.csv`: released witness events.
- `runs/semantic_probe_1k_1400_thr05/trace_distance_by_kind.csv`: class-level trace displacement.
- `runs/semantic_probe_1k_1400_thr05/op_energy_deltas_by_kind.csv`: operation shifts.
- `runs/semantic_probe_1k_1400_thr05/lane_metric_means_by_kind.csv`: lane metric means.
- `runs/semantic_probe_1k_1400_thr05/state_1400.h5`: retained final state plus selector continuation state.