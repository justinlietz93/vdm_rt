# Orthad sensorimotor V3 exploration

Ran three complete 1k / 1200-walker windows with full UTE and UTD logs. Engine source was not edited; this runner uses the original VDM runtime objects and a fixed actuator-neuron readout.

## orthad_sensorimotor_logged_v3_1k_260

```json
{
  "neurons": 1000,
  "walkers": 1200,
  "ticks_completed": 260,
  "elapsed_s": 26.585775136947632,
  "mean_wall_tick_s": 0.1022529831299415,
  "source_counts": {
    "curriculum": 108,
    "reafference": 152
  },
  "motor_event_count": 153,
  "motor_by_primitive": {
    "LATCH": 22,
    "STABLE": 22,
    "BOUNDARY": 10,
    "PRESSURE": 12,
    "REQUEST": 12,
    "UNSTABLE": 21,
    "COUPLING": 13,
    "CYCLE": 8,
    "MARK": 6,
    "TRACE": 9,
    "PROJECTION_LOSS": 5,
    "WAIT": 5,
    "REJECT": 4,
    "ADMIT": 4
  },
  "scan_firewall": "passed"
}
```

### Category event rates

| category         |   ticks |   motor |   event_rate |   mean_vt |   mean_val |
|:-----------------|--------:|--------:|-------------:|----------:|-----------:|
| B overlap        |      17 |      15 |     0.882353 |   5.41707 |   0.581823 |
| L boundary       |      17 |      12 |     0.705882 |   5.44225 |   0.590139 |
| overlap transfer |      18 |      11 |     0.611111 |   5.41174 |   0.593536 |
| self consequence |     152 |      92 |     0.605263 |   5.33999 |   0.591766 |
| L cycle close    |      15 |       7 |     0.466667 |   5.37973 |   0.591464 |
| Q chart          |      41 |      16 |     0.390244 |   5.46563 |   0.568305 |

### First 40 IO events

```text
000 [curriculum] Q chart A
001 [curriculum] Q chart A
002 [curriculum] Q chart A
003 [curriculum] Q chart A
004 [curriculum] B overlap AB
005 [curriculum] B overlap AB -> LATCH
006 [reafference] motor feedback LATCH -> STABLE
007 [reafference] motor feedback STABLE
008 [curriculum] L boundary AB
009 [curriculum] Q chart B
010 [curriculum] L boundary AB -> BOUNDARY
011 [reafference] motor feedback BOUNDARY -> PRESSURE
012 [reafference] motor feedback PRESSURE
013 [curriculum] L boundary AB
014 [curriculum] Q chart B -> REQUEST
015 [reafference] motor feedback REQUEST -> UNSTABLE
016 [reafference] motor feedback UNSTABLE
017 [curriculum] overlap transfer AB BC -> LATCH
018 [reafference] motor feedback LATCH -> STABLE COUPLING
019 [reafference] motor feedback STABLE
020 [reafference] motor feedback COUPLING
021 [curriculum] L cycle close
022 [curriculum] B overlap BC -> CYCLE
023 [reafference] motor feedback CYCLE -> PRESSURE
024 [reafference] motor feedback PRESSURE
025 [curriculum] Q chart A
026 [curriculum] L boundary BC
027 [curriculum] Q chart C -> UNSTABLE
028 [reafference] motor feedback UNSTABLE -> MARK
029 [reafference] motor feedback MARK -> BOUNDARY LATCH
030 [reafference] motor feedback BOUNDARY -> STABLE
031 [reafference] motor feedback LATCH
032 [reafference] motor feedback STABLE
033 [curriculum] Q chart B
034 [curriculum] overlap transfer BC CA
035 [curriculum] overlap transfer BC CA -> TRACE PRESSURE
036 [reafference] motor feedback TRACE
037 [reafference] motor feedback PRESSURE -> REQUEST
038 [reafference] motor feedback REQUEST
039 [curriculum] L cycle close -> UNSTABLE PROJECTION_LOSS COUPLING
```

## orthad_external_only_logged_v3_1k_260

```json
{
  "neurons": 1000,
  "walkers": 1200,
  "ticks_completed": 260,
  "elapsed_s": 26.927533388137817,
  "mean_wall_tick_s": 0.10356743794221145,
  "source_counts": {
    "curriculum": 260
  },
  "motor_event_count": 170,
  "motor_by_primitive": {
    "LATCH": 21,
    "STABLE": 20,
    "BOUNDARY": 13,
    "COUPLING": 21,
    "REQUEST": 19,
    "TRACE": 16,
    "PRESSURE": 14,
    "UNSTABLE": 20,
    "MARK": 10,
    "PROJECTION_LOSS": 4,
    "REJECT": 3,
    "WAIT": 4,
    "CYCLE": 3,
    "ADMIT": 2
  },
  "scan_firewall": "passed"
}
```

### Category event rates

| category         |   ticks |   motor |   event_rate |   mean_vt |   mean_val |
|:-----------------|--------:|--------:|-------------:|----------:|-----------:|
| L boundary       |      50 |      41 |     0.82     |   5.50899 |   0.591549 |
| overlap transfer |      49 |      33 |     0.673469 |   5.50438 |   0.593403 |
| B overlap        |      51 |      33 |     0.647059 |   5.50182 |   0.58699  |
| Q chart          |      79 |      46 |     0.582278 |   5.53223 |   0.57959  |
| L cycle close    |      31 |      17 |     0.548387 |   5.53795 |   0.591886 |

### First 40 IO events

