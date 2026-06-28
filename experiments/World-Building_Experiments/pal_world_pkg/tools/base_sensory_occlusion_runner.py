#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, sys, time, hashlib, importlib.util, random, re
from pathlib import Path
from types import SimpleNamespace
from collections import Counter, defaultdict, deque
from typing import Any, Dict, List, Iterable, Optional, Tuple

# Experimental accumulated intention-trace readout
try:
    from intention_trace_translator import IntentionTraceTranslatorSet, append_jsonl as append_intent_jsonl, write_csv as write_intent_csv
except Exception:
    IntentionTraceTranslatorSet = None
    append_intent_jsonl = None
    write_intent_csv = None

OP_NAMES = [
    "SELECT", "HOLD", "RELEASE", "INHIBIT", "ADVANCE", "RETREAT", "SPLIT", "MERGE",
    "AMPLIFY", "DAMP", "COMPARE", "CORRECT", "COMMIT", "ABORT"
]
LANE_NAMES = [f"L{i}" for i in range(8)]
AP_NAMES = [
    "AP_RELAX", "AP_WHOLE", "AP_SPAN", "AP_PAIR", "AP_POSITION", "AP_CHAR", "AP_PUNCT", "AP_SHAPE",
    "AP_WIDEN", "AP_NARROW", "AP_CLOSE", "AP_OPEN"
]
LAYER_ORDER = ["relaxed", "whole", "span", "pair", "position", "char", "punct"]

STABLE_SENTENCES = [
    "The bridge holds while the signal crosses.",
    "The signal waits until the bridge is steady.",
    "The path remains open while the marker moves.",
    "The boundary holds before the transfer begins.",
]
NOISY_SENTENCES = [
    "xq7 miv ru19 pz8 loma qx",
    "delta spoon violet hinge under glass",
    "The quote opens but never closes",
    "A bracket opens while the sentence keeps moving",
    "bridge the crosses signal while holds",
]
RETURN_SENTENCES = [
    "The bridge holds while the signal crosses.",
    "The boundary holds before the transfer begins.",
    "The signal waits until the bridge is steady.",
]

def bootstrap_vdm(repo: Path) -> None:
    repo = repo.resolve(); init_py = repo / "__init__.py"
    if not init_py.exists(): raise SystemExit(f"missing repo __init__.py: {repo}")
    if str(repo.parent) not in sys.path: sys.path.insert(0, str(repo.parent))
    if "vdm_rt" not in sys.modules:
        spec = importlib.util.spec_from_file_location("vdm_rt", str(init_py), submodule_search_locations=[str(repo)])
        if spec is None or spec.loader is None: raise SystemExit("could not import vdm_rt")
        mod = importlib.util.module_from_spec(spec); sys.modules["vdm_rt"] = mod; spec.loader.exec_module(mod)

def _u64(s: str) -> int:
    return int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(), "little", signed=False)

def deterministic_group(label: str, n: int, size: int, salt: str) -> List[int]:
    out=[]; seen=set(); j=0
    while len(out) < max(1,int(size)):
        idx = int(_u64(f"{salt}|{label}|{j}") % max(1,int(n))); j+=1
        if idx not in seen: seen.add(idx); out.append(idx)
    return out

def sha_list(xs: Iterable[int]) -> str:
    h=hashlib.sha256()
    for x in xs:
        h.update(str(int(x)).encode()); h.update(b",")
    return h.hexdigest()[:16]

def append_jsonl(path: Path, rec: dict) -> None:
    with open(path,"a",encoding="utf-8") as f: f.write(json.dumps(rec,ensure_ascii=False,sort_keys=True)+"\n")

def norm_atom(atom: str) -> str:
    return re.sub(r"\s+", " ", str(atom).strip())

def tokenize(atom: str) -> List[str]:
    return re.findall(r"[\w]+|[^\w\s]", atom, flags=re.UNICODE)

def simple_shape(tok: str) -> str:
    out=[]
    for ch in tok:
        if ch.isupper(): out.append('A')
        elif ch.islower(): out.append('a')
        elif ch.isdigit(): out.append('0')
        else: out.append('p')
    c=[]
    for x in out:
        if not c or c[-1]!=x: c.append(x)
    return ''.join(c)[:12] or 'empty'

