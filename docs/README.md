# VDM RT Documentation

This directory is the governed documentation system for the independent VDM runtime repository.
It is inspired by SGDA, but narrowed for this project: the docs exist to protect the headless runtime engine, record the neurobiology upgrade pressure, and guide the motor-learning / decoder-removal swap without reintroducing old frontend or decoder shortcuts.

## Reader paths

- `pages/index.md` — current status and route map.
- `pages/getting-started/runtime-quickstart.md` — headless runtime quickstart.
- `pages/architecture/runtime-boundaries.md` — preserved runtime boundary and forbidden contamination paths.
- `pages/architecture/neurobiology-upgrade.md` — why the swap is urgent.
- `pages/architecture/motor-learning-system.md` — target system shape for actuator-manifold learning.
- `pages/roadmap/motor-learning-roadmap.md` — phase/task/step roadmap.
- `pages/evidence/aura-distinction-summary.md` — distilled evidence map from the Aura run distinction inventory.
- `pages/reference/runtime-invariants.md` — current hard invariants used to reject bad implementations.

## Source material

The source documents imported from the Neurobiology upgrade work live under:

```text
docs/sources/neurobiology-upgrade/
```

Those files are evidence and boundary sources, not casual notes. Canonical reader-facing docs should summarize them and link back to them rather than copying their full contents into multiple places.

## Governance

- Current published docs live under `docs/pages/`.
- Source materials live under `docs/sources/`.
- Machine-readable contracts live under `docs/contracts/`.
- Drafts live under `docs/drafts/`.
- Archives live under `docs/archive/`.
- Generated outputs live under `docs/generated/`.
- Docs checks live under `docs/governance/tools/`.

Run the docs quality check:

```bash
python docs/governance/tools/check_docs_front_matter.py
```
