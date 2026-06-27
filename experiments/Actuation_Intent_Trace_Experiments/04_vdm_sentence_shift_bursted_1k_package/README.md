# VDM sentence-shift selector trace, bursted 1k run

This package contains a fresh-state VDM selector-trace sentence-shift run using stop/save/reload bursts.

## Core run

- `N=1000`
- `walkers=1200`
- `hops=2`
- `ticks=1200`
- ticks `0-999`: stable sentence curriculum
- ticks `1000-1199`: novel semantic sentences introduced into the random schedule
- release threshold: `0.5`
- no graph scans during tick loop
- H5 saved and reloaded at every burst boundary with state-signature verification

## Main files

- `reports/RESULTS.md`
- `data/input_sets.json`
- `data/sentence_schedule.jsonl`
- `runs/release05_final/tick_rows.csv`
- `runs/release05_final/trace_log.jsonl`
- `runs/release05_final/utd_events.jsonl`
- `runs/release05_final/ute_input_stream.jsonl`
- `runs/release05_final/state_1200.h5`
- `scripts/run_sentence_shift_burst_once.py`

## Resume method

Each burst loads the previous H5, restores the embedded runner state from `/sentence_runner/state_pickle_u8`, runs the next schedule segment, saves a new H5, reloads it into fresh runtime objects, and verifies the state signature before accepting the burst.