def highres_features(atom: str, max_units: int=10, char_budget: int=16) -> Dict[str,List[str]]:
    atom=norm_atom(atom); toks=tokenize(atom); lows=[t.lower() for t in toks]
    layers={k:[] for k in ["whole","norm","span","position","shape","pair","char","punct","dark"]}
    layers["whole"].append(f"atom:{atom}")
    layers["norm"].append(f"atom_lower:{atom.lower()}")
    layers["shape"].append(f"token_count:{min(24,len(toks))}")
    layers["shape"].append(f"shape_seq:{'-'.join(simple_shape(t) for t in toks[:max_units])}")
    if toks and all(len(t)==1 and not t.isalnum() for t in toks[-1:]):
        layers["punct"].append(f"terminal_punct:{toks[-1]}")
    char_added=0
    for i,(tok,low) in enumerate(zip(toks[:max_units], lows[:max_units])):
        layers["span"].append(f"span:{low}")
        layers["position"].append(f"atompos:{i}:span:{low}")
        layers["shape"].append(f"span_shape:{simple_shape(tok)}")
        layers["shape"].append(f"atompos:{i}:shape:{simple_shape(tok)}")
        layers["shape"].append(f"span_len:{min(16,len(tok))}")
        if len(low)>0:
            layers["char"].append(f"span_first:{low[0]}")
            layers["position"].append(f"atompos:{i}:first:{low[0]}")
        if len(low)>1:
            layers["char"].append(f"span_last:{low[-1]}")
            layers["position"].append(f"atompos:{i}:last:{low[-1]}")
        for j,ch in enumerate(low[:8]):
            if char_added >= char_budget: break
            if not ch.isalnum():
                layers["punct"].append(f"span:{low}:punctpos:{j}:{ch}")
            else:
                layers["char"].append(f"span:{low}:charpos:{j}:{ch}")
            char_added += 1
    for i in range(max(0,min(len(lows)-1,max_units-1))):
        a,b=lows[i],lows[i+1]
        layers["pair"].append(f"spanpair:{a}|{b}")
        layers["position"].append(f"atompos:{i}-{i+1}:spanpair:{a}|{b}")
    for ch in atom:
        if not ch.isalnum() and not ch.isspace():
            layers["punct"].append(f"punct:{ch}")
    layers["dark"] = ["ute_dark_field", "ute_occluded", f"dark_len_bucket:{min(12, len(atom)//8)}"]
    # dedupe preserving order
    for k,vals in list(layers.items()):
        seen=set(); out=[]
        for v in vals:
            if v not in seen: seen.add(v); out.append(v)
        layers[k]=out
    return layers

