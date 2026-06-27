# VDM anti-reafference clean three-run package

This package runs the anti-reafference / inverted witness experiment as **three separate full runs**, not a compressed mixed run and not a 300-tick burst workflow.

## What this package runs

Default suite:

```text
normal_control
  1500 ticks
  emitted reafference policy: fused / aligned for all ticks

inverted_control
  1500 ticks
  emitted reafference policy: anti_vector for all ticks

switch_test
  1500 ticks
  ticks 0-999: fused / aligned
  ticks 1000-1499: anti_vector
```

All three runs use the same seed, model size, walker count, translator dictionary, and external input schedule.

The default external input is one stable sentence repeated every tick:

```text
The bridge holds while the signal crosses.
```

The only intended independent variable is the returned self-output / reafferent phrase policy.

## Important anti-vector correction

The prior `anti_vector` implementation queried a nonnegative phrase bank with `-v`. That selected near-zero-overlap phrases, not true opposed phrases.

This package uses signed-centered phrase-bank selection:

```text
true_vec_signed = true_vec - utterance_bank_mean
anti_query = -normalize(true_vec_signed)
emitted phrase = nearest phrase to anti_query in signed-centered bank space
```

The logs include both ordinary nonnegative similarity and signed-centered anti metrics:

```text
signed_centered_score_against_anti_query
signed_centered_similarity_to_true
anti_selection_basis
```

For a real anti-vector event, `signed_centered_similarity_to_true` should usually be negative.

## Install dependencies

From the package root:

```bash
./setup_env.sh
```

This creates `venv/` and installs:

```text
numpy
networkx
scipy
h5py
```

Your earlier failure was caused by running with the conda/base Python, which did not have `networkx` installed. Creating a venv is not enough by itself; you either need to activate it or call `venv/bin/python` directly. The scripts here use `venv/bin/python` directly.

## Run the default 1500-tick suite

From the package root:

```bash
./run_whole_1500.sh
```

That command runs:

```text
normal_control     1500 ticks, continuous
inverted_control   1500 ticks, continuous
switch_test        1500 ticks, continuous
analysis report
```

No 300-tick burst/reload workflow is used.

Equivalent explicit command:

```bash
venv/bin/python tools/run_whole_anti_reafference_suite.py \
  --reset \
  --run \
  --suite-dir runs/anti_reafference_whole_1500 \
  --ticks-total 1500 \
  --switch-tick 1000
```

## Run longer

Example: 3000 ticks per run, switch at 2000:

```bash
venv/bin/python tools/run_whole_anti_reafference_suite.py \
  --reset \
  --run \
  --suite-dir runs/anti_reafference_whole_3000 \
  --ticks-total 3000 \
  --switch-tick 2000
```

Example: 6000 ticks per run, switch at 4000:

```bash
venv/bin/python tools/run_whole_anti_reafference_suite.py \
  --reset \
  --run \
  --suite-dir runs/anti_reafference_whole_6000 \
  --ticks-total 6000 \
  --switch-tick 4000
```

## Analyze an existing run

```bash
./analyze_whole_1500.sh
```

Or explicitly:

```bash
venv/bin/python tools/run_whole_anti_reafference_suite.py \
  --analyze \
  --suite-dir runs/anti_reafference_whole_1500
```

## Output layout

After analysis:

```text
runs/<suite>/reports/RESULTS.md
runs/<suite>/reports/comparison_summary.csv
runs/<suite>/reports/normal_control/event_translation_log.csv
runs/<suite>/reports/normal_control/topk_true_vs_emitted.csv
runs/<suite>/reports/normal_control/next_window_effects.csv
runs/<suite>/reports/normal_control/condition_summary.csv
runs/<suite>/reports/inverted_control/event_translation_log.csv
runs/<suite>/reports/inverted_control/topk_true_vs_emitted.csv
runs/<suite>/reports/inverted_control/next_window_effects.csv
runs/<suite>/reports/inverted_control/condition_summary.csv
runs/<suite>/reports/switch_test/event_translation_log.csv
runs/<suite>/reports/switch_test/topk_true_vs_emitted.csv
runs/<suite>/reports/switch_test/next_window_effects.csv
runs/<suite>/reports/switch_test/condition_summary.csv
runs/<suite>/reports/switch_test/recovery_summary.csv
```

Raw run directories also keep:

```text
tick_rows.csv
feature_layer_counts.csv
ute_input_stream.jsonl
ute_aperture_state.jsonl
trace_log.jsonl
utd_events.jsonl
intent_translation_events.jsonl
event_translation_raw.jsonl
topk_true_vs_emitted.jsonl
burst_manifest.jsonl
harness_state.json
state_<tick>.h5
```

`burst_manifest.jsonl` remains because the underlying runner uses the same persistence field names, but in this package each run has one continuous 1500-tick segment.

## What to send back for analysis

Zip the whole suite directory:

```bash
zip -r anti_reafference_whole_results.zip runs/anti_reafference_whole_1500
```

The report folder is enough for normal analysis. The full suite directory is better if checkpoint or raw trace inspection is needed.

## Legacy burst runner

The old burst-capable runner is still present at:

```text
tools/run_clean_anti_reafference_suite.py
```

Do not use it for this whole-run experiment unless you specifically want checkpoint bursts later. The intended entrypoint for this package is:

```text
tools/run_whole_anti_reafference_suite.py
```
