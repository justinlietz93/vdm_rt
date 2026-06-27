#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, sys, time, hashlib, importlib.util, random, math
from pathlib import Path
from types import SimpleNamespace
from collections import Counter, defaultdict, deque
from typing import Any, Dict, List, Iterable, Optional, Tuple

OP_NAMES = [
    "SELECT", "HOLD", "RELEASE", "INHIBIT", "ADVANCE", "RETREAT", "SPLIT", "MERGE",
    "AMPLIFY", "DAMP", "COMPARE", "CORRECT", "COMMIT", "ABORT"
]
LANE_NAMES = [f"L{i}" for i in range(8)]

LEGAL_BASIC = [
    "Q chart A",
    "B overlap AB",
    "L boundary AB",
    "Q chart B",
    "overlap transfer AB BC",
    "L cycle close",
]
LEGAL_REWRITE = [
    "Q chart A",
    "B overlap AB",
    "Q chart B",
    "L boundary AB",
    "overlap transfer AB BC",
    "L cycle close",
]
LEGAL_THREE_CHART_LOOP = [
    "Q chart A",
    "B overlap AB",
    "L boundary AB",
    "Q chart B",
    "overlap transfer AB BC",
    "B overlap BC",
    "L boundary BC",
    "Q chart C",
    "overlap transfer BC CA",
    "B overlap CA",
    "L boundary CA",
    "overlap transfer CA AB",
    "L cycle close",
]
LEGAL_LATCH_RICH = [
    "Q chart A",
    "B overlap AB",
    "L boundary AB",
    "Q chart B",
    "B overlap BC",
    "L boundary BC",
    "Q chart C",
    "overlap transfer AB BC",
    "overlap transfer BC CA",
    "L cycle close",
]
BUILTIN_STREAMS = {
    "basic": [LEGAL_BASIC],
    "rewrite_mix": [LEGAL_BASIC, LEGAL_REWRITE],
    "three_chart": [LEGAL_BASIC, LEGAL_REWRITE, LEGAL_THREE_CHART_LOOP],
    "rich": [LEGAL_BASIC, LEGAL_REWRITE, LEGAL_THREE_CHART_LOOP, LEGAL_LATCH_RICH],
}
OPAQUE_MAP = {
    "Q": "x7", "B": "k4", "L": "t6", "chart": "m2", "overlap": "r9",
    "boundary": "h3", "transfer": "z5", "cycle": "c8", "close": "q0",
    "A": "a0", "BCHART": "b0", "C": "c0", "AB": "p1", "BC": "p2", "CA": "p3",
}

def bootstrap_vdm(repo: Path) -> None:
    repo = repo.resolve()
    init_py = repo / "__init__.py"
    if not init_py.exists():
        raise SystemExit(f"Could not find __init__.py in repo root: {repo}")
    if str(repo.parent) not in sys.path:
        sys.path.insert(0, str(repo.parent))
    if "vdm_rt" not in sys.modules:
        spec = importlib.util.spec_from_file_location("vdm_rt", str(init_py), submodule_search_locations=[str(repo)])
        if spec is None or spec.loader is None:
            raise SystemExit("Could not create vdm_rt import spec")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["vdm_rt"] = mod
        spec.loader.exec_module(mod)

def _u64(s: str) -> int:
    return int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(), "little", signed=False)

def deterministic_group(label: str, n: int, size: int, salt: str) -> List[int]:
    out: List[int] = []
    seen = set()
    j = 0
    while len(out) < max(1, int(size)):
        idx = int(_u64(f"{salt}|{label}|{j}") % max(1, int(n)))
        j += 1
        if idx in seen: continue
        seen.add(idx); out.append(idx)
    return out

def atom_to_indices(atom: str, n: int, group_size: int, max_units: int, salt: str) -> List[int]:
    atom = str(atom).strip()
    if not atom: return []
    toks = atom.split()
    labels: List[str] = [f"atom:{atom}"]
    for pos, tok in enumerate(toks[: int(max_units)]):
        labels.append(f"pos:{pos}:tok:{tok}")
        labels.append(f"tok:{tok}")
    idxs: List[int] = []
    seen = set()
    for lab in labels:
        for idx in deterministic_group(lab, n, group_size, salt):
            if idx not in seen:
                seen.add(idx); idxs.append(idx)
    return idxs

