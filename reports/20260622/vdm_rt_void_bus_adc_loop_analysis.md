# VDM RT Void Walker / Bus / ADC / Loop Analysis

Generated from the Arachnid scan bundle plus a direct inspection of the current headless `vdm_rt` code snapshot available in the sandbox. I also ran a small 64-neuron smoke run to check whether the runtime surfaces the signals it appears to intend to surface.

## Executive finding

The suspicion is mostly correct, but needs a sharper split:

1. The connectome-level void traversal **is** attached to the announcement bus, and ADC **does** receive some observations.
2. The bus is not receiving the richer scout/map event stream. The newer void walkers produce `BaseEvent` objects and are folded directly through `CoreEngine`; they are not published into the `AnnounceBus`, and ADC does not consume them.
3. ADC is receiving a narrow event vocabulary: mostly `region_stat` and `cycle_hit`. It accepts `boundary_probe` and `novel_frontier`, but the current sparse connectome path does not emit those. In a smoke run, `adc_boundaries` stayed at 0 for all ticks.
4. The main loop is doing repeated full or near-full graph traversals even though the sparse connectome already curates active-edge counts, fragment lower bounds, cycle estimates, traversal findings, and event-driven map heads.
5. The runtime has several parallel event systems that are useful individually but not yet seated behind one event spine: `AnnounceBus`, `Observation`, `BaseEvent`, `EventDrivenMetrics`, ADC, `TerritoryUF`, and the map reducers.

The right fix is not to delete the void walkers/maps. They are producing useful signals. The fix is to formalize a single runtime event spine and route the event producers into the reducers intentionally.

## Evidence from smoke run

Command class used: headless `python -m vdm_rt.run_nexus` with 64 neurons, k=4, duration 2 seconds.

Observed tick count: 39 ticks.

Key summary:

| Metric | Observed result |
|---|---:|
| `adc_territories` | 2 to 4 |
| `adc_boundaries` | always 0 |
| `adc_cycle_hits` | 56 to 107 per tick |
| canonical `vt_coverage` | 0.765625 to 1.0 |
| event-driven `evt_vt_coverage` | always 1.0 |
| `evt_heat_count` | 53 to 64 |
| `evt_exc_count` | 53 to 64 |
| `evt_inh_count` | always 15 |
| `evt_memory_count` | 53 to 64 |
| `evt_trail_count` | 53 to 64 |

Interpretation:

- ADC is alive, but boundary detection is effectively dead or unimplemented in the runtime feed.
- Event-driven maps are alive and being populated.
- The rich maps are not making ADC richer because they bypass the announcement bus and are folded inside `CoreEngine`.
- Memory/trail maps are active, but dimensionless memory steering scalars such as `mem_Theta`, `mem_Da`, `mem_Lambda`, and `mem_Gamma` were absent from the tick logs. The runtime fold checks `nx._memory_field`, while ownership currently lives on `eng._memory_field`.

## Dataflow currently implied by the code

Current runtime shape:

```text
SparseConnectome.step()
  -> _void_traverse()
      -> bus.publish(Observation(kind="cycle_hit"))
      -> bus.publish(Observation(kind="region_stat"))

runtime.telemetry.tick_fold()
  -> bus.drain()
  -> ADC.update_from(observations)
  -> observations_to_events(observations)
  -> EventDrivenMetrics, if CoreEngine is absent

runtime.loop.main
  -> run 9 void scouts with bus=None
  -> collect BaseEvent list
  -> convert last obs batch to BaseEvents
  -> add ADCEvent
  -> fold memory/trail/maps
  -> CoreEngine.step(events)
```

Important consequence:

```text
Connectome traversal observations go through bus -> ADC.
Scout events do not go through bus -> ADC.
Scout events go directly to CoreEngine/event maps.
```

That means the runtime is not missing all void information. It is split into two channels without a unified router.

## Finding 1: ADC is connected, but the feed is too thin

`SparseConnectome._void_traverse()` publishes only:

- `cycle_hit`
- `region_stat`

ADC can consume:

- `region_stat`
- `boundary_probe`
- `cycle_hit`
- `novel_frontier`

The missing producer side is the issue. In the sparse path, `boundary_probe` and `novel_frontier` are not emitted. That explains the smoke result where `adc_boundaries` remained 0 for every tick.

There is also a richness problem in `region_stat`:

- `nodes` are sampled from local traversal.
- `s_mean` is local-ish from selected traversal weights.
- `w_mean` and `w_var` are global values from `self.W.mean()` and `self.W.var()`.
- `domain_hint` is always empty.
- `cycle_hit` uses `coverage_id=0`.

So ADC is not getting enough local territory identity to produce strong territory maps.

## Finding 2: void walkers are used, but not in the bus/ADC path

The newer void walkers under `core/cortex/void_walkers/` are active in the runtime. They emit `BaseEvent` objects like:

