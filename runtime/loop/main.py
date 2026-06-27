"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles. Commercial use requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""

from __future__ import annotations

"""
Runtime main loop (extracted from Nexus.run for modularization).

Behavior:
- Mirrors the original Nexus while-loop exactly (move-only).
- No logging configuration or finalization here; caller handles setup/teardown.
- Operates directly on the passed 'nx' Nexus-like object to preserve state and IO wiring.

Inputs:
- nx: Nexus-like instance (provides ute/utd/connectome/adc/etc.)
- t0: float timestamp at loop start (time.time())
- step: starting tick index (int)
- duration_s: optional max wall-clock seconds to run

Returns:
- last step index (int) after the loop completes/breaks
"""

from typing import Any, Dict, Iterable, List, Set, Optional
import hashlib
import time

from vdm_rt.config import config_bool, config_float, config_int
from vdm_rt.runtime.stepper import compute_step_and_metrics as _compute_step_and_metrics
from vdm_rt.runtime.telemetry import tick_fold as _tick_fold
from vdm_rt.runtime.events_adapter import (
    observations_to_events as _obs_to_events,
    adc_metrics_to_event as _adc_event,
)
from vdm_rt.core.engine import CoreEngine as _CoreEngine
from vdm_rt.core.proprioception.events import EventDrivenMetrics as _EvtMetrics
from vdm_rt.core.cortex.scouts import VoidColdScoutWalker as _VoidScout
from vdm_rt.core.signals import apply_b1_detector as _apply_b1d
from vdm_rt.runtime.helpers.ingest import process_messages as _process_messages
from vdm_rt.runtime.helpers.checkpointing import save_tick_checkpoint as _save_tick_checkpoint
from vdm_rt.runtime.helpers.status_http import (
    maybe_start_status_http as _maybe_start_status_http,
)
from vdm_rt.runtime.helpers.redis_out import maybe_publish_status_redis as _maybe_publish_status_redis

# Void-faithful scout runner (stateless, per-tick; no schedulers)
from vdm_rt.core.cortex.void_walkers.runner import run_scouts_once as _run_scouts_once
from vdm_rt.core.cortex.void_walkers.void_heat_scout import HeatScout
from vdm_rt.core.cortex.void_walkers.void_ray_scout import VoidRayScout
from vdm_rt.core.cortex.void_walkers.void_memory_ray_scout import MemoryRayScout
from vdm_rt.core.cortex.void_walkers.void_frontier_scout import FrontierScout
from vdm_rt.core.cortex.void_walkers.void_cycle_scout import CycleHunterScout
from vdm_rt.core.cortex.void_walkers.void_sentinel_scout import SentinelScout
# Also expose the remaining scouts for full coverage (9 walkers)
from vdm_rt.core.cortex.void_walkers.void_cold_scout import ColdScout
from vdm_rt.core.cortex.void_walkers.void_excitation_scout import ExcitationScout
from vdm_rt.core.cortex.void_walkers.void_inhibition_scout import InhibitionScout
# Memory/trail steering fields (owner + adapter view)
from vdm_rt.core.cortex.maps.memorymap import MemoryMap
from vdm_rt.core.cortex.maps.trailmap import TrailMap
from vdm_rt.core.memory import MemoryField

# Development strictness gate: raise swallowed exceptions when enabled
STRICT = config_bool("runtime.strict", False)


def _bounded_ints(values: Iterable[Any], limit: int = 64) -> List[int]:
    out: List[int] = []
    seen: Set[int] = set()
    for value in values or []:
        try:
            item = int(value)
        except Exception:
            continue
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
        if len(out) >= int(max(0, limit)):
            break
    return out


def _bounded_int_sequence(values: Iterable[Any], limit: int = 64) -> List[int]:
    out: List[int] = []
    for value in values or []:
        try:
            item = int(value)
        except Exception:
            continue
        out.append(item)
        if len(out) >= int(max(0, limit)):
            break
    return out