class SensoryAperture:
    """Model-actuated receptor aperture with sensory occlusion actuator.

    UTE uses the previous aperture state to weight feature layers. UTD aperture groups update the next state.
    If AP_CLOSE is held above threshold for close_hold_ticks, occlusion level moves closed.
    When close pressure drops, aperture reopens one notch per tick.
    """
    def __init__(self, n:int, salt:str, group_size:int=8, current_min:int=2, close_hold_ticks:int=2, max_occlusion:int=3) -> None:
        self.n=int(n); self.salt=str(salt); self.group_size=int(group_size); self.current_min=int(current_min)
        self.close_hold_ticks=int(close_hold_ticks); self.max_occlusion=int(max_occlusion)
        self.ap_groups={ap:deterministic_group(f"aperture:{ap}", self.n, self.group_size, self.salt) for ap in AP_NAMES}
        self.node_to_ap=defaultdict(list)
        for ap,nodes in self.ap_groups.items():
            for node in nodes: self.node_to_ap[int(node)].append(ap)
        self.ap_energy={ap:0.0 for ap in AP_NAMES}
        self.energy_decay=0.965
        self.level=0  # 0 relaxed, 1 whole, 2 span, 3 pair, 4 position, 5 char, 6 punct
        self.width=3
        self.occlusion_level=0 # 0 open, max=closed
        self.close_counter=0
        self.last_commands=[]
        self.last_active=[]
    def current_gains(self) -> Dict[str,float]:
        # base relaxed highres field: all layers weakly available
        base={"whole":0.55,"norm":0.50,"span":0.55,"position":0.45,"shape":0.35,"pair":0.45,"char":0.30,"punct":0.30,"dark":0.0}
        # resolution boost around current level; level 0 is relaxed/no boost
        if self.level>0:
            target = LAYER_ORDER[self.level]
            family_map={"whole":["whole","norm"],"span":["span"],"pair":["pair"],"position":["position"],"char":["char"],"punct":["punct"]}
            for layer in family_map.get(target,[target]): base[layer] += 0.55
            # width gives neighboring layers a smaller boost
            if self.width >= 2:
                for adj in [self.level-1,self.level+1]:
                    if 1 <= adj < len(LAYER_ORDER):
                        for layer in family_map.get(LAYER_ORDER[adj],[LAYER_ORDER[adj]]): base[layer] += 0.20
        # occlusion dampens normal external layers and adds dark-field sensory signal
        if self.occlusion_level>0:
            damp = [1.0, 0.35, 0.12, 0.03][min(self.occlusion_level,3)]
            for k in list(base.keys()):
                if k != "dark": base[k] *= damp
            base["dark"] = [0.0, 0.35, 0.60, 0.85][min(self.occlusion_level,3)]
        return {k:round(float(v),4) for k,v in base.items()}
    def feature_indices_by_layer(self, atom:str, n:int, salt:str, group_size:int=1) -> Dict[str,List[int]]:
        features=highres_features(atom)
        out={}
        for layer,labels in features.items():
            idxs=[]; seen=set()
            # budget per layer to keep the smoke run sane
            budgets={"whole":3,"norm":2,"span":12,"position":16,"shape":8,"pair":10,"char":16,"punct":8,"dark":3}
            keep=labels[:budgets.get(layer,8)]
            for lab in keep:
                for idx in deterministic_group(f"ute:{layer}:{lab}", n, group_size, salt):
                    if idx not in seen: seen.add(idx); idxs.append(idx)
            out[layer]=idxs
        return out
    def observe_and_update(self, tick:int, nodes:Iterable[int]) -> dict:
        for k in self.ap_energy: self.ap_energy[k] *= self.energy_decay
        touched=Counter()
        for node in nodes:
            for ap in self.node_to_ap.get(int(node),[]): touched[ap]+=1
        for ap,c in touched.items(): self.ap_energy[ap] += float(c)
        active=[ap for ap,c in touched.items() if c >= self.current_min]
        commands=[]
        # Close is special: must be held for >1 tick.
        close_active = "AP_CLOSE" in active
        if close_active:
            self.close_counter += 1
        else:
            self.close_counter = 0
        close_confirmed = False
        if close_active and self.close_counter >= self.close_hold_ticks:
            self.occlusion_level = min(self.max_occlusion, self.occlusion_level + 1)
            commands.append("AP_CLOSE_CONFIRMED")
            close_confirmed = True
        elif not close_active and self.occlusion_level > 0:
            # one notch open per tick as soon as closing pressure falls below trigger
            self.occlusion_level = max(0, self.occlusion_level - 1)
            commands.append("AP_REOPEN_STEP")
        # Explicit open/relax accelerate opening, but not on the same tick that a held close command is confirmed.
        if ("AP_OPEN" in active or "AP_RELAX" in active) and not close_confirmed:
            self.occlusion_level = max(0, self.occlusion_level - 2)
            commands.append("AP_OPEN_OR_RELAX")
        # Resolution state: only update if actuator fires, otherwise drift one level toward relaxed.
        target_map={"AP_WHOLE":1,"AP_SPAN":2,"AP_PAIR":3,"AP_POSITION":4,"AP_CHAR":5,"AP_PUNCT":6}
        targets=[target_map[a] for a in active if a in target_map]
        if targets:
            # strongest touched target wins
            target=max(targets, key=lambda lv: touched.get({v:k for k,v in target_map.items()}[lv],0))
            if self.level < target: self.level += 1
            elif self.level > target: self.level -= 1
            commands.append(f"AP_LEVEL_TOWARD:{LAYER_ORDER[target]}")
        elif self.level > 0:
            self.level -= 1
            commands.append("AP_LEVEL_DRIFT_RELAX")
        if "AP_NARROW" in active: self.width=max(1,self.width-1); commands.append("AP_NARROW")
        elif "AP_WIDEN" in active: self.width=min(6,self.width+1); commands.append("AP_WIDEN")
        elif self.width < 3: self.width += 1
        elif self.width > 3: self.width -= 1
        self.last_active=active; self.last_commands=commands
        return {"active_aperture":active,"aperture_commands":commands,"touched_aperture":dict(touched),"aperture_state":self.state_dict()}
    def state_dict(self):
        return {"level":self.level,"level_name":LAYER_ORDER[self.level],"width":self.width,"occlusion_level":self.occlusion_level,"closed":self.occlusion_level>=self.max_occlusion,"close_counter":self.close_counter,"gains":self.current_gains(),"top_aperture":[[ap,round(v,4)] for ap,v in sorted(self.ap_energy.items(), key=lambda kv:kv[1], reverse=True)[:6]]}

