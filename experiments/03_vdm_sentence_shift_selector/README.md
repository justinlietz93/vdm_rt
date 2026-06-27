# VDM sentence-shift selector-trace package

This package contains a fresh-state VDM selector-trace sentence experiment.

Main report: `reports/RESULTS.md`

Primary run:

`runs/sentence_shift_complete_300N_w360_h2_thr05_1049`

Important files:

- `data/input_sets.json` — sentence pools and schedule parameters
- `data/sentence_schedule.jsonl` — exact tick-by-tick input schedule
- `data/sentence_stream.txt` — raw text stream sent to receptor indices
- `scripts/run_sentence_shift_fast.py` — analysis runner variant
- `codebase/vdm_rt-main/` — copied VDM runtime codebase used for the package
- `codebase/orthad_tools/run_orthad_selector_trace.py` — selector-trace runner used for completed run
- `runs/.../tick_rows_annotated.csv` — tick-level input, telemetry, selector state, witness info
- `runs/.../utd_events_annotated.csv` — witness events annotated with sentence phase/kind/input id
- `runs/.../trace_log.jsonl` — private selector trace log
- `runs/.../first80_after_shift_annotated.txt` — readable shift-window IO trace
- `runs/.../state_1049.h5` — fresh model retained state after the completed run

Several attempted N=1000 runs are preserved under `runs/` as partial pilot windows.
