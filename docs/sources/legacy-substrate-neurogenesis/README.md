# Legacy Substrate Neurogenesis Source

## Status

**Archived source material. Do not delete. Do not import as live runtime
code.**

These files are the retained design source for sparse-native population work.
They are not an alternate backend, compatibility layer, or executable fallback.
The former implementation uses dense matrices and Torch/GPU paths that are not
permitted in the reboot runtime.

## Preserved Source

- `substrate.py` - node membrane, refractory, spike-history, intrinsic
  plasticity, and synaptic-scaling goals.
- `neurogenesis.py` - node allocation, state extension, and initial supported
  connection goals.
- `growth_arbiter.py` - stability and void-debt admission goal for growth.
- `structural_homeostasis.py` - pruning and bridge-repair goal.

## Sparse-Native Obligation

The active goal is dynamic `N` without dense scans or dense `N x N` allocation:

- bounded growth and retirement between configured minimum and maximum counts;
- sparse extension or retirement of adjacency, node field, stimulation,
  territory, memory, map, SIE, and traversal state;
- growth admission from pressure, stability, and void debt;
- local sparse seeding, pruning, and bridge repair;
- lifecycle events visible through the event spine; and
- no Torch, GPU backend, optimizer, loss, gradient, or training-loop path.

The implementation authority is
`docs/roadmap/sparse-neurogenesis/TODO.md`. The capability obligations and
current gaps are recorded in
`docs/contracts/runtime-capability-coverage.yml`.

## Archive Rule

This archive exists so the original goals remain inspectable while the runtime
is made sparse-native. A future cleanup may delete a source file only after its
corresponding capability is covered or explicitly retired, with evidence added
to the capability-coverage contract.