def _hash_ints(values: Iterable[Any]) -> str:
    ints = sorted(_bounded_ints(values, limit=4096))
    raw = ",".join(str(i) for i in ints).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _observation_nodes(obs_batch: Iterable[Any], limit: int = 4096) -> List[int]:
    nodes: List[int] = []
    for obs in obs_batch or []:
        try:
            raw_nodes = getattr(obs, "nodes", None)
            if raw_nodes is None and isinstance(obs, dict):
                raw_nodes = obs.get("nodes")
            nodes.extend(
                _bounded_int_sequence(raw_nodes or [], limit=max(0, limit - len(nodes)))
            )
            if len(nodes) >= int(max(0, limit)):
                break
        except Exception:
            continue
    return nodes


def _record_motor_trace(nx: Any, method_name: str, record: Dict[str, Any]) -> bool:
    try:
        trace = getattr(nx, "motor_trace", None)
        method = getattr(trace, method_name, None)
        if method is None:
            return False
        return bool(method(dict(record or {})))
    except Exception:
        return False


def _call_observe_nodes(actuator: Any, nodes: List[int], step: int, metrics: Dict[str, Any]) -> Any:
    fn = getattr(actuator, "observe_nodes", None)
    if fn is None:
        fn = getattr(actuator, "observe", None)
    if fn is None:
        return None
    try:
        return fn(nodes, tick=int(step), metrics=metrics)
    except TypeError:
        try:
            return fn(nodes, int(step))
        except TypeError:
            return fn(nodes)


def _maybe_observe_motor_actuator(
    nx: Any,
    step: int,
    obs_nodes: List[int],
    metrics: Dict[str, Any],
) -> None:
    if not obs_nodes:
        return
    actuator = None
    for name in ("motor_actuator", "fixed_group_actuator", "actuator"):
        candidate = getattr(nx, name, None)
        if candidate is not None:
            actuator = candidate
            break
    if actuator is None:
        return

    try:
        result = _call_observe_nodes(actuator, obs_nodes, int(step), metrics)
    except Exception:
        return
    if result is None:
        return

    if isinstance(result, dict):
        trace_record = dict(result)
        emitted = trace_record.pop("emitted", [])
    else:
        trace_record = {"result": repr(result)}
        emitted = []

    if isinstance(emitted, dict):
        emitted = [emitted]
    try:
        emitted_list = [dict(ev) for ev in (emitted or []) if isinstance(ev, dict)]
    except Exception:
        emitted_list = []

    trace_record.update(
        {
            "tick": int(step),
            "obs_nodes_count": int(len(obs_nodes)),
            "obs_nodes_unique": int(len(set(obs_nodes))),
            "obs_nodes_sample": _bounded_ints(obs_nodes, limit=32),
            "emitted_count": int(len(emitted_list)),
        }
    )
    _record_motor_trace(nx, "record_actuator_trace", trace_record)

    utd = getattr(nx, "utd", None)
    for event in emitted_list:
        event.setdefault("tick", int(step))
        _record_motor_trace(nx, "record_witness_event", event)
        try:
            emit = getattr(utd, "emit_motor_event", None)
            if emit is not None:
                emit(dict(event))
        except Exception:
            continue


