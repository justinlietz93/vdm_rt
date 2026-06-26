# Runtime Cleanup Guardrails TODO

Status: active draft.
Phase 0 evidence: `docs/roadmap/runtime-cleanup-guardrails/ANALYSIS.md`.

This checklist protects the fresh independent runtime identity. It is allowed to be aggressive because this repo is a reboot extraction, not a compatibility-preserving refactor.

## Phase 0 — Define the Reboot Boundary

### Task 0.1 — Classify every suspicious file

- [x] Step 0.1.1 — Add `docs/contracts/runtime-cleanup-classification.yml` with `keep`, `port`, `archive`, and `delete` classes.
- [x] Step 0.1.2 — Mark active runtime files as `keep`.
- [x] Step 0.1.3 — Mark legacy substrate/neurogenesis files as `port` or `archive`, not silent delete.
- [x] Step 0.1.4 — Mark frontend, visualization, generated outputs, and stale analysis bundles as `delete`.
- [x] Step 0.1.5 — Add a review note for any file whose static import status conflicts with known runtime intent.

### Task 0.2 — Freeze allowed runtime identity

- [x] Step 0.2.1 — Add policy that `SparseConnectome` is the live runtime substrate.
- [x] Step 0.2.2 — Add policy that void walkers and void maps are core runtime systems.
- [x] Step 0.2.3 — Add policy that ADC, SIE, GDSP/REVGSP, bus/event spine, and headless runtime must remain live concepts.
- [x] Step 0.2.4 — Add policy that old frontend, visualization adapters, WebSocket map streaming, torch, and dense substrate backends are not live runtime concepts.

### Task 0.3 — Prove Capability Ownership Before Removal

- [x] Step 0.3.1 — Add a capability-coverage contract for every current archive or port candidate.
- [x] Step 0.3.2 — Record each goal as covered, partial, unwired, unmet, diagnostic-only, or intentionally retired.
- [x] Step 0.3.3 — Add a guard that prevents deletion while capability coverage is unresolved and requires archived source preservation.
- [ ] Step 0.3.4 — Assign an implementation owner and acceptance gate for every `unwired` or `unmet` runtime goal.

## Phase 1 — Add Hard Guard Tests

### Task 1.1 — Guard against deleted frontend and visualization paths

- [ ] Step 1.1.1 — Add `tests/guards/test_no_frontend_residue.py`.
- [ ] Step 1.1.2 — Add `tests/guards/test_no_visualization_runtime_path.py`.
- [ ] Step 1.1.3 — Verify no live module imports `vdm_rt.frontend`, `vdm_rt.io.visualization`, `dash`, WebSocket map stream helpers, or old visualization frames.
- [ ] Step 1.1.4 — Verify no runtime CLI flag retains compatibility behavior for removed visualization systems.

### Task 1.2 — Guard against ML/GPU contamination

- [ ] Step 1.2.1 — Add `tests/guards/test_no_torch_runtime_dependency.py`.
- [ ] Step 1.2.2 — Verify no live `vdm_rt/` module imports `torch`.
- [ ] Step 1.2.3 — Verify `requirements.txt` does not include torch or GPU stack dependencies.
- [ ] Step 1.2.4 — Add runtime text scan for `backward`, `optimizer`, `loss`, `training loop`, and similar ML-training vocabulary in live runtime modules.
- [ ] Step 1.2.5 — Permit historical vocabulary only under `docs/archive/` or explicitly marked source material.

### Task 1.3 — Guard the systems that must not be deleted

- [ ] Step 1.3.1 — Add `tests/guards/test_void_maps_remain_core_runtime.py`.
- [ ] Step 1.3.2 — Add `tests/guards/test_sparse_connectome_is_runtime_substrate.py`.
- [ ] Step 1.3.3 — Verify `core/cortex/void_walkers/` remains importable.
- [ ] Step 1.3.4 — Verify `core/cortex/maps/` remains importable.
- [ ] Step 1.3.5 — Verify `core/sparse_connectome.py`, `core/adc.py`, `core/sie.py`, and `core/sie_v2.py` remain importable without frontend dependencies.

## Phase 2 — Archive Without Losing Capability

### Task 2.1 — Move legacy substrate material out of live runtime

- [x] Step 2.1.1 — Create `docs/sources/legacy-substrate-neurogenesis/` as a tracked source archive.
- [x] Step 2.1.2 — Move old dense substrate files there as source material.
- [x] Step 2.1.3 — Remove the old files from live importable runtime paths.
- [x] Step 2.1.4 — Add `README.md` explaining that the old code is design source for sparse neurogenesis, not live runtime code.

### Task 2.2 — Preserve the extracted invariant

- [x] Step 2.2.1 — Document dynamic neuron population growth as a preserved capability.
- [x] Step 2.2.2 — Document node-count management between configured minimum and maximum bounds.
- [x] Step 2.2.3 — Document growth debt, stability arbitration, seeding, culling, structural homeostasis, edge repair, and bridge growth as requirements for the sparse replacement.
- [x] Step 2.2.4 — Link this extraction note to `docs/roadmap/sparse-neurogenesis/TODO.md`.

## Phase 3 — Validate the Clean Runtime

### Task 3.1 — Runtime smoke gates

- [ ] Step 3.1.1 — Run a 32-neuron smoke test from a clean environment.
- [ ] Step 3.1.2 — Run a 64-neuron smoke test with bus/ADC telemetry enabled.
- [ ] Step 3.1.3 — Verify smoke output includes event/bus counters after the event-spine phase lands.
- [ ] Step 3.1.4 — Store smoke command and expected minimal fields in docs.

### Task 3.2 — Import gates

- [ ] Step 3.2.1 — Prove `import vdm_rt` works without frontend dependencies.
- [ ] Step 3.2.2 — Prove `import vdm_rt.core.sparse_connectome` works without torch.
- [ ] Step 3.2.3 — Prove `import vdm_rt.run_nexus` works from the fresh repo root.
- [ ] Step 3.2.4 — Add these import checks to CI.

## Phase 4 — TODO Comment Hygiene

### Task 4.1 — Classify live-code TODOs

- [x] Step 4.1.1 — Remove stale `TODO REMOVE DENSE SCANS` comments from `nexus.py`.
- [x] Step 4.1.2 — Rewrite the scan-reduction TODO in `core/metrics.py` to point at `SparseConnectome.metrics_snapshot()` and event-spine reducers.
- [x] Step 4.1.3 — Rewrite the legacy SIE TODO in `core/global_system.py` as a keep/port/archive/delete classification task.
- [ ] Step 4.1.4 — Add a TODO scanner that reports every live-code TODO with file, line, category, and owner.
- [ ] Step 4.1.5 — Require each live-code TODO to be classified as `bug`, `cleanup`, `port`, `archive`, `performance`, or `roadmap-linked`.

### Task 4.2 — Remove stale dense backend compatibility

- [x] Step 4.2.1 — Remove `FORCE_DENSE` runtime backend switching from `nexus.py`.
- [x] Step 4.2.2 — Remove CLI dense/sparse selection flags.
- [x] Step 4.2.3 — Remove `sparse_mode` forwarding from the runtime launcher and process manager.
- [x] Step 4.2.4 — Update the dense-connectome guard so dense backend selection cannot reappear silently.
- [ ] Step 4.2.5 — Add a scan report that distinguishes runtime dense scans from accurate comments saying a module avoids dense scans.
