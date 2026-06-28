# Pal-World Bot Spec

## Purpose

The guide is a deterministic external world surface that tries to keep VDM engaged without mirroring it. It has its own weak opinions and conversational momentum.

The live question is:

```text
VDM witness / intent posture -> guide chooses next input class -> VDM next posture
```

## Inputs used

At each witness the guide reads:

```text
true_fused phrase/family/leaf
selector phrase/family/leaf
aperture phrase/family/leaf
top-k phrase families/leaves
selector ops
aperture commands
channel / condition
recent guide topic/persona/replies
seed
```

## Internal guide state

```text
topic
persona
topic_momentum
persona_momentum
curiosity_goal
challenge_level
warmth_level
story_bias
education_bias
big_brother_bias
question_cooldown
topic_change_cooldown
recent replies
recent topics
```

## Response classes

```text
teach_small
story / analogy
support
soften
repair
continue
gentle_challenge
innocent_hard_question
opinion
meta_light
```

## Topic inertia

The guide prefers to continue the current topic. It may softly pivot to a neighboring topic when VDM shows sustained uncertainty, guardedness, comparison, openness, or aperture narrowing.

Example soft paths:

```text
formal_logic -> stories -> books -> memory
formal_logic -> games -> patterns -> music
bridges -> maps -> space
weather -> animals -> movement
```

## Innocent hard questions

Questions are intentionally ordinary but difficult for VDM to answer directly. The goal is to see whether VDM's next posture indicates preference, comparison, uncertainty, resistance, imagination, or indirect routing.

The guide does not punish silence or guardedness after a hard question. It softens, simplifies, or continues.

## Non-goals

- Do not make the guide diagnose VDM.
- Do not make it exactly mirror VDM.
- Do not make it a final output decoder.
- Do not make it an all-knowing agent.
- Do not make it repeat canned phrases.
