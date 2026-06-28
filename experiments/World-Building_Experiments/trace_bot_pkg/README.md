# Trace-conditioned deterministic bot comparison suite

This package tests whether the VDM intent trace carries usable control information.

It is a thin experiment overlay. It does **not** bundle a copy of `vdm_rt-main`. Run it against your current official repo.

## What it runs

Six separate matched runs from the same initial setup:

```text
no_return_control
  true fused translations are logged only
  no returned self-output

true_phrase_return
  current true fused translation is returned as reafference

bot_matched_trace
  current true fused translation drives the deterministic bot
  bot reply is returned as reafference

bot_lagged_trace
  deterministic bot receives the true fused trace from N witness events ago
  default lag = 50 witness events

anti_trace_return
  corrected signed-centered anti-vector phrase is returned

bot_yoked_replay
  replays the exact bot reply stream from bot_matched_trace
  but does not use the current run's trace
```

The key comparison is:

```text
bot_matched_trace vs bot_lagged_trace vs bot_yoked_replay
```

If matched beats lagged and yoked, that is stronger evidence that the current trace carries live control information. Yoked replay controls for reply inventory and wording.

## No warmup exclusion

The runner does not discard early ticks. Reports include whole-run and windowed summaries. Early formation is kept as evidence.

## Setup

From inside this package:

```bash
./setup_env.sh
```

## Run against your live repo

Example if your repo is at `~/git/vdm_rt`:

```bash
./run_trace_bot_3000.sh ~/git/vdm_rt
```

Or manually:

```bash
venv/bin/python tools/run_trace_conditioned_bot_suite.py \
  --reset \
  --run \
  --repo ~/git/vdm_rt \
  --suite-dir runs/trace_conditioned_bot_3000 \
  --ticks-total 3000 \
  --tick-print-stride 10 \
  --live-topn 5
```

Longer run:

```bash
./run_trace_bot_5000.sh ~/git/vdm_rt
```

## Output reports

Reports are written to:

```text
runs/trace_conditioned_bot_3000/reports/
```

Important files:

```text
RESULTS.md
condition_summary.csv
window_summary.csv
event_translation_log.csv
bot_interaction_log.csv
topk_true_vs_emitted.csv
next_window_effects.csv
```

Send back either the reports directory or the whole suite zip:

```bash
zip -r trace_conditioned_bot_results.zip runs/trace_conditioned_bot_3000
```

## Live terminal output

The runner prints witness events and tick telemetry. Use `--tick-print-stride 10` or `--tick-print-stride 25` to reduce noise. Witness ticks always print.

## Notes

- `bot_yoked_replay` must run after `bot_matched_trace`; the runner order handles this.
- `bot_lagged_trace` uses `--bot-event-lag 50` by default.
- `anti_trace_return` uses the corrected signed-centered anti-vector selector.
- The deterministic bot is not an LLM. It is a fixed rule surface mapping trace family to reply/action/aperture/stimulus hints.
