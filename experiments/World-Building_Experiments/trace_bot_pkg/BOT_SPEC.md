# Deterministic Conversation Bot Spec

## Core contract

```python
packet = bot.step(record)
```

Input `record` is a dict containing a translated VDM posture. Output `packet` is a deterministic response packet.

The same input sequence and same configuration must produce byte-identical JSONL output.

## Normalization

The bot normalizes input in this order:

1. Use explicit `family` if present.
2. Else use known aliases such as `true_top1_family`, `fused_family`, `selector_family`, or `aperture_family`.
3. Else infer a coarse family from phrase keywords.
4. Else use `unknown`.

The phrase is similarly taken from `phrase`, then top1 aliases.

## State

The bot keeps only deterministic state:

```text
turn_count
last_family
family_streak
last_rule_id
```

There is no stochastic choice.

## Rule families

Primary families:

```text
attention
containment
restraint
conflict
recognition
comparison
readiness
uncertainty
completion
novelty
avoidance
overload
unknown
```

## Output actions

Each rule emits:

```text
reply_text
aperture_hint
stimulus_policy
reafferent_gain_hint
action
```

`reply_text` is human-readable. The other fields are machine-readable experiment logs.

## Timing controls

The bot itself does not know ticks except for logging. If shifted timing is needed, use the CLI `--lag-events` option or perform lagging in the runtime harness.

## Non-goals

```text
The bot does not decide truth.
The bot does not infer meaning beyond fixed keyword/family rules.
The bot does not improve itself.
The bot does not store conversation content except family streak state.
The bot does not generate novel sentences.
```
