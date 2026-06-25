# VDM RT Documentation Quality Gates

## Required before a docs commit

```bash
python docs/governance/tools/check_docs_front_matter.py
```

Recommended runtime check:

```bash
PYTHONPATH=.. python -m vdm_rt.run_nexus --neurons 32 --k 4 --hz 5 --duration 1 --run-dir /tmp/vdm_rt_docs_smoke
```

Recommended test check from the parent directory:

```bash
PYTHONPATH=.. pytest -q vdm_rt/tests
```

## Manual review checklist

- [ ] Pages under `docs/pages/` have front matter.
- [ ] Imported sources stay under `docs/sources/`.
- [ ] Hard requirements point to a source document or contract.
- [ ] Roadmap items are written as buildable tasks, not vague aspirations.
- [ ] No page claims a feature is implemented unless the repo contains it.
- [ ] No page reintroduces a live text decoder, phrase bank, completion branch, renderer author, or frontend-owned runtime path.

## Future checks

Add these when the repo stabilizes:

- link checker,
- duplicate authority checker,
- source-authority existence checker,
- code/docs invariant drift checker,
- roadmap status checker,
- import boundary checker for `core`, `runtime`, `io`, and `control`.
