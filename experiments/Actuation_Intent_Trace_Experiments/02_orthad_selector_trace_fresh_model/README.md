# Orthad selector-trace fresh-model experiment

This package contains a full runnable VDM-RT codebase copy, the selector-trace runner, fresh-model run data, and a results report.

Run entrypoint:

```bash
python codebase/orthad_tools/run_orthad_selector_trace.py \
  --repo codebase/vdm_rt-main \
  --run-dir runs/selector_trace_fresh_1k \
  --neurons 1000 --walkers 1200 --ticks 260 \
  --curriculum rich --reafference --save-h5
```

The runner starts from a fresh `SparseConnectome` state with the configured seed. It does not edit VDM engine source files.

Key logs:

- `runs/selector_trace_fresh_1k/ute_input_stream.jsonl`
- `runs/selector_trace_fresh_1k/trace_log.jsonl`
- `runs/selector_trace_fresh_1k/utd_events.jsonl`
- `runs/selector_trace_fresh_1k/io_timeline.jsonl`
- `runs/selector_trace_fresh_1k/tick_rows.csv`
- `runs/selector_trace_fresh_1k/state_260.h5`
- `reports/RESULTS.md`


## Primary completed runs

- `runs/selector_trace_fresh_1k_current`
- `runs/selector_trace_fresh_1k_current_opaque`

See `reports/RESULTS.md`.
