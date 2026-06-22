# Repo-Scan Upgrade TODO

Status: active draft.
Source report: `reports/20260622/vdm_rt_void_bus_adc_loop_analysis.md`.

Arachnid import and audit scans were useful, but this class of issue is runtime dataflow, not just static imports. These TODOs are candidate improvements for the repo-scan stack.

## Phase 0 — Event and Bus Schema Scanner

### Task 0.1 — Discover event producers

- [ ] Step 0.1.1 — Detect calls to `publish(...)`, `publish_many(...)`, `append(BaseEvent)`, and event constructors.
- [ ] Step 0.1.2 — Extract literal event kind strings.
- [ ] Step 0.1.3 — Extract dataclass event types.
- [ ] Step 0.1.4 — Report producer file, function, and line number.

### Task 0.2 — Discover event consumers

- [ ] Step 0.2.1 — Detect `if kind == ...` and `match kind` consumers.
- [ ] Step 0.2.2 — Detect reducer handlers by dataclass type.
- [ ] Step 0.2.3 — Report consumed-but-never-produced kinds.
- [ ] Step 0.2.4 — Report produced-but-never-consumed kinds.
- [ ] Step 0.2.5 — Generate candidate coverage tests.

## Phase 1 — Runtime Hot-Loop Scan Detector

### Task 1.1 — Find scan-heavy loops

- [ ] Step 1.1.1 — Detect loops over `range(N)` inside runtime tick modules.
- [ ] Step 1.1.2 — Detect loops over adjacency lists and full weight vectors.
- [ ] Step 1.1.3 — Detect repeated calls to metric functions in one tick path.
- [ ] Step 1.1.4 — Detect DSU rebuilds and connected-component computations.
- [ ] Step 1.1.5 — Rank hot-loop candidates by file and likely tick frequency.

### Task 1.2 — Suggest cache/reducer replacements

- [ ] Step 1.2.1 — Identify repeated metrics already cached on runtime objects.
- [ ] Step 1.2.2 — Identify event-fed reducers that could replace scans.
- [ ] Step 1.2.3 — Emit candidate “replace scan with snapshot field” notes.

## Phase 2 — State Ownership Scanner

### Task 2.1 — Track private field writes and reads

- [ ] Step 2.1.1 — Detect assignments to fields like `_memory_field`.
- [ ] Step 2.1.2 — Detect reads of the same field on different object names.
- [ ] Step 2.1.3 — Report likely split ownership patterns such as `eng._memory_field` vs `nx._memory_field`.
- [ ] Step 2.1.4 — Flag fields written in one layer and read in another without a port or accessor.

### Task 2.2 — Generate ownership report

- [ ] Step 2.2.1 — Group fields by owner object symbol.
- [ ] Step 2.2.2 — Group reads/writes by layer.
- [ ] Step 2.2.3 — Emit suggested single-owner candidate.

## Phase 3 — Tick-Order Dataflow Trace

### Task 3.1 — Static stage extractor

- [ ] Step 3.1.1 — Identify producer calls.
- [ ] Step 3.1.2 — Identify drain/fold/reducer calls.
- [ ] Step 3.1.3 — Identify metrics build calls.
- [ ] Step 3.1.4 — Identify actuator/plasticity calls.
- [ ] Step 3.1.5 — Report order as a stage table.

### Task 3.2 — Dynamic trace option

- [ ] Step 3.2.1 — Add optional instrumentation hooks for a one-tick trace.
- [ ] Step 3.2.2 — Record producer/fold/metric order.
- [ ] Step 3.2.3 — Flag producer-after-reducer and stale-batch patterns.

## Phase 4 — Boundary and Contamination Scanner

### Task 4.1 — Fresh runtime policy scan

- [ ] Step 4.1.1 — Detect frontend/UI imports.
- [ ] Step 4.1.2 — Detect torch/GPU imports.
- [ ] Step 4.1.3 — Detect visualization/WebSocket runtime paths.
- [ ] Step 4.1.4 — Detect ML/training vocabulary in live runtime modules.
- [ ] Step 4.1.5 — Report allowed exceptions under `docs/archive/` and `docs/sources/`.

### Task 4.2 — CI-ready output

- [ ] Step 4.2.1 — Emit JSON report.
- [ ] Step 4.2.2 — Emit markdown report.
- [ ] Step 4.2.3 — Exit nonzero on hard policy violations.
- [ ] Step 4.2.4 — Support warning-only mode for exploratory scans.
