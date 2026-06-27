# Sensory Occlusion Actuator Probe

## Purpose

Implemented a sensory occlusion actuator for the high-resolution UTE.

The intended behavior:

```text
AP_CLOSE held above threshold for more than one tick
  -> sensory occlusion increases

AP_CLOSE falls below threshold
  -> aperture reopens one notch per tick

closed/occluded state
  -> ordinary external receptor layers are heavily damped
  -> UTE emits a dark-field / occluded sensory signal
  -> time and VDM dynamics continue
```

This is not vision. It is a data-sense occlusion mechanism: the model can damp the data receptor surface without erasing time or internal dynamics.

## Implementation

Tool:

```text
tools/run_sensory_occlusion_probe.py
```

Main run:

```text
runs/smoke_1k_300_apmin2_priority
```

Parameters:

```text
N = 1000
walkers = 1200
walker:neuron ratio = 1.2
ticks = 300
phases:
  0-99    stable readable input
  100-199 noisy / missing-closure input
  200-299 return stable input
```

The UTE builds high-resolution receptor layers:

```text
whole
normalized whole
span / word
positioned span
shape
pair
char
punctuation
dark / occluded field
```

The aperture actuator groups are separate from the selector trace groups:

```text
AP_RELAX
AP_WHOLE
AP_SPAN
AP_PAIR
AP_POSITION
AP_CHAR
AP_PUNCT
AP_SHAPE
AP_WIDEN
AP_NARROW
AP_CLOSE
AP_OPEN
```

## Main result

The primary run completed cleanly:

```text
ticks completed: 300
elapsed: 26.534 s
mean tick: 0.08845 s
final H5: state_300.h5
```

Witness activity:

| phase | ticks | witnesses | witness rate |
|---|---:|---:|---:|
| stable | 100 | 5 | 0.05 |
| noisy_missing_closure | 100 | 7 | 0.07 |
| return_stable | 100 | 1 | 0.01 |

Aperture behavior:

```text
AP_CLOSE active ticks:        46
AP_CLOSE_CONFIRMED events:    7
AP_REOPEN_STEP events:        6
occlusion level 1 ticks:      6
occlusion level 2 ticks:      1
occlusion level 3 ticks:      0
```

So the sensory occlusion actuator did engage, but only briefly. It never reached full closed state in this short run.

## Occlusion events

The held-close rule triggered in all three phases, including noisy / missing-closure inputs:

```text
tick 001 stable                 AP_CLOSE_CONFIRMED -> occlusion 1
tick 002 stable                 AP_CLOSE_CONFIRMED -> occlusion 2
tick 003 stable                 AP_REOPEN_STEP     -> occlusion 0

tick 110 noisy_missing_closure  AP_CLOSE_CONFIRMED -> occlusion 1
tick 111 noisy_missing_closure  AP_REOPEN_STEP     -> occlusion 0

tick 127 noisy_missing_closure  AP_CLOSE_CONFIRMED -> occlusion 1
tick 128 noisy_missing_closure  AP_REOPEN_STEP     -> occlusion 0

tick 197 noisy_missing_closure  AP_CLOSE_CONFIRMED -> occlusion 1
tick 198 noisy_missing_closure  AP_REOPEN_STEP     -> occlusion 0

tick 274 return_stable          AP_CLOSE_CONFIRMED -> occlusion 1
tick 275 return_stable          AP_REOPEN_STEP     -> occlusion 0
```

Example noisy/missing-closure close events:

```text
tick 127: "The quote opens but never closes"
  AP_CLOSE_CONFIRMED
  level: char
  occlusion_level: 1

tick 197: "The quote opens but never closes"
  AP_CLOSE_CONFIRMED
  level: position
  occlusion_level: 1
```

## Aperture focus profile

Aperture resolution state spent most time in character / position / punctuation regions:

| aperture level | ticks |
|---|---:|
| char | 120 |
| position | 74 |
| punct | 57 |
| pair | 34 |
| span | 13 |
| whole | 2 |
| relaxed | 0 |

This smoke run therefore shows that the model used the aperture actuator surface. It did not stay at relaxed default.

## Calibration runs

Two calibration runs are included:

```text
runs/smoke_1k_300
  aperture_current_min = 1
  too permissive: many aperture groups active; AP_CLOSE constantly conflicted with AP_OPEN/AP_RELAX

runs/smoke_1k_300_apmin4
  aperture_current_min = 4
  stricter: model used resolution aperture but no sustained AP_CLOSE confirmation

runs/smoke_1k_300_apmin2_priority
  aperture_current_min = 2
  useful smoke setting: AP_CLOSE confirmed 7 times, reopened correctly, resolution aperture remained active
```

## Read

The sensory occlusion mechanism works mechanically:

```text
held AP_CLOSE -> occlusion increases
close pressure drops -> aperture reopens one notch
dark-field layer becomes available during occlusion
ordinary receptor layers are damped during occlusion
```

The model did actuate the occlusion path in the live run. The short 300-tick window showed brief occlusion pulses rather than sustained closure. That is actually a reasonable first behavior: it blinked/damped rather than staying closed.

The resolution aperture surface was more active than the close surface. The model drifted strongly toward char / position / punctuation receptor layers, especially under the mixed stable/noisy/missing-closure schedule.

## Next better test

The next run should be longer and should not judge the close actuator only by full closure. Track:

```text
AP_CLOSE pressure
AP_CLOSE_CONFIRMED pulses
occlusion_level duration
whether occlusion suppresses witness bursts
whether missing-closure inputs raise AP_CHAR/AP_PUNCT/AP_CLOSE together
whether return-stable inputs reduce occlusion and witness rate
```

A useful next protocol:

```text
N = 1000
walkers = 1200
burst = 300 ticks
total = 1800 or 3600 ticks
phases:
  stable readable
  noisy/opaque
  missing quote/bracket closure
  return stable
```