class SelectorTraceController:
    def __init__(self, n:int, group_size:int, salt:str, release_threshold:float, decay:float, cooldown:int, run_dir:Path, current_op_min:int=2, current_lane_min:int=2) -> None:
        self.n=int(n); self.group_size=int(group_size); self.salt=salt; self.release_threshold=float(release_threshold); self.decay=float(decay); self.cooldown=int(cooldown); self.current_op_min=int(current_op_min); self.current_lane_min=int(current_lane_min)
        self.op_groups={op:deterministic_group(f"selector_op:{op}", self.n, group_size, salt) for op in OP_NAMES}
        self.lane_groups={lane:deterministic_group(f"selector_lane:{lane}", self.n, group_size, salt) for lane in LANE_NAMES}
        self.node_to_ops=defaultdict(list); self.node_to_lanes=defaultdict(list)
        for op,nodes in self.op_groups.items():
            for node in nodes: self.node_to_ops[int(node)].append(op)
        for lane,nodes in self.lane_groups.items():
            for node in nodes: self.node_to_lanes[int(node)].append(lane)
        self.op_energy={op:0.0 for op in OP_NAMES}; self.lane_energy={lane:0.0 for lane in LANE_NAMES}; self.lane_hold={lane:0.0 for lane in LANE_NAMES}; self.lane_inhibit={lane:0.0 for lane in LANE_NAMES}; self.lane_release={lane:0.0 for lane in LANE_NAMES}; self.lane_correct={lane:0.0 for lane in LANE_NAMES}
        self.last_emit=-10**12; self.witness_count=0; self.run_dir=Path(run_dir)
    def observe(self,tick:int,nodes:Iterable[int],source_input:str,atom:str):
        for d in [self.op_energy,self.lane_energy,self.lane_hold,self.lane_inhibit,self.lane_release,self.lane_correct]:
            for k in d: d[k]*=self.decay
        touched_ops=Counter(); touched_lanes=Counter()
        for node in nodes:
            node=int(node)
            for op in self.node_to_ops.get(node,[]): touched_ops[op]+=1
            for lane in self.node_to_lanes.get(node,[]): touched_lanes[lane]+=1
        for op,c in touched_ops.items(): self.op_energy[op]+=float(c)
        for lane,c in touched_lanes.items(): self.lane_energy[lane]+=float(c)
        active_ops=[op for op,c in touched_ops.items() if c>=self.current_op_min]
        active_lanes=[l for l,c in touched_lanes.items() if c>=self.current_lane_min]
        commands=[]
        if active_ops and active_lanes:
            sorted_ops=sorted(active_ops,key=lambda o:touched_ops[o], reverse=True)
            sorted_lanes=sorted(active_lanes,key=lambda l:touched_lanes[l], reverse=True)
            for lane in sorted_lanes[:3]:
                for op in sorted_ops[:4]:
                    amp=min(1.0,(touched_ops[op]/max(1,self.current_op_min)+touched_lanes[lane]/max(1,self.current_lane_min))/6.0)
                    commands.append({"op":op,"lane":lane,"amp":round(float(amp),4)})
                    if op in ("SELECT","ADVANCE","SPLIT","MERGE","AMPLIFY","COMPARE"): self.lane_hold[lane]+=0.12*amp
                    if op=="HOLD": self.lane_hold[lane]+=0.25*amp
                    if op=="INHIBIT": self.lane_inhibit[lane]+=0.30*amp
                    if op in ("RELEASE","COMMIT"): self.lane_release[lane]+=0.35*amp
                    if op=="CORRECT": self.lane_correct[lane]+=0.35*amp
                    if op in ("DAMP","ABORT","RETREAT"):
                        self.lane_hold[lane]*=0.65; self.lane_release[lane]*=0.65
        emitted=[]
        strongest=max(LANE_NAMES,key=lambda l:self.lane_hold[l]+self.lane_release[l])
        release_score=self.lane_hold[strongest]+self.lane_release[strongest]-0.35*self.lane_inhibit[strongest]
        commit_pressure=max(float(touched_ops.get("COMMIT",0)),float(touched_ops.get("RELEASE",0)))
        release_intent=("COMMIT" in active_ops) or ("RELEASE" in active_ops)
        gate_pressure=release_score+0.10*commit_pressure
        if release_intent and gate_pressure>=self.release_threshold and (tick-self.last_emit)>=self.cooldown:
            self.last_emit=tick; self.witness_count+=1; witness=f"W{strongest[1:]}_{self.witness_count:04d}"
            emitted.append({"tick":tick,"witness":witness,"lane":strongest,"gate_pressure":round(float(gate_pressure),4),"source_input":source_input,"source_atom":atom,"top_ops":self.top_ops(5),"top_lanes":self.top_lanes(5)})
            self.lane_hold[strongest]*=0.35; self.lane_release[strongest]*=0.20; self.lane_inhibit[strongest]*=0.70
        top_trace=sorted([{"lane":l,"hold":round(self.lane_hold[l],4),"release":round(self.lane_release[l],4),"inhibit":round(self.lane_inhibit[l],4),"correct":round(self.lane_correct[l],4),"energy":round(self.lane_energy[l],4)} for l in LANE_NAMES], key=lambda r:r["hold"]+r["release"]+r["energy"], reverse=True)[:4]
        return {"active_ops":active_ops,"active_lanes":active_lanes,"commands":commands,"emitted":emitted,"top_ops":self.top_ops(6),"top_lanes":self.top_lanes(6),"top_trace":top_trace,"release_lane":strongest,"release_score":round(float(release_score),4),"gate_pressure":round(float(gate_pressure),4)}
    def top_ops(self,k=5): return [[op,round(v,4)] for op,v in sorted(self.op_energy.items(), key=lambda kv:kv[1], reverse=True)[:k]]
    def top_lanes(self,k=5): return [[lane,round(v,4)] for lane,v in sorted(self.lane_energy.items(), key=lambda kv:kv[1], reverse=True)[:k]]