- `VTTouchEvent`
- `EdgeOnEvent`
- `SpikeEvent`
- `DeltaWEvent`

The runtime calls:

```text
_run_scouts_once(..., bus=None)
```

So their events are returned to the runtime and folded into `CoreEngine`, not published to `AnnounceBus`.

This is probably the core mismatch you were feeling. The walkers are not unused. They are just not globally visible through the same bus that ADC reads.

Do not simply pass `AnnounceBus` into `_run_scouts_once()`. The event types do not match ADC’s `Observation` contract. Either add a second event channel or normalize `BaseEvent` into ADC-compatible observations.

## Finding 3: territory sampling for GDSP is one tick late and underfed

GDSP asks for `territory_indices` before the telemetry fold and before the current tick’s observations are folded into `TerritoryUF`.

Current order:

```text
compute step and metrics
maybe_run_gdsp()
telemetry fold drains bus
TerritoryUF folds observations
CoreEngine folds events
```

So GDSP mostly acts on old territory data. If no territory exists, it publishes a `BiasHintEvent(kind="bias_hint")` to the bus, but ADC does not consume `bias_hint`, and the observation-to-event adapter ignores unknown kinds.

That means `bias_hint` is effectively a dead signal right now.

## Finding 4: `_last_obs_batch` can become stale

`tick_fold()` only sets `nx._last_obs_batch` when `obs_batch` is nonempty. If a tick drains no bus items, the old batch can remain on `nx` and later code may fold stale observations.

In the smoke run the bus was busy every tick, so this likely did not manifest. It is still a bug shape.

Fix:

```text
set nx._last_obs_batch = [] before drain
set nx._last_adc_metrics = {} before drain
then replace only with current tick data
```

## Finding 5: the main loop repeats expensive graph-derived work

The main loop currently uses scan-based metrics in several places:

1. `_comp_density()` calls `active_edge_count()` before the connectome step.
2. `SparseConnectome.step()` itself scans active edges to update `_edges_active`, `_vertices_active`, fragment state, and cycle estimate.
3. `compute_metrics()` calls:
   - `active_edge_count()`
   - `connected_components()`
   - `cyclomatic_complexity()`
   - `connectome_entropy()`
4. `CoreEngine.snapshot()` calls `compute_metrics()` again and merges the result under `evt_*` fields.

So the same active graph can be walked multiple times per tick.

This confirms the concern that the loop is scanning data already curated elsewhere. The issue is not exactly that SIE itself scans the graph. Legacy SIE is handed a density value, and SIE v2 is vector-local over `W`/`dW`. The scans happen around the metric and snapshot layer feeding SIE/runtime telemetry.

## Finding 6: there are duplicate scout paths

There are at least two scout paths:

1. `CoreEngine._void_scout`, initialized from the legacy `VoidColdScoutWalker` facade.
2. Runtime loop’s explicit 9-scout list: heat, cold, excitation, inhibition, void-ray, memory-ray, frontier, cycle, sentinel.

With `CoreEngine` present, the fallback runtime `_void_scout` path is skipped, but `CoreEngine.step()` still runs its own cold scout, while the runtime also runs the broader scout batch before calling `eng.step()`.

That may be intentional as a compatibility bridge, but it is currently hard to reason about. There should be one scout ownership point.

## Finding 7: memory field ownership is split

The runtime creates or patches:

- `eng._memory_field`
- `eng._memory_map`
- `connectome._memory_field`
- `connectome._memory_map`

But `tick_fold()` looks for:

```text
nx._memory_field
```

The smoke logs did not include `mem_Theta`, `mem_Da`, `mem_Lambda`, or `mem_Gamma`, which supports the conclusion that the memory field is not exposed at the location the telemetry fold expects.

## Recommended architecture correction

Introduce a runtime event spine that separates type-safe channels but gives the global systems one place to read from.

Suggested shape:

```text
RuntimeEventSpine
  observations: Observation channel for ADC/cartography
  events: BaseEvent channel for maps/EventDrivenMetrics/motor reducers
  counters: per-kind published/drained/dropped metrics
```

Minimal API:

```python
spine.publish_observation(obs)
spine.publish_event(event)
spine.drain_observations(max_items)
spine.drain_events(max_items)
spine.metrics()
```

Then normalize producers:

```text
SparseConnectome traversal
  -> Observation: cycle_hit, region_stat, boundary_probe, novel_frontier

Scout batch
  -> BaseEvent: vt_touch, edge_on, spike, delta_w
  -> optional Observation summary: region_stat/boundary_probe/novel_frontier

Runtime scalar delta
  -> BaseEvent DeltaEvent
  -> optional Observation only if ADC should care
```

## Better tick order

A cleaner tick should be staged like this:

