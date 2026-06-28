# VDM Pal-World Conversation Harness

This package is the cleaned-up version of the trace-conditioned conversation idea.

It is **not** a mirror bot, not a terminal action-code graph, and not a final VDM mouth. It is a small deterministic educational/exploratory world with a friendly guide. The guide has its own weak preferences, topic momentum, persona inertia, and curiosity agenda. VDM's witness event can steer it, but cannot puppet it.

## What it tests

Can VDM's current witness/trace posture bias the kind of input it receives next?

The guide can move among:

- small teaching
- story analogy
- supportive big-brother mode
- gentle challenge
- innocent hard questions
- topic continuation
- soft topic pivot
- repair/simplification

The important comparison is not whether the guide is smart. It is whether `pal_live` creates a different VDM trajectory than `pal_static` or `pal_yoked`.

## Modes

```text
pal_live
  Uses current VDM witness event, selector/aperture traces, top-k families, ops, aperture commands, and recent guide state.

pal_static
  Uses the same response bank but follows a mostly fixed topic progression.

pal_yoked
  Replays the pal_live response stream from another run with an offset.
```

## Run

```bash
./run_pal_world_300.sh /path/to/vdm_rt runs/pal_world_300
```

Longer:

```bash
./run_pal_world_1500.sh /path/to/vdm_rt runs/pal_world_1500
```

## Output files

Each run folder contains:

```text
tick_rows.csv
intent_translation_events.jsonl
topk_true_vs_emitted.jsonl
bot_packets.jsonl
utd_events.jsonl
ute_input_stream.jsonl
ute_aperture_state.jsonl
```

`bot_packets.jsonl` keeps the Pal-World choice metadata:

```text
reply_text
topic
persona
topic_momentum
persona_momentum
response_class
model_output_category
op_posture
query_terms
top_response_ids
```

## Design constraints

- The guide has inertia. It does not instantly switch topics from one trace.
- The guide has mild preferences. It likes books, stories, examples, bridges, patterns, and gentle questions.
- It avoids exact repeats.
- It does not return terminal action-code prose.
- It does not paraphrase VDM's trace back at every turn.
- It asks innocent hard questions occasionally, not constantly.
- It lowers pressure when guardedness/restraint/uncertainty rises.

## First inspection target

Start with a short run and inspect about 20 witness turns:

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path('runs/pal_world_300/pal_live/bot_packets.jsonl')
for i, line in enumerate(p.read_text().splitlines()[:20]):
    r = json.loads(line)
    b = r['bot_packet']
    print(r['tick'], b['topic'], b['persona'], b['response_class'], '::', b['reply_text'])
PY
```

## v2 conversational guide update

This update makes the guide less terse and less interrogative.

Changes:

- Replies are now usually explanatory mini-turns, not one-line action labels.
- The guide has stronger teaching/story/opinion bias.
- Innocent hard questions exist, but are cooled down and not asked every turn.
- Short pithy responses are penalized in selection.
- The live guide keeps topic momentum instead of instantly laying on top of VDM's current trace.
- The package includes a tested 120-tick VDM smoke run report generated from `/mnt/data/vdm_recon/vdm_rt`.

Quick smoke check used here:

```bash
PYTHONPATH=src pytest -q
PYTHONPATH=src:/mnt/data/vdm_recon python tools/run_trace_conditioned_bot_suite_core.py \
  --suite-dir /mnt/data/pal_world_v2_test \
  --repo /mnt/data/vdm_recon/vdm_rt \
  --intent-index-dir index \
  --reset --init --ticks-total 120 --burst-ticks 120 --tick-print-stride 40 --live-topn 2
PYTHONPATH=src:/mnt/data/vdm_recon python tools/run_trace_conditioned_bot_suite_core.py \
  --suite-dir /mnt/data/pal_world_v2_test --next-burst-run pal_live
PYTHONPATH=src:/mnt/data/vdm_recon python tools/run_trace_conditioned_bot_suite_core.py \
  --suite-dir /mnt/data/pal_world_v2_test --next-burst-run pal_static
PYTHONPATH=src:/mnt/data/vdm_recon python tools/run_trace_conditioned_bot_suite_core.py \
  --suite-dir /mnt/data/pal_world_v2_test --next-burst-run pal_yoked
```
