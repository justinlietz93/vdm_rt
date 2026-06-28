# intent_shuffle_probe

A permutation-control experiment to decide whether VDM's gravitation toward
restraint/stability is a real structure-coupled choice or a mirage.

## The question

In coherent/factual windows VDM gravitates toward a restrained, settled regime
(in the shipped `facts_then_questions` run, HOLD presence sits at ~0.54 during
factual exposure and collapses to ~0.06 under questions). Is that gravitation a
choice coupled to intact intent-handle structure, or does it show up regardless
of whether the handles are meaningfully wired?

## The control

Shuffle which neuron sits in which intent-handle slot. It is a pure relocation:
the same neuron locations, same values, only the slot->neuron assignment is
permuted (a forced derangement, so every handle genuinely moves). Nothing is
added, removed, or rescaled. Any behavioral change under the shuffle is therefore
attributable to structure, not to a changed population.

## The three tracks

```
track1  baseline                       0 .. 1500
track2  shuffled handles, whole run     0 .. 1500
track3  baseline 0 .. 1000, then shuffled 1000 .. 1500   (engine resume at 1000)
```

Track 3 is the strong one. It resumes from the exact baseline state at tick 1000
and changes only the handle assignment, so it holds history constant. The switch
is a within-subject control.

## The falsifier (decided in advance)

| observable under shuffle | MIRAGE predicts | COUPLED predicts |
|---|---|---|
| HOLD presence (restraint) | unchanged | drops |
| op-presence entropy (settledness) | unchanged | rises |
| gate-pressure variance | unchanged | rises |
| witness rate | unchanged | rises |
| stability_index (composite) | flat across track2 vs track1, no step at tick 1000 | lower in track2, steps down at tick 1000 |
| change-point tick (track3) | none / not near 1000 | localized at ~1000 |

MIRAGE: the stability profile is invariant to which neuron is which handle, so
the gravitation is not a structure-coupled choice (a readout aggregate or a
structure-independent attractor). COUPLED: shuffling degrades the stability the
system was holding, with a step at the manipulation tick.

## Why projection-independent observables

The verdict reads off raw engine output only: witness rate, gate_pressure and its
variance, op presence-fractions (HOLD = restraint, SELECT = attention, RELEASE /
ABORT = letting go), and op-presence entropy. No posture projection and no
reaching overlay feed the verdict, so the conclusion does not inherit any
uncalibrated mapping. (`op_HOLD_rate` here reproduces the
`summary_by_phase_kind.csv` scale: presence-fraction of the op in `active_ops`.)

## Validation

The change-point detector and verdict logic were validated on the real
`facts_then_questions` run, which has a genuine regime switch at tick 1000
(factual -> questions). The detector independently localized the change-point to
**tick 998**, the stability index stepped **-0.77**, bootstrap **p < 0.001**, and
the verdict read **coupled**. That is the positive control: when a true regime
step exists, the machinery finds it and calls it. Applied to the handle-shuffle
tracks, the same machinery returns MIRAGE if the shuffle produces no such step.

Note: that validation step uses a content switch as the manipulation, not a
handle shuffle. It proves the detector fires on a real step; it says nothing yet
about the handle question, which needs your three real tracks.

## Run it

```bash
# 0. confirm the handle-map representation, then sanity-check the control
python -m intent_shuffle_probe.permute_handles --self-test
python -m intent_shuffle_probe.permute_handles --in handle_map.json --seed 20260627

# 1. build + run the three tracks (drop --execute for a dry run plan)
python -m intent_shuffle_probe.run_tracks \
    --schedule <stimulus_schedule.jsonl> --out-root runs/intent_shuffle \
    --total-ticks 1500 --switch-tick 1000 --n-handles 64 --execute

# 2. verdict
python -m intent_shuffle_probe.analyze \
    --track1 runs/intent_shuffle/track1_baseline \
    --track2 runs/intent_shuffle/track2_full_shuffle \
    --track3 runs/intent_shuffle/track3_switch --switch-tick 1000
```

## Two contracts to confirm against your engine

1. Handle-map representation (`permute_handles.extract/inject`). Assumed to be an
   ordered `handle_locations[slot] = neuron_location` (list or `{slot: loc}`
   dict). If it is a matrix or a name->coord dict, adapt only those two functions.
2. Runner CLI (`run_tracks.run_one`). Assumed `runner --config <json>
   [--handle-perm <json>] [--resume <h5>]`. Adapt the argv to your
   `run_orthad_selector_trace.py` flags; the configs and the resume-at-switch
   logic are already built.

## A caution on the verdict

A shuffle that merely injects noise could raise overall activity without telling
you anything about the restraint *choice*. That is why the stability observables
are framed as restraint dominance and settledness (relative, not absolute
activity), and why track 3's within-subject step is the primary signal. If track2
and track3 disagree (full shuffle moves it but the mid-run switch does not, or
vice versa), the reading returns MIXED and you should inspect which observable
moved before concluding.

## Layout

```
intent_shuffle_probe/
  observables.py     projection-independent windowed observables
  analyze.py         change-point scan + bootstrap + three-track verdict
  permute_handles.py the relocation control (+ self-test, JSON in/out)
  run_tracks.py      three-track orchestrator (resume-at-switch for track 3)
```