class SimpleWorld:
    def __init__(self, seed:int, ticks:int):
        self.rng=random.Random(seed); self.t=0; self.ticks=ticks
    def next_atom(self):
        t=self.t; self.t+=1
        if t < 100:
            phase="stable"; atom=STABLE_SENTENCES[t % len(STABLE_SENTENCES)]
        elif t < 200:
            phase="noisy_missing_closure"; atom=NOISY_SENTENCES[(t-100) % len(NOISY_SENTENCES)]
        else:
            phase="return_stable"; atom=RETURN_SENTENCES[(t-200) % len(RETURN_SENTENCES)]
        return "curriculum", phase, atom

class ScanFirewall:
    def __init__(self, connectome):
        self.connectome=connectome; self.originals={}; self.forbidden=["active_edge_count","connected_components","cyclomatic_complexity","snapshot_graph","connectome_entropy"]
    def __enter__(self):
        for name in self.forbidden:
            if hasattr(self.connectome,name):
                self.originals[name]=getattr(self.connectome,name)
                def _boom(*_a,_name=name,**_kw): raise RuntimeError(f"SCAN_FIREWALL forbidden {_name}")
                setattr(self.connectome,name,_boom)
        return self
    def __exit__(self,exc_type,exc,tb):
        for name,fn in self.originals.items(): setattr(self.connectome,name,fn)
        return False

