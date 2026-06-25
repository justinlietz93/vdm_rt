# VDM RT Documentation Architecture

## Purpose

The VDM RT docs are not a general website skeleton. They are a control surface for a surgical runtime rewrite.
The docs must keep four realities separated:

1. **Runtime engine truth** — what the repo currently runs.
2. **Hard implementation law** — what the new UTE/UTD and motor-learning path must not violate.
3. **Evidence pressure** — why the swap is justified by Aura distinctions and runtime papers.
4. **Roadmap state** — what work is planned, active, blocked, or complete.

## Documentation layers

```text
docs/
├─ README.md                    documentation maintainer guide
├─ DOCS_ARCHITECTURE.md         this system
├─ DOCS_CONVENTIONS.md          writing and naming rules
├─ DOCS_QUALITY_GATES.md        checks required before publishing
├─ pages/                       current reader-facing documentation
├─ contracts/                   machine-readable docs/runtime contracts
├─ sources/                     imported source material and evidence packets
├─ roadmap/                     working task checklists and phase trackers
├─ governance/                  docs policy and validation scripts
├─ generated/                   generated evidence and reports
├─ drafts/                      unpublished drafts
└─ archive/                     historical material, not current truth
```

## Authority rules

- `docs/pages/` owns reader-facing truth.
- `docs/sources/` owns imported evidence and source packets.
- `docs/contracts/` owns machine-checkable boundaries and invariants.
- `docs/roadmap/` owns working task state.
- `README.md` at repo root owns public project orientation, not detailed architecture.

## Narrowed SGDA rule

A document is only added if it helps one of these jobs:

- run the headless runtime,
- protect the core/runtime boundary,
- explain the neurobiology upgrade,
- prevent decoder/renderer/front-end contamination,
- guide the motor-learning implementation,
- record evidence status and acceptance gates.

If a doc does not serve one of those jobs, it belongs outside this repo or in `docs/archive/`.
