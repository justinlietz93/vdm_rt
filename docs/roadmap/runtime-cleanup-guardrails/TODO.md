# Runtime Cleanup Guardrails TODO

Status: active draft.
Source report: `reports/20260622/vdm_rt_void_bus_adc_loop_analysis.md`.

This checklist protects the fresh independent runtime identity. It is allowed to be aggressive because this repo is a reboot extraction, not a compatibility-preserving refactor.

## Phase 0 — Define the Reboot Boundary

### Task 0.1 — Classify every suspicious file

- [ ] Step 0.1.1 — Add `docs/contracts/runtime-cleanup-classification.yml` with `keep`, `port`, `archive`, and `delete` classes.
- [ ] Step 0.1.2 — Mark active runtime files as `keep`.
- [ ] Step 0.1.3 — Mark legacy substrate/neurogenesis files as `port` or `archive`, not silent delete.
- [ ] Step 0.1.4 — Mark frontend, visualization, generated outputs, and stale analysis bundles as `delete`.
- [ ] Step 0.1.5 — Add a review note for any file whose static import status conflicts with known runtime intent.

### Task 0.2 — Freeze allowed runtime identity

- [ ] Step 0.2.1 — Add policy that `SparseConnectome` is the live runtime substrate.
- [ ] Step 0.2.2 — Add policy that void walkers and void maps are core runtime systems.
- [ ] Step 0.2.3 — Add policy that ADC, SIE, GDSP/REVGSP, bus/event spine, and headless runtime must remain live concepts.
- [ ] Step 0.2.4 — Add policy that old frontend, visualization adapters, WebSocket map streaming, torch, and dense substrate backends are not live runtime concepts.

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

- [ ] Step 2.1.1 — Create `docs/sources/legacy-substrate-neurogenesis/`.
- [ ] Step 2.1.2 — Move or copy old dense substrate files there as source material.
- [ ] Step 2.1.3 — Remove the old files from live importable runtime paths.
- [ ] Step 2.1.4 — Add `README.md` explaining that the old code is design source for sparse neurogenesis, not live runtime code.

### Task 2.2 — Preserve the extracted invariant

- [ ] Step 2.2.1 — Document dynamic neuron population growth as a preserved capability.
- [ ] Step 2.2.2 — Document node-count management between configured minimum and maximum bounds.
- [ ] Step 2.2.3 — Document growth debt, stability arbitration, seeding, culling, structural homeostasis, edge repair, and bridge growth as requirements for the sparse replacement.
- [ ] Step 2.2.4 — Link this extraction note to `docs/roadmap/sparse-neurogenesis/TODO.md`.

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