def run_loop(nx: Any, t0: float, step: int, duration_s: Optional[int] = None) -> int:
    """
    Execute the main tick loop on the provided Nexus-like object.
    """
    try:
        # Lazy-init CoreEngine seam (telemetry-only additions; parity preserved)
        if getattr(nx, "_engine", None) is None:
            try:
                nx._engine = _CoreEngine(nx)
            except Exception:
                nx._engine = None

        # Lazy-init VOID cold scout (enabled by config scouts.enable_cold_probe)
        if getattr(nx, "_void_scout", None) is None:
            if config_bool("scouts.enable_cold_probe", True):
                try:
                    _sv = config_int("scouts.visits", int(getattr(nx, "scout_visits", config_int("scouts.visits", 16))))
                except Exception:
                    _sv = config_int("scouts.visits", 16)
                try:
                    _se = config_int("scouts.edges", int(getattr(nx, "scout_edges", config_int("scouts.edges", 8))))
                except Exception:
                    _se = config_int("scouts.edges", 8)
                try:
                    _seed = int(getattr(nx, "seed", 0))
                except Exception:
                    _seed = 0
                try:
                    nx._void_scout = _VoidScout(budget_visits=max(0, _sv), budget_edges=max(0, _se), seed=_seed)
                except Exception:
                    nx._void_scout = None

        # Lazy-init event-driven metrics aggregator (enabled by config events.event_metrics)
        if getattr(nx, "_evt_metrics", None) is None:
            if config_bool("events.event_metrics", True):
                try:
                    det = getattr(nx, "b1_detector", None)
                    z_spike = float(getattr(det, "z_spike", 1.0)) if det is not None else 1.0
                    hysteresis = float(getattr(det, "hysteresis", 1.0)) if det is not None else 1.0
                    half_life = int(getattr(nx, "b1_half_life_ticks", 50))
                    seed = int(getattr(nx, "seed", 0))
                    nx._evt_metrics = _EvtMetrics(
                        z_half_life_ticks=max(1, half_life),
                        z_spike=z_spike,
                        hysteresis=hysteresis,
                        seed=seed,
                    )
                except Exception:
                    nx._evt_metrics = None

        # Start status HTTP endpoint only when configured; idempotent; safe no-op on error.
        try:
            _maybe_start_status_http(nx)
        except Exception:
            pass

        # Ensure connectome publishes Observations to the runtime bus for ADC/cycles/B1
        # Without this attachment, cycle_hit/region_stat announcements never reach tick_fold(),
        # leaving adc_cycle_hits at 0 -> complexity_cycles stays 0 -> b1_z remains flatlined.
        try:
            C = getattr(nx, "connectome", None)
            b = getattr(nx, "bus", None)
            if C is not None and b is not None:
                setattr(C, "bus", b)
        except Exception:
            pass

        while True:
            # micro-profiler: high-resolution clock
            try:
                _pc = time.perf_counter
            except Exception:
                _pc = time.time
            _t0 = _pc()
            tick_start = time.time()
            obs_nodes_for_motor: List[int] = []

            # 1) ingest
            msgs = nx.ute.poll()
            ute_in_count = len(msgs)
            ute_text_count, stim_idxs, tick_rev_map = _process_messages(nx, msgs)

            # inject the accumulated stimulation before the learning step
            if stim_idxs:
                try:
                    stim_nodes = sorted(int(i) for i in stim_idxs)
                    stim_amp = float(getattr(nx, "stim_amp", 0.05))
                    nx.connectome.stimulate_indices(stim_nodes, amp=stim_amp)
                    _record_motor_trace(
                        nx,
                        "record_stimulation",
                        {
                            "tick": int(step),
                            "stim_count": int(len(stim_nodes)),
                            "stim_hash": _hash_ints(stim_nodes),
                            "stim_nodes_sample": _bounded_ints(stim_nodes, limit=32),
                            "amp": float(stim_amp),
                            "ute_in_count": int(ute_in_count),
                        },
                    )
                except Exception:
                    pass

            # Control plane: poll external phase control (file: runs/<ts>/phase.json)
            try:
                nx._poll_control()
            except Exception:
                pass

            # 2) SIE drive + update connectome
            # use wall-clock seconds since start as t
            t = time.time() - t0
            _t1 = _pc()

            # Decoder-side novelty scaling has been removed; keep dynamics neutral.
            novelty_scale = 1.0

            # Compute step and scan-based metrics (parity-preserving)
            m, drive = _compute_step_and_metrics(nx, t, step, novelty_scale=novelty_scale)

            # 3) telemetry fold (bus drain + ADC + optional event metrics + B1)
            void_topic_symbols: Set[Any] = set()
            _t2 = _pc()
            try:
                m, vts = _tick_fold(
                    nx,
                    m,
                    drive,
                    float(m.get("td_signal", 0.0)),  # td_signal produced by stepper
                    int(step),
                    tick_rev_map,
                    obs_to_events=_obs_to_events,
                    adc_event=_adc_event,
                    apply_b1=_apply_b1d,
                )
                try:
                    if isinstance(vts, set):
                        void_topic_symbols |= vts
                except Exception:
                    pass
                try:
                    obs_batch = getattr(nx, "_last_obs_batch", None) or []
                    obs_nodes_for_motor = _observation_nodes(obs_batch)
                    if obs_nodes_for_motor:
                        _record_motor_trace(
                            nx,
                            "record_efferent_dynamics",
                            {
                                "tick": int(step),
                                "obs_count": int(len(obs_batch)),
                                "obs_nodes_count": int(len(obs_nodes_for_motor)),
                                "obs_nodes_unique": int(len(set(obs_nodes_for_motor))),
                                "obs_nodes_hash": _hash_ints(obs_nodes_for_motor),
                                "obs_nodes_sample": _bounded_ints(obs_nodes_for_motor, limit=32),
                            },
                        )
                except Exception:
                    obs_nodes_for_motor = []
            except Exception:
                pass

            # 3a) Fold cohesion territories (event-folded union-find; no scans)
            try:
                terr = getattr(nx, "_territories", None)
                if terr is None:
                    try:
                        from vdm_rt.core.proprioception.territory import TerritoryUF as _TerrUF  # lazy import
                        try:
                            head_k = config_int("territory.head_k", 512)
                        except Exception:
                            head_k = config_int("territory.head_k", 512)
                        nx._territories = _TerrUF(head_k=int(max(8, head_k)))
                        terr = nx._territories
                    except Exception:
                        terr = None
                if terr is not None:
                    batch = getattr(nx, "_last_obs_batch", None)
                    if batch:
                        try:
                            terr.fold(batch)
                        except Exception:
                            pass
            except Exception:
                pass

            # 3b) Fold VOID cold-scout events into event-driven metrics (if aggregator present and no CoreEngine)
            try:
                if getattr(nx, "_engine", None) is None:
                    evtm = getattr(nx, "_evt_metrics", None)
                    scout = getattr(nx, "_void_scout", None)
                    if evtm is not None and scout is not None:
                        _evs = []
                        try:
                            _evs = scout.step(nx.connectome, int(step)) or []
                        except Exception:
                            _evs = []
                        for _ev in _evs:
                            try:
                                evtm.update(_ev)
                            except Exception:
                                pass
                        try:
                            _evsnap2 = evtm.snapshot()
                            if isinstance(_evsnap2, dict):
                                # Merge event-driven metrics without overriding canonical scan-based fields.
                                for _k, _v in _evsnap2.items():
                                    try:
                                        # Preserve existing B1 detector outputs from apply_b1 in the canonical keys.
                                        if str(_k).startswith("b1_") and _k in m:
                                            continue
                                        m[f"evt_{_k}"] = _v
                                    except Exception:
                                        continue
                        except Exception:
                            pass
            except Exception:
                pass
            # 3c) CoreEngine folding and snapshot merge (evt_* only; preserve canonical fields)
            try:
                eng = getattr(nx, "_engine", None)
                if eng is not None:
                    # Collect core events from drained observations and ADC metrics
                    evs = []
                    # Scouts: event-only, run once per tick under micro-budget (no schedulers)
                    try:
                        # Prepare bounded map heads for local routing (no scans)
                        maps_for_scouts = {}
                        try:
                            hm = getattr(eng, "_heat_map", None)
                            if hm is not None:
                                ms = hm.snapshot() or {}
                                if isinstance(ms, dict):
                                    maps_for_scouts.update(ms)
                        except Exception:
                            pass
                        try:
                            em = getattr(eng, "_exc_map", None)
                            if em is not None:
                                ms = em.snapshot() or {}
                                if isinstance(ms, dict):
                                    maps_for_scouts.update(ms)
                        except Exception:
                            pass
                        try:
                            im = getattr(eng, "_inh_map", None)
                            if im is not None:
                                ms = im.snapshot() or {}
                                if isinstance(ms, dict):
                                    maps_for_scouts.update(ms)
                        except Exception:
                            pass
                        try:
                            cm = getattr(eng, "_cold_map", None)
                            if cm is not None:
                                ms = cm.snapshot() or {}
                                if isinstance(ms, dict):
                                    maps_for_scouts.update(ms)
                        except Exception:
                            pass
                        # Memory and Trail steering fields (bounded; no scans)
                        try:
                            mm = getattr(eng, "_memory_map", None)
                            if mm is not None:
                                ms = mm.snapshot() or {}
                                if isinstance(ms, dict):
                                    maps_for_scouts.update(ms)
                        except Exception:
                            pass
                        try:
                            tm = getattr(eng, "_trail_map", None)
                            if tm is not None:
                                ms = tm.snapshot() or {}
                                if isinstance(ms, dict):
                                    maps_for_scouts.update(ms)
                        except Exception:
                            pass

                        # Seeds from recent stimulation (bounded)
                        try:
                            _seed_cap = config_int("scouts.seed_max", 64)
                        except Exception:
                            _seed_cap = config_int("scouts.seed_max", 64)
                        try:
                            seeds = sorted({int(s) for s in (stim_idxs or []) if isinstance(s, int)})[: max(0, _seed_cap)]
                        except Exception:
                            seeds = []

                        # Budgets (bounded)
                        try:
                            sv = config_int("scouts.visits", int(getattr(nx, "scout_visits", config_int("scouts.visits", 16))))
                        except Exception:
                            sv = config_int("scouts.visits", 16)
                        try:
                            se = config_int("scouts.edges", int(getattr(nx, "scout_edges", config_int("scouts.edges", 8))))
                        except Exception:
                            se = config_int("scouts.edges", 8)
                        try:
                            ttlv = config_int("scouts.ttl", 64)
                        except Exception:
                            ttlv = config_int("scouts.ttl", 64)
                        budget = {
                            "visits": max(0, sv),
                            "edges": max(0, se),
                            "ttl": max(1, ttlv),
                            "tick": int(step),
                            "seeds": list(seeds),
                        }

                        # Per-tick micro time budget across all scouts (µs)
                        try:
                            max_us = config_int("scouts.max_us", 2000)
                        except Exception:
                            max_us = 2000

                        scouts_list = []
                        # Per-scout config toggles (void-faithful; default on)
                        if config_bool("scouts.types.heat", True):
                            scouts_list.append(HeatScout())
                        if config_bool("scouts.types.cold", True):
                            scouts_list.append(ColdScout())
                        if config_bool("scouts.types.excitation", True):
                            scouts_list.append(ExcitationScout())
                        if config_bool("scouts.types.inhibition", True):
                            scouts_list.append(InhibitionScout())
                        if config_bool("scouts.types.void_ray", True):
                            scouts_list.append(VoidRayScout())
                        if config_bool("scouts.types.memory_ray", True):
                            scouts_list.append(MemoryRayScout())
                        if config_bool("scouts.types.frontier", True):
                            scouts_list.append(FrontierScout())
                        if config_bool("scouts.types.cycle", True):
                            scouts_list.append(CycleHunterScout())
                        if config_bool("scouts.types.sentinel", True):
                            scouts_list.append(SentinelScout())

                        scout_evs = _run_scouts_once(
                            getattr(nx, "connectome", None),
                            scouts_list,
                            maps=maps_for_scouts,
                            budget=budget,
                            bus=None,        # do not publish directly; fold via engine below
                            max_us=max_us,
                        ) or []
                        if scout_evs:
                            evs.extend(scout_evs)
                    except Exception:
                        pass
                    try:
                        batch = getattr(nx, "_last_obs_batch", None)
                        if batch is not None:
                            for _ev in _obs_to_events(batch) or []:
                                evs.append(_ev)
                    except Exception:
                        pass
                    try:
                        adc_metrics = getattr(nx, "_last_adc_metrics", None)
                        if isinstance(adc_metrics, dict):
                            evs.append(_adc_event(adc_metrics, int(step)))
                    except Exception:
                        pass
                    # Step the core engine with events (telemetry-only; no behavior change)
                    # Ensure memory field/map/trail exist (single owner; views only) and fold events
                    try:
                        # Owner field (physics): single source of truth for m[i]
                        if getattr(eng, "_memory_field", None) is None:
                            try:
                                seed_m = int(getattr(nx, "seed", 0))
                            except Exception:
                                seed_m = 0
                            try:
                                hk = int(getattr(nx, "cold_head_k", config_int("maps.head_k", 256)))
                            except Exception:
                                hk = config_int("maps.head_k", 256)
                            try:
                                eng._memory_field = MemoryField(head_k=max(8, hk), seed=seed_m)
                                # Attach to connectome for local, O(1) reads via getters
                                try:
                                    C = getattr(nx, "connectome", None)
                                    if C is not None:
                                        setattr(C, "_memory_field", eng._memory_field)
                                except Exception as e:
                                    if STRICT:
                                        raise
                            except Exception as e:
                                if STRICT:
                                    raise
                        # View adapter (bounded head/dict for scouts/UI)
                        if getattr(eng, "_memory_map", None) is None:
                            try:
                                hk = int(getattr(nx, "cold_head_k", config_int("maps.head_k", 256)))
                            except Exception:
                                hk = config_int("maps.head_k", 256)
                            eng._memory_map = MemoryMap(field=getattr(eng, "_memory_field", None), head_k=max(8, hk))
                            try:
                                C = getattr(nx, "connectome", None)
                                if C is not None:
                                    setattr(C, "_memory_map", eng._memory_map)
                            except Exception as e:
                                if STRICT:
                                    raise
                        # Trail map (short half-life, repulsion)
                        if getattr(eng, "_trail_map", None) is None:
                            try:
                                hk = int(getattr(nx, "cold_head_k", config_int("maps.head_k", 256)))
                            except Exception:
                                hk = config_int("maps.head_k", 256)
                            try:
                                hl2 = int(getattr(nx, "cold_half_life_ticks", config_int("maps.half_life_ticks", 200)))
                            except Exception:
                                hl2 = config_int("maps.half_life_ticks", 200)
                            try:
                                trail_hl = int(getattr(nx, "trail_half_life_ticks", config_int("maps.trail_half_life_ticks", max(1, hl2 // 4))))
                            except Exception:
                                trail_hl = config_int("maps.trail_half_life_ticks", max(1, hl2 // 4))
                            eng._trail_map = TrailMap(head_k=max(8, hk), half_life_ticks=max(1, trail_hl), seed=int(getattr(nx, "seed", 0)) + 5)
                        # Fold current events into memory/trail (bounded; no scans)
                        try:
                            # Prefer owner field for folding; MemoryMap remains a delegating view
                            mf = getattr(eng, "_memory_field", None)
                            mm = getattr(eng, "_memory_map", None)
                            if mm is not None and mf is not None:
                                try:
                                    # Ensure view delegates to owner
                                    if getattr(mm, "field", None) is None:
                                        setattr(mm, "field", mf)
                                except Exception:
                                    pass
                            if mf is not None:
                                mf.fold(evs, int(step))
                            elif mm is not None:
                                # Proxy mode: fold via map if owner missing
                                mm.fold(evs, int(step))
                        except Exception as e:
                            if STRICT:
                                raise
                        try:
                            tm = getattr(eng, "_trail_map", None)
                            if tm is not None:
                                tm.fold(evs, int(step))
                        except Exception as e:
                            if STRICT:
                                raise
                    except Exception as e:
                        if STRICT:
                            raise

                    try:
                        dt_ms = int(max(1, float(getattr(nx, "dt", config_float("runtime.default_dt_seconds", 0.1))) * 1000.0))
                    except Exception:
                        dt_ms = int(max(1, config_float("runtime.default_dt_seconds", 0.1) * 1000.0))
                    try:
                        eng.step(dt_ms, evs)
                    except Exception:
                        pass
                    # Merge engine snapshot under evt_* without overriding canonical fields
                    try:
                        esnap = eng.snapshot()
                        if isinstance(esnap, dict):
                            for _k, _v in esnap.items():
                                try:
                                    # Preserve existing B1 detector outputs from apply_b1 in the canonical keys.
                                    if str(_k).startswith("b1_") and _k in m:
                                        continue
                                    if str(_k).startswith("evt_"):
                                        m[_k] = _v
                                    else:
                                        m[f"evt_{_k}"] = _v
                                except Exception:
                                    continue
                    except Exception:
                        pass
            except Exception:
                pass

            # 3d) Optional actuator boundary. If a real actuator object is attached,
            # observe the current tick's node activity and emit witness/UTD rows.
            try:
                _maybe_observe_motor_actuator(nx, int(step), obs_nodes_for_motor, m)
            except Exception:
                pass

            # Attach SIE top-level fields and components (parity)
            try:
                m["sie_total_reward"] = float(drive.get("total_reward", 0.0))
                m["sie_valence_01"] = float(drive.get("valence_01", 0.0))
            except Exception:
                pass
            # Homeostasis counters from sparse maintenance/bridging (telemetry-only)
            try:
                m["homeostasis_pruned"] = int(getattr(nx.connectome, "_last_pruned_count", 0))
                m["homeostasis_bridged"] = int(getattr(nx.connectome, "_last_bridged_count", 0))
            except Exception:
                pass
            comps = drive.get("components", {})
            try:
                items = comps.items() if isinstance(comps, dict) else []
                for k, v in items:
                    try:
                        m[f"sie_{k}"] = float(v)
                    except Exception:
                        try:
                            m[f"sie_{k}"] = int(v)
                        except Exception:
                            m[f"sie_{k}"] = str(v)
            except Exception:
                pass

            # Intrinsic SIE v2 (computed inside connectome)
            try:
                m["sie_v2_reward_mean"] = float(getattr(nx.connectome, "_last_sie2_reward", 0.0))
                m["sie_v2_valence_01"] = float(getattr(nx.connectome, "_last_sie2_valence", 0.0))
            except Exception:
                pass

            # current phase (control plane)
            try:
                m["phase"] = int(getattr(nx, "_phase", {}).get("phase", 0))
            except Exception:
                m["phase"] = 0

            # Emitter contexts
            m["tick"] = int(step)
            m["t"] = int(step)
            m["wall_time_s"] = float(tick_start)
            m["ts"] = float(tick_start)
            m["run_elapsed_s"] = max(0.0, float(tick_start) - float(t0))
            m["ute_in_count"] = int(ute_in_count)
            m["ute_text_count"] = int(ute_text_count)

            try:
                nx._emit_step = int(step)
                # include canonical valence fields for convenience
                m["sie_valence_01"] = float(m.get("sie_valence_01", m.get("sie_total_reward", 0.0)))
                nx._emit_last_metrics = dict(m)
            except Exception:
                pass

            # Append history and trim
            nx.history.append(m)
            try:
                max_keep = 20000  # keep at most 20k ticks
                trim_to = 10000   # trim down to 10k when exceeding
                if len(nx.history) > max_keep:
                    nx.history = nx.history[-trim_to:]
            except Exception:
                pass

            # Structured tick log (batchable via LOG_EVERY to reduce I/O)
            try:
                _log_every_cfg = config_int("runtime.log_every_override", 0)
                if _log_every_cfg > 0:
                    nx.log_every = int(max(1, _log_every_cfg))
            except Exception:
                pass
            if (step % int(getattr(nx, "log_every", 1))) == 0:
                try:
                    nx.logger.info("tick", extra={"extra": m})
                except Exception as e:
                    # fallback serialization and retry
                    try:
                        safe = {}
                        for kk, vv in m.items():
                            try:
                                if isinstance(vv, (float, int, str, bool)) or vv is None:
                                    safe[kk] = vv
                                else:
                                    safe[kk] = float(vv)
                            except Exception:
                                safe[kk] = str(vv)
                        nx.logger.info("tick", extra={"extra": safe})
                    except Exception:
                        try:
                            print("[nexus] tick_log_error", str(e), flush=True)
                        except Exception:
                            pass

            # Redis Streams publish (optional, bounded; no schedulers)
            try:
                _maybe_publish_status_redis(nx, m, int(step))
            except Exception:
                pass

            # Checkpointing + retention. Checkpoint write failures are fatal:
            # continuing after a configured retention failure makes the run state
            # look durable when it is not.
            _save_tick_checkpoint(nx, int(step))

            # micro-profiler finalize
            try:
                _t3 = _pc()
                nx.prof = {
                    "step": float(_t1 - _t0) if True else 0.0,
                    "fold": float(_t2 - _t1) if True else 0.0,
                    "metrics": float(_t3 - _t2) if True else 0.0,
                    "tick": float(_t3 - _t0) if True else 0.0,
                }
            except Exception:
                pass

            # 4) pacing
            step += 1
            elapsed = time.time() - tick_start
            sleep = max(0.0, float(getattr(nx, "dt", 0.1)) - elapsed)
            time.sleep(sleep)

            if duration_s is not None and (time.time() - t0) > duration_s:
                try:
                    nx.logger.info(
                        "nexus_duration_reached",
                        extra={
                            "extra": {
                                "tick": int(step),
                                "duration_s": int(duration_s),
                            }
                        },
                    )
                except Exception:
                    pass
                break
    finally:
        return int(step)


__all__ = ["run_loop"]