```text
1. Ingest input and stimulation.
2. Compute previous-tick drive/gate.
3. Advance connectome.
4. Collect connectome observations.
5. Run bounded scouts using current seeds and map heads.
6. Normalize scout events into ADC observations where appropriate.
7. Fold ADC, TerritoryUF, EventDrivenMetrics, memory/trail/maps.
8. Build metrics from cached counters/reducers.
9. Run optional GDSP/REVGSP using current territories or schedule for next tick explicitly.
10. Emit status/log/checkpoint.
```

The important rule:

```text
all producers emit first, then all reducers fold, then metrics are built.
```

The current loop interleaves producers/reducers in a way that causes one-tick lag, bypassed channels, and duplicated scans.

## Prioritized fix plan

### Phase 1: Instrument and prove the bus path

- Add `AnnounceBus.publish_many()` and per-kind counters.
- Add `AnnounceBus.metrics()` with published/drained/dropped counts.
- Clear `_last_obs_batch` and `_last_adc_metrics` at the start of each fold.
- Add tick metrics:
  - `bus_published_region_stat`
  - `bus_published_cycle_hit`
  - `bus_published_boundary_probe`
  - `bus_published_novel_frontier`
  - `bus_drained_total`
  - `bus_dropped_total`
- Add tests proving ADC sees all four supported observation kinds.

### Phase 2: Feed ADC richer information

- Update `_void_traverse()` so `region_stat.w_mean/w_var` are local to `sample_nodes`, not global.
- Emit `boundary_probe` when traversal sees low support between adjacent regions or repeated low-coupling cut behavior.
- Emit `novel_frontier` when cold/rare/unseen regions repeatedly appear.
- Set meaningful `domain_hint` or `source_hint` values.
- Stop using `coverage_id=0` for all cycle hits.

### Phase 3: Unify scout output routing

- Keep scouts returning `BaseEvent`.
- Add `base_events_to_observations()` for ADC summaries.
- Have runtime publish/fold scout events through the event spine, not directly through scattered local lists.
- Feed `TerritoryUF` from both observation-derived edge/cycle signals and `EdgeOnEvent` from scouts.

### Phase 4: Remove repeated graph scans

- Add `SparseConnectome.metrics_snapshot()` or `snapshot_metrics()`.
- Let `compute_metrics()` prefer `connectome.metrics_snapshot()` when present.
- Replace `CoreEngine.snapshot()` scan with `CoreEngine.snapshot(canonical_metrics=m)` or an event-only snapshot.
- Use cached `_edges_active`, `_vertices_active`, `components_lb`, `cycles_est`, and traversal findings.
- Move expensive full audits behind explicit audit cadence.

### Phase 5: Simplify ownership

- One owner for scout execution.
- One owner for memory field.
- One owner for event folding.
- Runtime loop should orchestrate, not implement each reducer inline.

Suggested file split:

```text
runtime/loop/main.py                 thin tick shell
runtime/loop/event_spine.py          bus/channels/counters
runtime/loop/producers.py            connectome/scout/runtime event producers
runtime/loop/reducers.py             ADC, TerritoryUF, maps, EventDrivenMetrics
runtime/loop/metrics.py              cached metric snapshot builder
runtime/loop/actuators.py            GDSP/REVGSP gates
```

## What to keep

Keep these systems for now:

- `core/cortex/void_walkers/`
- `core/cortex/maps/`
- `core/adc.py`
- `core/bus.py`
- `core/proprioception/events.py`
- `core/proprioception/territory.py`
- both SIE systems until the motor-learning swap has explicit parity tests

The problem is not that these systems are useless. The problem is that their outputs are not routed through one spine, and some reducers consume stale or partial feeds.

## Repo-scan improvement suggestion

Arachnid is useful for imports and file pressure, but this kind of bug is mostly runtime dataflow, not import structure.

Useful next scanners:

1. **Bus schema scanner**
   - Finds `publish(...)`, `drain(...)`, event kinds, and consumers.
   - Reports event kinds produced but never consumed.
   - Reports event kinds consumed but never produced.

2. **Hot-loop scan detector**
   - Finds `for range(N)`, adjacency scans, DSU rebuilds, entropy scans, and repeated metric recomputation inside runtime loops.

3. **State ownership scanner**
   - Reports fields written in one object path but read from another, such as `eng._memory_field` vs `nx._memory_field`.

4. **Tick-order dataflow trace**
   - Static or lightweight dynamic trace of producer/fold/metric order.
   - Would flag one-tick lag and stale `_last_obs_batch` patterns.

5. **Event-kind coverage tests generator**
   - Reads event dataclasses and adapters, then scaffolds tests for every supported kind.

## Bottom line

The current runtime is not broken in a simple way. It is halfway through a good migration: from scan-heavy global metrics toward event-fed local reducers.

The missing step is to make the event spine explicit.

Once that is done, ADC can become rich enough to produce meaningful territories, SIE can stop depending on repeated scan-derived density, GDSP can receive current territory indices, and the main loop can be cut down to a small orchestration shell.
