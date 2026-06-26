# Runtime Cleanup Classification Analysis

**Date:** 2026-06-26  
**Scope:** Phase 0 of `runtime-cleanup-guardrails`  
**Machine contract:** `docs/contracts/runtime-cleanup-classification.yml`

## Method

This analysis separates code reachability from capability ownership. A source
file can be statically uncalled while still carrying a capability that must be
rederived elsewhere; it is therefore not silently deleted. The capability-level
record is `docs/contracts/runtime-capability-coverage.yml`.

The trace used repository-wide searches for direct imports of the candidate
modules and symbols, then searched for dynamic import mechanisms
(`importlib.import_module`, `__import__`, `pkgutil`, and `find_spec`). It also
checked the active entrypoint and loop imports, the existing runtime-prune
guards, the dependency manifest, and the 2026-06-25 Arachnid audit.

The trace establishes static reachability only. It does not prove behavioral
parity, and it is not a replacement for an import or smoke gate.

## Findings

### Live runtime identity

`nexus.py` constructs `SparseConnectome` and `SelfImprovementEngine`.
`SparseConnectome` invokes the intrinsic `sie_v2` rule. The runtime loop imports
void scouts and invokes optional GDSP/REVGSP adapters. These are live paths and
are classified `keep`.

`core/adc.py` is also a live boundary: checkpoint restoration imports its
territory and boundary state types. The classification does not infer that ADC
is optional merely because its construction is not a simple top-level import.

### Legacy dense substrate

The four former `core/substrate/` files, now preserved under
`docs/sources/legacy-substrate-neurogenesis/`, had no direct import reference
outside that directory, and no dynamic-import mechanism was found anywhere in
the repository. Their implementation is nevertheless not disposable source:

- `substrate.py` imports Torch and supports a GPU backend.
- `neurogenesis.py` imports Torch and grows by allocating a new dense `N x N`
  weight matrix.
- `growth_arbiter.py` records the intended stability and debt-pressure role for
  population growth.
- `structural_homeostasis.py` records pruning and bridge-repair intent.

The initial classification was too coarse: these files also carry node membrane
state, refractory state, spike history, intrinsic plasticity, and synaptic
scaling goals. The default `SparseConnectome` does not expose the corresponding
state, and the current firing-variance signal is variance of its field `W`, not
variance of observed firing events.

The source is preserved in a tracked archive outside the importable runtime.
It must not be deleted while the sparse replacement is open. That replacement
must be derived against the requirements in
`docs/roadmap/sparse-neurogenesis/TODO.md`, and the unowned physiology goals
must receive either a VDM-native sparse owner or an explicit retirement record.

### Legacy global-system variant

`core/global_system.py` also has no direct or dynamic import reference outside
itself. It contains a scheduled one-dimensional k-means ADC and a second SIE
variant. Those mechanics are not the current runtime path: sparse ADC/SIE roles
are held by `core/adc.py`, `core/sie.py`, and `core/sie_v2.py`.

It is an `archive` candidate pending a narrow capability comparison. The current
SIE carries intrinsic valence, but it does not consume current territories or
maintain territory-conditioned value and visitation state. Current ADC is
connected but underfed: it uses observation keys rather than local cartography,
and the sparse path does not emit boundary or frontier observations. In
particular, the old scheduler and k-means mechanics do not become live
requirements merely because they exist in the old file.

### Additional disconnected capability sources

- `core/growth_arbiter.py` computes growth/cull decisions but has no runtime
  caller and no sparse population executor.
- `core/structural_homeostasis.py` is unwired and expects the retired dense
  `A`/`E` interface. `SparseConnectome` carries a narrower pruning/bridging
  implementation internally, so the repair goal is only partial.
- `core/void_b1.py` has a sparse-capable topology packet producer but no runtime
  caller. The default path instead detects spikes in `complexity_cycles`; it
  does not emit Void B1's Euler-rank, triangle, or active-node packet.
- GDSP and REV-GSP are disabled by default and do not accept the default
  `SparseConnectome` state. Their runtime flags currently do not establish an
  operational plasticity path.
- `core/diagnostics.py` has no caller and requires the retired dense adjacency
  interface. Its diagnostic goal needs a sparse readout decision.

### Removed paths and dependency state

The frontend, visualization package, and WebSocket map helpers are absent and
already covered by runtime-prune guards. `requirements.txt` contains neither
Torch nor a GPU package.

The local `venv` can import `vdm_rt`, `SparseConnectome`, and ADC, but its SIE
import stops at `ModuleNotFoundError: scipy`. `scipy` is declared in
`requirements.txt`; this is a local environment provisioning gap, not evidence
against the classification. The Phase 3 import gates remain open until a clean
environment with all declared dependencies is exercised.

## Dispositions

| Surface | Class | Reason | Required next action |
| --- | --- | --- | --- |
| `SparseConnectome`, ADC, SIE/SIE v2, void maps/scouts, neuroplasticity | `keep` | Active runtime ownership | Add importability guards before cleanup moves. |
| `core/substrate/` source | `preserved archive` | Statically isolated dense/Torch implementation with unclosed goals | Keep under `docs/sources/legacy-substrate-neurogenesis/`; do not delete until coverage closes. |
| Sparse population management | `unmet` | No fixed-size sparse executor can grow or retire nodes | Build bounded sparse/event-fed behavior. |
| Node/spike dynamics, intrinsic plasticity, synaptic scaling | `unmet` | No compatible state or operator exists on SparseConnectome | Assign a sparse-native owner or explicitly retire each goal. |
| `core/global_system.py` | `archive` candidate | Statically isolated ADC/SIE variant with partial successors | Close ADC and territory-conditioned-valence coverage first. |
| Growth, homeostasis, B1, GDSP/REV-GSP | `unwired` or `partial` | Implementations exist but are not operational on the default substrate | Establish one compatible owner and an enabled-path test. |
| Frontend, visualization, WebSocket map helpers | `delete` | Removed runtime contamination | Retain and extend absence guards. |

## Open Evidence

- The roadmap refers to `reports/20260622/vdm_rt_void_bus_adc_loop_analysis.md`,
  but that source artifact is not present in this checkout. This report records
  only the current Phase 0 classification; it does not reconstruct the missing
  broader analysis.
- No behavior-level parity run has compared `core/global_system.py` against the
  current ADC/SIE implementations.
- No clean-environment import gate has yet established the retained module set
  without optional or undeclared dependencies.

## Next Gate

The legacy source has moved out of the importable runtime into its tracked
archive. Next, assign owners and acceptance gates for every unmet or unwired
capability; the archive stays until those obligations close.
