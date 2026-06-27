# 2048 Reafferent Index Accumulated-Word Smoke Test

This corrects the previous smoke test.

The translator input is not independent row snapshots and not a generic window summary.
For each witness event, the system constructs one accumulated intent word across the entire inter-witness interval:

```text
previous witness reset
for each tick until current witness:
    tick_delta = local trace posture stroke
    intent_word = retain * intent_word + tick_delta
at witness tick:
    intent_word += trigger contribution
    query 2048 utterance index
    emit top-1 utterance
    log top-k candidates
```

This matches the requested Phase Calculus/QBL-style accumulation: the word is built every tick and sampled at the actuator witness.

## Outputs

- `all_witness_accum_word_translation.csv` — one row per witness event.
- `all_witness_accum_word_topk.csv` — top-8 candidates per witness.
- `selected_example_outputs.csv` — compact examples.
- `selected_example_details.json` — includes final axis vector and tail of accumulated tick-word evolution.
- `summary_top1_family_counts.csv`
- `summary_top1_family_by_branch.csv`
- `summary_by_run.csv`
- `projection_accum_word_experimental.py` — runnable implementation.

## Tested scope

- Runs: 16
- Witness events: 556
- Index: 2048 first-person domain-agnostic utterances, 64 axes

## Runtime note

The current projection weights are experimental. The important correction is architectural: every tick contributes to an accumulating word; the witness trigger samples the completed word.