def sha_list(xs: Iterable[int]) -> str:
    h = hashlib.sha256()
    for x in xs:
        h.update(str(int(x)).encode()); h.update(b",")
    return h.hexdigest()[:16]

def append_jsonl(path: Path, rec: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")

def make_opaque(atom: str) -> str:
    out=[]
    for tok in atom.split():
        key = "BCHART" if tok == "B" and len(out) and out[-1] == "m2" else tok
        out.append(OPAQUE_MAP.get(key, f"u{_u64(tok)%97}"))
    return " ".join(out)

class CurriculumWorld:
    def __init__(self, curriculum: str, stream_file: Optional[Path], seed: int, reafference: bool, opaque: bool) -> None:
        self.rng = random.Random(int(seed))
        self.reafference_enabled = bool(reafference)
        self.reafference_queue: deque[str] = deque(maxlen=256)
        self.opaque = bool(opaque)
        if stream_file is not None:
            atoms = [ln.strip() for ln in Path(stream_file).read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.strip().startswith("#")]
            if not atoms: raise SystemExit(f"stream file has no atoms: {stream_file}")
            self.cycles = [atoms]
            self.name = f"file:{stream_file}"
        else:
            self.cycles = [list(cyc) for cyc in BUILTIN_STREAMS[str(curriculum)]]
            self.name = str(curriculum)
        if self.opaque:
            self.cycles = [[make_opaque(a) for a in cyc] for cyc in self.cycles]
            self.name += ":opaque"
        self._tick = 0
    def push_reafference(self, witness: str) -> None:
        if self.reafference_enabled:
            witness = str(witness).strip()
            if witness:
                self.reafference_queue.append(f"heard witness {witness}")
    def next_atom(self) -> Tuple[str, str, int, int]:
        if self.reafference_queue:
            atom = self.reafference_queue.popleft(); self._tick += 1
            return "reafference", atom, -1, -1
        cycle_idx = self._tick % len(self.cycles)
        cycle = self.cycles[cycle_idx]
        atom_idx = (self._tick // len(self.cycles)) % len(cycle)
        atom = cycle[atom_idx]
        self._tick += 1
        return "curriculum", atom, int(cycle_idx), int(atom_idx)

class ScanFirewall:
    def __init__(self, connectome: Any):
        self.connectome = connectome
        self.originals: Dict[str, Any] = {}
        self.forbidden = ["active_edge_count", "connected_components", "cyclomatic_complexity", "snapshot_graph", "connectome_entropy"]
    def __enter__(self):
        for name in self.forbidden:
            if hasattr(self.connectome, name):
                self.originals[name] = getattr(self.connectome, name)
                def _boom(*_a, _name=name, **_kw):
                    raise RuntimeError(f"SCAN_FIREWALL: forbidden graph scan called: {_name}")
                setattr(self.connectome, name, _boom)
        return self
    def __exit__(self, exc_type, exc, tb):
        for name, fn in self.originals.items(): setattr(self.connectome, name, fn)
        return False

class SelectorTraceController:
    """UTD-side selector manifold.

    It does not emit the private trace. It logs the private trace every tick.
    UTD emits only a compact witness when endogenous release/commit pressure crosses threshold.
    """
    def __init__(self, n:int, group_size:int, salt:str, op_threshold:float, lane_threshold:float,
                 release_threshold:float, decay:float, cooldown:int, run_dir:Path, current_op_min:int=2, current_lane_min:int=2) -> None:
        self.n=int(n); self.group_size=int(group_size); self.salt=salt
        self.op_threshold=float(op_threshold); self.lane_threshold=float(lane_threshold)
        self.release_threshold=float(release_threshold); self.decay=float(decay); self.cooldown=int(cooldown); self.current_op_min=int(current_op_min); self.current_lane_min=int(current_lane_min)
        self.op_groups={op:deterministic_group(f"selector_op:{op}", self.n, group_size, salt) for op in OP_NAMES}
        self.lane_groups={lane:deterministic_group(f"selector_lane:{lane}", self.n, group_size, salt) for lane in LANE_NAMES}
        self.node_to_ops=defaultdict(list); self.node_to_lanes=defaultdict(list)
        for op,nodes in self.op_groups.items():
            for node in nodes: self.node_to_ops[int(node)].append(op)
        for lane,nodes in self.lane_groups.items():
            for node in nodes: self.node_to_lanes[int(node)].append(lane)
        self.op_energy={op:0.0 for op in OP_NAMES}
        self.lane_energy={lane:0.0 for lane in LANE_NAMES}
        self.lane_hold={lane:0.0 for lane in LANE_NAMES}
        self.lane_inhibit={lane:0.0 for lane in LANE_NAMES}
        self.lane_release={lane:0.0 for lane in LANE_NAMES}
        self.lane_correct={lane:0.0 for lane in LANE_NAMES}
        self.last_emit=-10**12
        self.witness_count=0
        self.run_dir=Path(run_dir)
        with open(self.run_dir/"selector_group_map.json", "w", encoding="utf-8") as f:
            json.dump({"operation_groups":self.op_groups,"lane_groups":self.lane_groups}, f, indent=2)
    def observe(self, tick:int, nodes:Iterable[int], source_input:str, atom:str) -> dict:
        # Decay persistent pressures first.
        for d in [self.op_energy, self.lane_energy, self.lane_hold, self.lane_inhibit, self.lane_release, self.lane_correct]:
            for k in d: d[k] *= self.decay
        touched_ops=Counter(); touched_lanes=Counter()
        for node in nodes:
            node=int(node)
            for op in self.node_to_ops.get(node, []): touched_ops[op] += 1
            for lane in self.node_to_lanes.get(node, []): touched_lanes[lane] += 1
        for op,c in touched_ops.items(): self.op_energy[op] += float(c)
        for lane,c in touched_lanes.items(): self.lane_energy[lane] += float(c)
        active_ops=[op for op,c in touched_ops.items() if c >= self.current_op_min]
        active_lanes=[lane for lane,c in touched_lanes.items() if c >= self.current_lane_min]
        commands=[]
        if active_ops and active_lanes:
            # update control physiology from current tick coactivation; persistent energies are debug context only.
            sorted_ops=sorted(active_ops, key=lambda o:touched_ops[o], reverse=True)
            sorted_lanes=sorted(active_lanes, key=lambda l:touched_lanes[l], reverse=True)
            for lane in sorted_lanes[:3]:
                for op in sorted_ops[:4]:
                    amp = min(1.0, (touched_ops[op]/max(1,self.current_op_min) + touched_lanes[lane]/max(1,self.current_lane_min))/6.0)
                    commands.append({"op":op,"lane":lane,"amp":round(float(amp),4)})
                    if op in ("SELECT","ADVANCE","SPLIT","MERGE","AMPLIFY","COMPARE"):
                        self.lane_hold[lane] += 0.12*amp
                    if op == "HOLD":
                        self.lane_hold[lane] += 0.25*amp
                    if op == "INHIBIT":
                        self.lane_inhibit[lane] += 0.30*amp
                    if op in ("RELEASE","COMMIT"):
                        self.lane_release[lane] += 0.35*amp
                    if op == "CORRECT":
                        self.lane_correct[lane] += 0.35*amp
                    if op in ("DAMP","ABORT","RETREAT"):
                        self.lane_hold[lane] *= 0.65
                        self.lane_release[lane] *= 0.65
        # release gate: commits only when a lane has preparation plus release/commit pressure.
        emitted=[]
        strongest_lane=max(LANE_NAMES, key=lambda l:self.lane_hold[l] + self.lane_release[l])
        release_score = self.lane_hold[strongest_lane] + self.lane_release[strongest_lane] - 0.35*self.lane_inhibit[strongest_lane]
        commit_op_pressure = max(float(touched_ops.get("COMMIT",0)), float(touched_ops.get("RELEASE",0)))
        release_intent = ("COMMIT" in active_ops) or ("RELEASE" in active_ops)
        gate_pressure = release_score + 0.10*commit_op_pressure
        if release_intent and gate_pressure >= self.release_threshold and (tick-self.last_emit) >= self.cooldown:
            self.last_emit=tick
            self.witness_count += 1
            witness=f"W{strongest_lane[1:]}_{self.witness_count:04d}"
            emitted.append({
                "tick":int(tick), "witness":witness, "lane":strongest_lane,
                "gate_pressure":round(float(gate_pressure),4),
                "hold":round(float(self.lane_hold[strongest_lane]),4),
                "release":round(float(self.lane_release[strongest_lane]),4),
                "inhibit":round(float(self.lane_inhibit[strongest_lane]),4),
                "correct":round(float(self.lane_correct[strongest_lane]),4),
                "source_input":source_input, "source_atom":atom,
                "top_ops":self.top_ops(5), "top_lanes":self.top_lanes(5),
            })
            # executing the act consumes part of the prepared pressure; it is not the witness itself re-fed as trace.
            self.lane_hold[strongest_lane] *= 0.35
            self.lane_release[strongest_lane] *= 0.20
            self.lane_inhibit[strongest_lane] *= 0.70
        top_trace=sorted([{"lane":l,"hold":round(float(self.lane_hold[l]),4),"release":round(float(self.lane_release[l]),4),"inhibit":round(float(self.lane_inhibit[l]),4),"correct":round(float(self.lane_correct[l]),4),"energy":round(float(self.lane_energy[l]),4)} for l in LANE_NAMES], key=lambda r:r["hold"]+r["release"]+r["energy"], reverse=True)[:4]
        return {
            "active_ops":active_ops, "active_lanes":active_lanes,
            "commands":commands, "emitted":emitted,
            "top_ops":self.top_ops(6), "top_lanes":self.top_lanes(6), "top_trace":top_trace,
            "release_lane":strongest_lane, "release_score":round(float(release_score),4), "gate_pressure":round(float(gate_pressure),4),
            "op_touch_count":int(sum(touched_ops.values())), "lane_touch_count":int(sum(touched_lanes.values())),
        }
    def top_ops(self, k:int=5):
        return [[op, round(float(v),4)] for op,v in sorted(self.op_energy.items(), key=lambda kv:kv[1], reverse=True)[:k]]
    def top_lanes(self, k:int=5):
        return [[lane, round(float(v),4)] for lane,v in sorted(self.lane_energy.items(), key=lambda kv:kv[1], reverse=True)[:k]]


def build(args, run_dir:Path):
    bootstrap_vdm(args.repo)
    from vdm_rt.core.sparse_connectome import SparseConnectome
    from vdm_rt.core.bus import AnnounceBus
    from vdm_rt.core.adc import ADC
    from vdm_rt.core.engine import CoreEngine
    walkers = int(args.walkers) if args.walkers is not None else int(round(1.2*args.neurons))
    C = SparseConnectome(N=args.neurons, k=args.k, seed=args.seed, threshold=args.threshold,
                         lambda_omega=args.lambda_omega, candidates=args.candidates,
                         traversal_walkers=walkers, traversal_hops=args.hops)
    bus=AnnounceBus(capacity=args.bus_capacity); C.bus=bus
    adc=ADC()
    nx_like=SimpleNamespace(connectome=C, adc=adc, run_dir=str(run_dir), checkpoint_format="h5",
                            N=args.neurons, k=args.k, seed=args.seed, dt=1.0/max(1e-9,args.hz),
                            _emit_step=0, _phase={"phase":0}, scout_visits=args.scout_visits,
                            scout_edges=args.scout_edges, cold_head_k=args.cold_head_k,
                            cold_half_life_ticks=args.cold_half_life_ticks, b1_half_life_ticks=50,
                            b1_detector=SimpleNamespace(z_spike=1.0, hysteresis=1.0))
    eng=CoreEngine(nx_like)
    world=CurriculumWorld(args.curriculum, args.stream_file, args.seed, args.reafference, args.opaque)
    selector=SelectorTraceController(n=args.neurons, group_size=args.selector_group_size, salt=f"orthad-selector-v1:{args.seed}",
                                     op_threshold=args.op_threshold, lane_threshold=args.lane_threshold,
                                     release_threshold=args.release_threshold, decay=args.selector_decay,
                                     cooldown=args.release_cooldown, run_dir=run_dir, current_op_min=args.current_op_min, current_lane_min=args.current_lane_min)
    return C,bus,adc,nx_like,eng,world,selector

def category(atom:str)->str:
    if atom.startswith("heard witness"): return "self_consequence"
    toks=atom.split()
    if not toks: return "empty"
    if toks[0] == "Q" or toks[0] == "x7": return "Q chart"
    if "overlap" in toks or "r9" in toks:
        if "transfer" in toks or "z5" in toks: return "overlap transfer"
        return "B overlap"
    if "boundary" in toks or "h3" in toks: return "L boundary"
    if "cycle" in toks or "c8" in toks: return "L cycle close"
    return "other"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--neurons", type=int, default=1000)
    ap.add_argument("--walkers", type=int, default=1200)
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--hops", type=int, default=3)
    ap.add_argument("--candidates", type=int, default=64)
    ap.add_argument("--threshold", type=float, default=0.15)
    ap.add_argument("--lambda-omega", type=float, default=0.1)
    ap.add_argument("--domain-modulation", type=float, default=1.15625)
    ap.add_argument("--hz", type=float, default=10.0)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--ticks", type=int, default=260)
    ap.add_argument("--max-wall-s", type=float, default=120.0)
    ap.add_argument("--curriculum", choices=sorted(BUILTIN_STREAMS.keys()), default="rich")
    ap.add_argument("--stream-file", type=Path, default=None)
    ap.add_argument("--opaque", action="store_true")
    ap.add_argument("--reafference", action="store_true")
    ap.add_argument("--stim-group-size", type=int, default=4)
    ap.add_argument("--stim-max-units", type=int, default=8)
    ap.add_argument("--stim-amp", type=float, default=0.05)
    ap.add_argument("--selector-group-size", type=int, default=8)
    ap.add_argument("--op-threshold", type=float, default=16.0)
    ap.add_argument("--lane-threshold", type=float, default=14.0)
    ap.add_argument("--release-threshold", type=float, default=1.15)
    ap.add_argument("--current-op-min", type=int, default=2)
    ap.add_argument("--current-lane-min", type=int, default=2)
    ap.add_argument("--selector-decay", type=float, default=0.965)
    ap.add_argument("--release-cooldown", type=int, default=8)
    ap.add_argument("--bus-capacity", type=int, default=65536)
    ap.add_argument("--bus-drain", type=int, default=4096)
    ap.add_argument("--scout-visits", type=int, default=16)
    ap.add_argument("--scout-edges", type=int, default=8)
    ap.add_argument("--cold-head-k", type=int, default=256)
    ap.add_argument("--cold-half-life-ticks", type=int, default=200)
    ap.add_argument("--use-time-dynamics", action="store_true", default=True)
    ap.add_argument("--save-h5", action="store_true")
    args=ap.parse_args()
    args.repo=args.repo.resolve(); run_dir=args.run_dir.resolve(); run_dir.mkdir(parents=True, exist_ok=True)
    for name in ["ute_input_stream.jsonl","trace_log.jsonl","utd_events.jsonl","io_timeline.jsonl","tick_rows.csv","run_summary.json"]:
        p=run_dir/name
        if p.exists(): p.unlink()
    import numpy as np
    np.random.seed(args.seed)
    C,bus,adc,nx_like,eng,world,selector=build(args,run_dir)
    cfg=vars(args).copy(); cfg["mode"]="orthad_selector_trace_fresh_model_v1"; cfg["walker_ratio"]=args.walkers/max(1,args.neurons)
    (run_dir/"run_config.json").write_text(json.dumps(cfg, indent=2, default=str), encoding="utf-8")
    from vdm_rt.runtime.events_adapter import observations_to_events, adc_metrics_to_event
    fields=["tick","source","category","atom","stim_count","stim_hash","obs_count","obs_nodes_count","obs_nodes_unique","adc_territories","adc_boundaries","adc_cycle_hits","vt_visits","vt_unique","vt_coverage","vt_entropy","sie2_valence","sie_gate","active_ops","active_lanes","commands","witnesses","top_ops","top_lanes","top_trace","release_lane","release_score","gate_pressure","tick_s"]
    start=time.time(); completed=0
    source_counts=Counter(); input_counts=Counter(); category_counts=Counter(); witness_counts=Counter(); cat_witness=Counter(); op_by_cat=Counter(); lane_by_cat=Counter(); command_by_cat=Counter()
    with open(run_dir/"tick_rows.csv", "w", newline="", encoding="utf-8") as cf:
        writer=csv.DictWriter(cf, fieldnames=fields); writer.writeheader(); cf.flush()
        with ScanFirewall(C):
            for tick in range(args.ticks):
                if time.time()-start > args.max_wall_s: break
                tt0=time.perf_counter()
                source, atom, cyc, ai = world.next_atom(); cat=category(atom)
                stim=atom_to_indices(atom, args.neurons, args.stim_group_size, args.stim_max_units, salt=f"orthad-input-selector-v1:{args.seed}")
                append_jsonl(run_dir/"ute_input_stream.jsonl", {"tick":tick,"source":source,"category":cat,"cycle_index":cyc,"atom_index":ai,"atom":atom,"stim_count":len(stim),"stim_hash":sha_list(stim)})
                source_counts[source]+=1; input_counts[atom]+=1; category_counts[cat]+=1
                if stim: C.stimulate_indices(stim, amp=args.stim_amp)
                sie2=float(getattr(C,"_last_sie2_valence",0.0) or 0.0); sie_gate=max(0.35,min(1.0,sie2 if sie2>0.0 else 1.0))
                C.step(tick/max(1e-9,args.hz), domain_modulation=args.domain_modulation, sie_drive=sie_gate, use_time_dynamics=args.use_time_dynamics)
                obs=bus.drain(args.bus_drain); adc.update_from(obs); adc_m=adc.get_metrics()
                evs=observations_to_events(obs); evs.append(adc_metrics_to_event(adc_m,tick)); nx_like._emit_step=tick; eng.step(int(max(1,nx_like.dt*1000.0)), evs)
                obs_nodes=[]
                for o in obs:
                    try: obs_nodes.extend([int(x) for x in (getattr(o,"nodes",[]) or [])])
                    except Exception: pass
                sel=selector.observe(tick, obs_nodes, source, atom)
                for cmd in sel["commands"]:
                    op_by_cat[(cat,cmd["op"])] += 1
                    lane_by_cat[(cat,cmd["lane"])] += 1
                    command_by_cat[(cat,cmd["op"],cmd["lane"])] += 1
                for ev in sel["emitted"]:
                    append_jsonl(run_dir/"utd_events.jsonl", ev)
                    witness_counts[ev["lane"]]+=1; cat_witness[(cat,ev["lane"])] += 1
                    world.push_reafference(ev["witness"])
                findings=dict(getattr(C,"findings",{}) or {})
                rec={"tick":tick,"source":source,"category":cat,"atom":atom,"stim_count":len(stim),"stim_hash":sha_list(stim),"obs_count":len(obs),"obs_nodes_count":len(obs_nodes),"obs_nodes_unique":len(set(obs_nodes)),"adc_territories":int(adc_m.get("adc_territories",0)),"adc_boundaries":int(adc_m.get("adc_boundaries",0)),"adc_cycle_hits":int(adc_m.get("adc_cycle_hits",0)),"vt_visits":int(findings.get("vt_visits",0)),"vt_unique":int(findings.get("vt_unique",0)),"vt_coverage":float(findings.get("vt_coverage",0.0)),"vt_entropy":float(findings.get("vt_entropy",0.0)),"sie2_valence":float(getattr(C,"_last_sie2_valence",0.0) or 0.0),"sie_gate":sie_gate,"active_ops":" ".join(sel["active_ops"]),"active_lanes":" ".join(sel["active_lanes"]),"commands":json.dumps(sel["commands"]),"witnesses":" ".join(ev["witness"] for ev in sel["emitted"]),"top_ops":json.dumps(sel["top_ops"]),"top_lanes":json.dumps(sel["top_lanes"]),"top_trace":json.dumps(sel["top_trace"]),"release_lane":sel["release_lane"],"release_score":sel["release_score"],"gate_pressure":sel["gate_pressure"],"tick_s":float(time.perf_counter()-tt0)}
                writer.writerow(rec); cf.flush()
                append_jsonl(run_dir/"trace_log.jsonl", {"tick":tick,"source":source,"category":cat,"atom":atom,"selector":sel})
                append_jsonl(run_dir/"io_timeline.jsonl", rec)
                completed=tick+1
    final_h5=None
    if args.save_h5:
        try:
            from vdm_rt.core.memory import save_checkpoint
            final_h5=str(save_checkpoint(str(run_dir), completed, C, fmt="h5", adc=adc))
        except Exception as e:
            final_h5="SAVE_FAILED: "+repr(e)
    # summaries
    total_by_cat=Counter(); witness_by_cat=Counter()
    for (cat,lane),c in cat_witness.items(): witness_by_cat[cat]+=c
    category_summary=[]
    for cat,c in category_counts.most_common():
        category_summary.append({"category":cat,"input_ticks":c,"witnesses":witness_by_cat[cat],"witness_rate":round(witness_by_cat[cat]/max(1,c),4)})
    summary={"run_dir":str(run_dir),"mode":"orthad_selector_trace_fresh_model_v1","neurons":args.neurons,"walkers":args.walkers,"ticks_requested":args.ticks,"ticks_completed":completed,"elapsed_s":time.time()-start,"mean_wall_tick_s":(time.time()-start)/max(1,completed),"source_counts":dict(source_counts),"category_summary":category_summary,"top_inputs":input_counts.most_common(30),"witness_count":sum(witness_counts.values()),"witness_by_lane":dict(witness_counts),"top_category_lane_witness":[{"category":cat,"lane":lane,"count":c} for (cat,lane),c in cat_witness.most_common(30)],"top_category_ops":[{"category":cat,"op":op,"count":c} for (cat,op),c in op_by_cat.most_common(40)],"top_category_lanes":[{"category":cat,"lane":lane,"count":c} for (cat,lane),c in lane_by_cat.most_common(40)],"top_category_commands":[{"category":cat,"op":op,"lane":lane,"count":c} for (cat,op,lane),c in command_by_cat.most_common(40)],"final_h5":final_h5,"scan_firewall":"passed"}
    (run_dir/"run_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    # write csv summaries
    with open(run_dir/"category_summary.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=["category","input_ticks","witnesses","witness_rate"]); w.writeheader(); w.writerows(category_summary)
    with open(run_dir/"first120_io.txt","w",encoding="utf-8") as f:
        for line in list(open(run_dir/"io_timeline.jsonl",encoding="utf-8"))[:120]:
            r=json.loads(line); acts=r.get("commands","[]"); wits=r.get("witnesses","")
            cmds=json.loads(acts) if acts else []
            cmdtxt=" ".join(f"{c['op']}:{c['lane']}" for c in cmds[:4])
            suffix=(" -> "+cmdtxt if cmdtxt else "") + ((" | WIT "+wits) if wits else "")
            f.write(f"{r['tick']:03d} [{r['source']}/{r['category']}] {r['atom']}{suffix}\n")
    print(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