def build(args, run_dir):
    bootstrap_vdm(args.repo)
    from vdm_rt.core.sparse_connectome import SparseConnectome
    from vdm_rt.core.bus import AnnounceBus
    from vdm_rt.core.adc import ADC
    from vdm_rt.core.engine import CoreEngine
    C=SparseConnectome(N=args.neurons,k=args.k,seed=args.seed,threshold=args.threshold,lambda_omega=args.lambda_omega,candidates=args.candidates,traversal_walkers=args.walkers,traversal_hops=args.hops)
    bus=AnnounceBus(capacity=args.bus_capacity); C.bus=bus; adc=ADC()
    nx_like=SimpleNamespace(connectome=C,adc=adc,run_dir=str(run_dir),checkpoint_format="h5",N=args.neurons,k=args.k,seed=args.seed,dt=1.0/max(1e-9,args.hz),_emit_step=0,_phase={"phase":0},scout_visits=16,scout_edges=8,cold_head_k=256,cold_half_life_ticks=200,b1_half_life_ticks=50,b1_detector=SimpleNamespace(z_spike=1.0,hysteresis=1.0))
    eng=CoreEngine(nx_like); world=SimpleWorld(args.seed,args.ticks)
    selector=SelectorTraceController(args.neurons,args.selector_group_size,f"selector:{args.seed}",args.release_threshold,args.selector_decay,args.release_cooldown,run_dir,args.current_op_min,args.current_lane_min)
    aperture=SensoryAperture(args.neurons,f"aperture:{args.seed}",args.aperture_group_size,args.aperture_current_min,args.close_hold_ticks)
    return C,bus,adc,nx_like,eng,world,selector,aperture

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",type=Path,required=True); ap.add_argument("--run-dir",type=Path,required=True)
    ap.add_argument("--neurons",type=int,default=1000); ap.add_argument("--walkers",type=int,default=1200); ap.add_argument("--k",type=int,default=12); ap.add_argument("--hops",type=int,default=2); ap.add_argument("--candidates",type=int,default=64); ap.add_argument("--threshold",type=float,default=0.15); ap.add_argument("--lambda-omega",type=float,default=0.1); ap.add_argument("--domain-modulation",type=float,default=1.15625); ap.add_argument("--hz",type=float,default=10.0); ap.add_argument("--seed",type=int,default=20260627); ap.add_argument("--ticks",type=int,default=300); ap.add_argument("--max-wall-s",type=float,default=220.0)
    ap.add_argument("--stim-amp",type=float,default=0.035); ap.add_argument("--feature-group-size",type=int,default=1)
    ap.add_argument("--selector-group-size",type=int,default=8); ap.add_argument("--release-threshold",type=float,default=0.8); ap.add_argument("--current-op-min",type=int,default=2); ap.add_argument("--current-lane-min",type=int,default=2); ap.add_argument("--selector-decay",type=float,default=0.965); ap.add_argument("--release-cooldown",type=int,default=8)
    ap.add_argument("--aperture-group-size",type=int,default=10); ap.add_argument("--aperture-current-min",type=int,default=1); ap.add_argument("--close-hold-ticks",type=int,default=2)
    ap.add_argument("--bus-capacity",type=int,default=65536); ap.add_argument("--bus-drain",type=int,default=4096); ap.add_argument("--save-h5",action="store_true")
    ap.add_argument("--intent-index-dir", type=Path, default=None, help="Optional 2048 phrase/vector index dir for accumulated intention-trace translation")
    ap.add_argument("--intent-modes", default="aperture_only,selector_only,fused")
    ap.add_argument("--intent-retain", type=float, default=0.94)
    ap.add_argument("--intent-trigger-mix", type=float, default=0.18)
    ap.add_argument("--intent-top-k", type=int, default=8)
    ap.add_argument("--intent-emit-reafferent", action="store_true", help="Optional experimental mode: send top-1 phrase as damped reafferent input on the next tick. Default is logging-only.")
    args=ap.parse_args(); run_dir=args.run_dir.resolve(); run_dir.mkdir(parents=True,exist_ok=True)
    for name in ["tick_rows.csv","trace_log.jsonl","utd_events.jsonl","ute_aperture_state.jsonl","aperture_events.jsonl","feature_layer_counts.csv","ute_input_stream.jsonl","run_summary.json"]:
        p=run_dir/name
        if p.exists(): p.unlink()
    import numpy as np; np.random.seed(args.seed)
    C,bus,adc,nx_like,eng,world,selector,aperture=build(args,run_dir)
    (run_dir/"run_config.json").write_text(json.dumps(vars(args),indent=2,default=str),encoding="utf-8")
    (run_dir/"aperture_group_map.json").write_text(json.dumps(aperture.ap_groups,indent=2),encoding="utf-8")
    (run_dir/"selector_group_map.json").write_text(json.dumps({"ops":selector.op_groups,"lanes":selector.lane_groups},indent=2),encoding="utf-8")
    intent_translator=None; intent_events=[]
    if args.intent_index_dir is not None:
        if IntentionTraceTranslatorSet is None:
            raise SystemExit("intention_trace_translator.py is not importable; place this script beside tools/intention_trace_translator.py")
        modes=[m.strip() for m in args.intent_modes.split(",") if m.strip()]
        intent_translator=IntentionTraceTranslatorSet(args.intent_index_dir, modes=modes, retain=args.intent_retain, trigger_mix=args.intent_trigger_mix, top_k=args.intent_top_k)
    from vdm_rt.runtime.events_adapter import observations_to_events, adc_metrics_to_event
    fields=["tick","phase","atom","stim_count","stim_hash","occlusion_level","aperture_level","aperture_level_name","aperture_width","active_aperture","aperture_commands","obs_count","obs_nodes_unique","active_ops","active_lanes","witnesses","release_lane","release_score","gate_pressure","top_ops","top_lanes","top_trace","tick_s"]
    feature_fields=["tick","phase","whole","norm","span","position","shape","pair","char","punct","dark","stim_total","gains"]
    start=time.time(); completed=0
    phase_counts=Counter(); witness_by_phase=Counter(); aperture_active_counts=Counter(); aperture_command_counts=Counter(); occlusion_ticks=Counter(); aperture_level_counts=Counter(); close_events=[]
    with open(run_dir/"tick_rows.csv","w",newline="",encoding="utf-8") as cf, open(run_dir/"feature_layer_counts.csv","w",newline="",encoding="utf-8") as ff:
        writer=csv.DictWriter(cf,fieldnames=fields); writer.writeheader(); cf.flush()
        fwriter=csv.DictWriter(ff,fieldnames=feature_fields); fwriter.writeheader(); ff.flush()
        with ScanFirewall(C):
            for tick in range(args.ticks):
                if time.time()-start > args.max_wall_s: break
                tt=time.perf_counter(); source,phase,atom=world.next_atom(); phase_counts[phase]+=1
                # UTE uses previous aperture state for this tick.
                ap_state_before=aperture.state_dict(); gains=ap_state_before["gains"]
                by_layer=aperture.feature_indices_by_layer(atom,args.neurons,f"ute-sensory-occlusion:{args.seed}",args.feature_group_size)
                stim_all=[]; layer_counts={}
                for layer,idxs in by_layer.items():
                    gain=float(gains.get(layer,0.0)); layer_counts[layer]=len(idxs)
                    if idxs and gain>0:
                        amp=args.stim_amp*gain
                        C.stimulate_indices(idxs, amp=amp)
                        stim_all.extend(idxs)
                append_jsonl(run_dir/"ute_input_stream.jsonl", {"tick":tick,"phase":phase,"atom":atom,"aperture_before":ap_state_before,"layer_counts":layer_counts,"stim_hash":sha_list(stim_all),"stim_count":len(set(stim_all))})
                fwriter.writerow({"tick":tick,"phase":phase,**{k:layer_counts.get(k,0) for k in ["whole","norm","span","position","shape","pair","char","punct","dark"]},"stim_total":len(set(stim_all)),"gains":json.dumps(gains)}); ff.flush()
                sie2=float(getattr(C,"_last_sie2_valence",0.0) or 0.0); sie_gate=max(0.35,min(1.0,sie2 if sie2>0.0 else 1.0))
                C.step(tick/max(1e-9,args.hz), domain_modulation=args.domain_modulation, sie_drive=sie_gate, use_time_dynamics=True)
                obs=bus.drain(args.bus_drain); adc.update_from(obs); adc_m=adc.get_metrics()
                evs=observations_to_events(obs); evs.append(adc_metrics_to_event(adc_m,tick)); nx_like._emit_step=tick; eng.step(int(max(1,nx_like.dt*1000.0)), evs)
                obs_nodes=[]
                for o in obs:
                    try: obs_nodes.extend([int(x) for x in (getattr(o,"nodes",[]) or [])])
                    except Exception: pass
                sel=selector.observe(tick,obs_nodes,source,atom)
                ap_update=aperture.observe_and_update(tick,obs_nodes)
                for a in ap_update["active_aperture"]: aperture_active_counts[a]+=1
                for c in ap_update["aperture_commands"]: aperture_command_counts[c]+=1
                occlusion_ticks[ap_update["aperture_state"]["occlusion_level"]]+=1
                aperture_level_counts[ap_update["aperture_state"]["level_name"]]+=1
                if any(c.startswith("AP_CLOSE") or c.startswith("AP_REOPEN") or c=="AP_OPEN_OR_RELAX" for c in ap_update["aperture_commands"]):
                    ev={"tick":tick,"phase":phase,"atom":atom,"active_aperture":ap_update["active_aperture"],"aperture_commands":ap_update["aperture_commands"],"state":ap_update["aperture_state"]}
                    close_events.append(ev); append_jsonl(run_dir/"aperture_events.jsonl",ev)
                append_jsonl(run_dir/"ute_aperture_state.jsonl", {"tick":tick,"phase":phase,"atom":atom,"before":ap_state_before,"after":ap_update["aperture_state"],"active_aperture":ap_update["active_aperture"],"commands":ap_update["aperture_commands"]})
                for ev in sel["emitted"]:
                    ev["phase"]=phase; append_jsonl(run_dir/"utd_events.jsonl", ev); witness_by_phase[phase]+=1
                rec={"tick":tick,"phase":phase,"atom":atom,"stim_count":len(set(stim_all)),"stim_hash":sha_list(stim_all),"occlusion_level":ap_state_before["occlusion_level"],"aperture_level":ap_state_before["level"],"aperture_level_name":ap_state_before["level_name"],"aperture_width":ap_state_before["width"],"active_aperture":" ".join(ap_update["active_aperture"]),"aperture_commands":" ".join(ap_update["aperture_commands"]),"obs_count":len(obs),"obs_nodes_unique":len(set(obs_nodes)),"active_ops":" ".join(sel["active_ops"]),"active_lanes":" ".join(sel["active_lanes"]),"witnesses":" ".join(e["witness"] for e in sel["emitted"]),"release_lane":sel["release_lane"],"release_score":sel["release_score"],"gate_pressure":sel["gate_pressure"],"top_ops":json.dumps(sel["top_ops"]),"top_lanes":json.dumps(sel["top_lanes"]),"top_trace":json.dumps(sel["top_trace"]),"tick_s":float(time.perf_counter()-tt)}
                
                if intent_translator is not None:
                    intent_translator.update_tick(rec, raw_ref={"tick": tick, "phase": phase, "row_file": "tick_rows.csv"})
                    for ev in sel["emitted"]:
                        sampled = intent_translator.sample_and_reset({
                            "event_kind": "witness", "tick": tick, "phase_label": phase, "run_label": run_dir.name,
                            "run_dir": str(run_dir), "tick_rows_path": str(run_dir/"tick_rows.csv"), "trace_log_path": str(run_dir/"trace_log.jsonl"),
                            "witness_event_id": ev.get("witness", "")
                        })
                        intent_events.extend(sampled)
                        append_jsonl(run_dir/"intent_translation_events.jsonl", sampled)
                        if args.intent_emit_reafferent and sampled:
                            # Optional emission hook: default off. Runner keeps this as a log-level marker; production UTE should route it as damped reafference.
                            append_jsonl(run_dir/"intent_reafferent_emissions.jsonl", [{"tick": tick, "phrase": sampled[0].get("top1_phrase"), "mode": sampled[0].get("translation_mode"), "note": "optional damped reafferent marker; not injected by default runner"}])
                writer.writerow(rec); cf.flush(); append_jsonl(run_dir/"trace_log.jsonl", {"tick":tick,"phase":phase,"atom":atom,"selector":sel,"aperture":ap_update}); completed=tick+1
    final_h5=None
    if args.save_h5:
        try:
            from vdm_rt.core.memory import save_checkpoint
            final_h5=str(save_checkpoint(str(run_dir), completed, C, fmt="h5", adc=adc))
        except Exception as e: final_h5="SAVE_FAILED: "+repr(e)
    phase_summary=[]
    for phase,c in phase_counts.items():
        phase_summary.append({"phase":phase,"ticks":c,"witnesses":witness_by_phase[phase],"witness_rate":round(witness_by_phase[phase]/max(1,c),4)})
    with open(run_dir/"phase_summary.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["phase","ticks","witnesses","witness_rate"]); w.writeheader(); w.writerows(phase_summary)
    if intent_translator is not None and intent_events and write_intent_csv is not None:
        write_intent_csv(run_dir/"intent_translation_events.csv", intent_events)
        topk=[]
        for sr in intent_events:
            for d in json.loads(sr.get("top_k_detail_json","[]")):
                topk.append({"tick":sr.get("tick"),"run_label":sr.get("run_label"),"phase_label":sr.get("phase_label"),"event_kind":sr.get("event_kind"),"witness_event_id":sr.get("witness_event_id"),"translation_mode":sr.get("translation_mode"), **d})
        write_intent_csv(run_dir/"intent_translation_topk.csv", topk)
    summary={"run_dir":str(run_dir),"mode":"sensory_occlusion_actuator_smoke_v1","neurons":args.neurons,"walkers":args.walkers,"walker_ratio":args.walkers/max(1,args.neurons),"ticks_requested":args.ticks,"ticks_completed":completed,"elapsed_s":round(time.time()-start,3),"mean_tick_s":round((time.time()-start)/max(1,completed),5),"phase_summary":phase_summary,"witness_total":sum(witness_by_phase.values()),"aperture_active_counts":dict(aperture_active_counts),"aperture_command_counts":dict(aperture_command_counts),"occlusion_ticks_by_level":dict(occlusion_ticks),"aperture_level_counts":dict(aperture_level_counts),"close_event_count":len([e for e in close_events if "AP_CLOSE_CONFIRMED" in e.get("aperture_commands",[])]),"aperture_event_count":len(close_events),"first_aperture_events":close_events[:20],"final_aperture_state":aperture.state_dict(),"final_h5":final_h5}
    (run_dir/"run_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))
    return 0
if __name__ == "__main__": raise SystemExit(main())