```text
000 [curriculum] Q chart A
001 [curriculum] Q chart A
002 [curriculum] Q chart A
003 [curriculum] Q chart A
004 [curriculum] B overlap AB
005 [curriculum] B overlap AB -> LATCH
006 [curriculum] B overlap AB -> STABLE
007 [curriculum] B overlap AB
008 [curriculum] L boundary AB
009 [curriculum] Q chart B
010 [curriculum] L boundary AB
011 [curriculum] L boundary AB
012 [curriculum] Q chart B
013 [curriculum] L boundary AB -> BOUNDARY
014 [curriculum] Q chart B -> COUPLING
015 [curriculum] Q chart B -> REQUEST
016 [curriculum] overlap transfer AB BC
017 [curriculum] overlap transfer AB BC -> TRACE LATCH PRESSURE
018 [curriculum] overlap transfer AB BC -> STABLE
019 [curriculum] B overlap BC
020 [curriculum] L cycle close
021 [curriculum] L cycle close
022 [curriculum] B overlap BC
023 [curriculum] L boundary BC -> UNSTABLE
024 [curriculum] Q chart A
025 [curriculum] Q chart A
026 [curriculum] L boundary BC -> MARK COUPLING
027 [curriculum] Q chart C
028 [curriculum] B overlap AB -> REQUEST
029 [curriculum] B overlap AB -> LATCH
030 [curriculum] Q chart C -> STABLE
031 [curriculum] overlap transfer AB BC
032 [curriculum] L boundary AB
033 [curriculum] Q chart B
034 [curriculum] overlap transfer BC CA -> TRACE
035 [curriculum] overlap transfer BC CA -> UNSTABLE
036 [curriculum] Q chart B
037 [curriculum] L boundary AB
038 [curriculum] B overlap CA -> COUPLING
039 [curriculum] L cycle close -> PRESSURE
```

## orthad_sensorimotor_logged_v3_1k_260_thr80

```json
{
  "neurons": 1000,
  "walkers": 1200,
  "ticks_completed": 260,
  "elapsed_s": 27.316470861434937,
  "mean_wall_tick_s": 0.10506335221804106,
  "source_counts": {
    "curriculum": 186,
    "reafference": 74
  },
  "motor_event_count": 75,
  "motor_by_primitive": {
    "LATCH": 21,
    "STABLE": 16,
    "UNSTABLE": 19,
    "COUPLING": 9,
    "REQUEST": 4,
    "TRACE": 4,
    "BOUNDARY": 2
  },
  "scan_firewall": "passed"
}
```

### Category event rates

| category         |   ticks |   motor |   event_rate |   mean_vt |   mean_val |
|:-----------------|--------:|--------:|-------------:|----------:|-----------:|
| overlap transfer |      39 |      17 |     0.435897 |   5.53998 |   0.593254 |
| L boundary       |      35 |      14 |     0.4      |   5.54336 |   0.589907 |
| B overlap        |      40 |      12 |     0.3      |   5.52968 |   0.58634  |
| Q chart          |      51 |      15 |     0.294118 |   5.57234 |   0.573001 |
| self consequence |      74 |      16 |     0.216216 |   5.54344 |   0.592505 |
| L cycle close    |      21 |       1 |     0.047619 |   5.58041 |   0.591551 |

### First 40 IO events

```text
000 [curriculum] Q chart A
001 [curriculum] Q chart A
002 [curriculum] Q chart A
003 [curriculum] Q chart A
004 [curriculum] B overlap AB
005 [curriculum] B overlap AB
006 [curriculum] B overlap AB
007 [curriculum] B overlap AB
008 [curriculum] L boundary AB
009 [curriculum] Q chart B
010 [curriculum] L boundary AB -> LATCH
011 [reafference] motor feedback LATCH
012 [curriculum] Q chart B
013 [curriculum] L boundary AB
014 [curriculum] Q chart B
015 [curriculum] Q chart B
016 [curriculum] overlap transfer AB BC
017 [curriculum] overlap transfer AB BC
018 [curriculum] overlap transfer AB BC -> STABLE
019 [reafference] motor feedback STABLE
020 [curriculum] L cycle close
021 [curriculum] L cycle close
022 [curriculum] B overlap BC -> LATCH
023 [reafference] motor feedback LATCH
024 [curriculum] Q chart A
025 [curriculum] Q chart A
026 [curriculum] L boundary BC
027 [curriculum] Q chart C
028 [curriculum] B overlap AB
029 [curriculum] B overlap AB
030 [curriculum] Q chart C -> UNSTABLE
031 [reafference] motor feedback UNSTABLE
032 [curriculum] L boundary AB
033 [curriculum] Q chart B
034 [curriculum] overlap transfer BC CA -> LATCH
035 [reafference] motor feedback LATCH -> COUPLING
036 [reafference] motor feedback COUPLING
037 [curriculum] L boundary AB
038 [curriculum] B overlap CA -> STABLE
039 [reafference] motor feedback STABLE
```

## Clean comparison

- Sensorimotor threshold 40: 260 ticks, 153 motor events, 108 curriculum ticks, 152 self-consequence ticks. B-overlap had the highest event rate at 0.882/event tick.

- External-only threshold 40: 260 ticks, 170 motor events, all curriculum ticks. L-boundary had the highest event rate at 0.820/event tick.

- Sensorimotor threshold 80: 260 ticks, 75 motor events. With a stricter mouth, overlap-transfer and L-boundary stayed above Q-chart and self-consequence by event rate.


Files to inspect first: each run has `first80_io.txt`, `io_timeline_slim.csv`, `tick_rows.csv`, `ute_input_stream.jsonl`, `utd_motor_events.jsonl`, and `run_summary.json`.
