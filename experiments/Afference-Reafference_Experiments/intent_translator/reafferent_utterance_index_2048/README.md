# Reafferent Utterance Index 2048

This package is a domain-agnostic first-person utterance index for translating a dense witness-window trace composite into one emitted reafferent phrase.

It is designed for this runtime shape:

```text
trace rows since previous witness
→ recency-weighted posture64_v1 axis vector
→ cosine search over 2048 first-person utterances
→ emit top-1 utterance
→ quietly log top-k candidates + distance + source witness/window
```

The model-facing output is only the utterance, for example:

```text
I recognize this.
```

The index does not emit internal mechanics like `SELECT RELEASE HOLD ADVANCE`, and it does not contain external-domain phrases like chemistry, music, code, math, social cues, etc.

## Contents

```text
utterance_bank_2048.jsonl          2048 utterance entries with hierarchy paths and sparse axis weights
utterance_index_2048.npz           normalized vector matrix for cosine search
index_schema_2048.json             axis list, family list, and index policy
query_reafferent_index.py          query tool for axis-vector → utterance top-k
trace_to_posture_projection.py     conservative trace-window → posture-axis scaffold
family_axis_summary.csv            quick audit of family counts and dominant axes
example_*.json                     example vectors and query results
```

## Shape

```text
64 posture axes
32 families
4 leaves per family
4 core clauses per leaf
4 first-person forms per clause
= 2048 utterances
```

## Axes

The index uses `posture64_v1`:

```text
attention, salience, valence, intensity, certainty, confidence, doubt, uncertainty, coherence, ambiguity, novelty, familiarity, memory, recognition, confirmation, realization, clarity, surprise, curiosity, interest, engagement, search, need, comparison, similarity, difference, connection, separation, ordering, containment, boundary, completion, incompletion, closure_gap, repair, correction, mismatch, conflict, rejection, acceptance, restraint, hesitation, readiness, commitment, persistence, release_pressure, approach, avoidance, withdrawal, overload, calm, tension, urgency, relief, friction, importance, agency, orientation, transition, expectation, saturation, stability, instability, alignment
```

## Families

```text
recognition, familiarity, novelty, curiosity, attention, engagement, uncertainty, confusion, hesitation, restraint, confidence, confirmation, realization, clarity, surprise, mismatch, conflict, rejection, search, comparison, connection, separation, ordering, completion, incompletion, closure_gap, repair, readiness, commitment, approach, avoidance, overload
```

## Query example

```bash
python query_reafferent_index.py --example recognition -k 8
```

Or:

```bash
python query_reafferent_index.py --axis-json '{"recognition":0.95,"familiarity":0.7,"confirmation":0.65,"confidence":0.75}' -k 8
```

## Runtime logging recommendation

Emit top-1 only. Quietly log:

```json
{
  "witness": "W4_0088",
  "emitted_utterance": "I recognize this.",
  "top_k": [
    {"rank": 1, "utterance": "I recognize this.", "cosine": 0.94, "distance": 0.06},
    {"rank": 2, "utterance": "Yes, I recognize this.", "cosine": 0.92, "distance": 0.08}
  ],
  "rank_margin": 0.02,
  "source_window": {"start_tick": 1530, "end_tick": 1557},
  "axis_vector": {}
}
```

## Notes

`trace_to_posture_projection.py` is intentionally conservative. Tune it with real witness windows. The phrase index itself is ready to use.
