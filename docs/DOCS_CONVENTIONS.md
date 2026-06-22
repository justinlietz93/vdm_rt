# VDM RT Documentation Conventions

## Tone

Use direct engineering language. Avoid motivational filler. State the boundary, reason, and test.

Preferred pattern:

```text
Claim.
Why it matters.
What would violate it.
How to test it.
```

## Status labels

Use one of:

- `active` — current truth or active roadmap.
- `draft` — useful but not yet enforced.
- `source` — imported material used as evidence or design input.
- `archived` — retained for history only.
- `generated` — produced by tools, not hand edited.

## File naming

Use lowercase kebab-case for docs paths.

```text
runtime-boundaries.md
motor-learning-roadmap.md
aura-distinction-summary.md
```

Imported source files may preserve their original names under `docs/sources/`.

## Front matter

Every file under `docs/pages/` should start with:

```yaml
---
title: Example Title
status: active
owner: runtime-core
source_authority: docs/sources/example.md
summary: One sentence.
---
```

## Evidence language

Do not flatten evidence levels. Use these labels:

- **Hard** — implementation rule. Break = reject.
- **Strong** — design target. May defer, may not contradict.
- **Observational** — observed and important, not fully quantified or packaged.
- **External** — source exists outside this repo.
- **Missing** — expected source not currently included.

## Prohibited doc behavior

- Do not present decoder-generated text as internal state.
- Do not present renderer output as the model's cognition.
- Do not imply the old frontend is coming back.
- Do not duplicate the same invariant as separate authorities.
- Do not hide missing evidence by writing around it.
