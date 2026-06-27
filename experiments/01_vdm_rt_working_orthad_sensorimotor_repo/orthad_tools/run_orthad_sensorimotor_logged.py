#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, sys, time, hashlib, importlib.util, random
from pathlib import Path
from types import SimpleNamespace
from collections import Counter, defaultdict, deque
from typing import Any, Dict, List, Iterable, Optional, Tuple

# Load helpers from verified runner without copying engine code.
HELPER = Path('/mnt/data/pkg_unpack/vdm_orthad_curriculum_verified_resume_scripts/scripts/run_orthad_curriculum_verified_resume.py')
spec = importlib.util.spec_from_file_location('orthad_verified_runner_helpers', str(HELPER))
helpers = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(helpers)

ACTUATOR_PRIMITIVES = helpers.ACTUATOR_PRIMITIVES

def append_jsonl(path: Path, rec: dict):
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + '\n')

def sha_list(xs):
    h = hashlib.sha256()
    for x in xs:
        h.update(str(int(x)).encode()); h.update(b',')
    return h.hexdigest()[:16]

class LoggingActuator(helpers.FixedGroupActuator):
    def observe_nodes_with_energy(self, tick:int, nodes:Iterable[int], source:str, weight:float=1.0):
        before = dict(self.energy)
        fired = self.observe_nodes(tick, nodes, source, weight)
        after = dict(self.energy)
        top_before = sorted(before.items(), key=lambda kv: kv[1], reverse=True)[:5]
        top_after = sorted(after.items(), key=lambda kv: kv[1], reverse=True)[:5]
        return fired, top_before, top_after

def build(args, run_dir: Path):
    helpers.bootstrap_vdm(args.repo)
    from vdm_rt.core.sparse_connectome import SparseConnectome
    from vdm_rt.core.bus import AnnounceBus
    from vdm_rt.core.adc import ADC
    from vdm_rt.core.engine import CoreEngine
    walkers = int(args.walkers) if args.walkers is not None else int(round(1.2*args.neurons))
    C = SparseConnectome(N=args.neurons, k=args.k, seed=args.seed, threshold=args.threshold,
                         lambda_omega=args.lambda_omega, candidates=args.candidates,
                         traversal_walkers=walkers, traversal_hops=args.hops)
    bus = AnnounceBus(capacity=args.bus_capacity)
    C.bus = bus
    adc = ADC()
    nx_like = SimpleNamespace(connectome=C, adc=adc, run_dir=str(run_dir), checkpoint_format='h5',
                              N=args.neurons, k=args.k, seed=args.seed, dt=1.0/max(1e-9,args.hz),
                              _emit_step=0, _phase={'phase':0}, scout_visits=args.scout_visits,
                              scout_edges=args.scout_edges, cold_head_k=args.cold_head_k,
                              cold_half_life_ticks=args.cold_half_life_ticks,
                              b1_half_life_ticks=50,
                              b1_detector=SimpleNamespace(z_spike=1.0, hysteresis=1.0))
    eng = CoreEngine(nx_like)
    world = helpers.CurriculumWorld(args.curriculum, args.stream_file, args.seed, args.reafference)
    motor = LoggingActuator(n=args.neurons, group_size=args.motor_group_size, salt=f'orthad-motor-v3:{args.seed}',
                            threshold=args.motor_threshold, decay=args.motor_decay, cooldown=args.motor_cooldown,
                            run_dir=run_dir)
    return C, bus, adc, nx_like, eng, world, motor

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--run-dir', type=Path, required=True)
    ap.add_argument('--neurons', type=int, default=1000)
    ap.add_argument('--walkers', type=int, default=1200)
    ap.add_argument('--k', type=int, default=12)
    ap.add_argument('--hops', type=int, default=3)
    ap.add_argument('--candidates', type=int, default=64)
    ap.add_argument('--threshold', type=float, default=0.15)
    ap.add_argument('--lambda-omega', type=float, default=0.1)
    ap.add_argument('--domain-modulation', type=float, default=1.15625)
    ap.add_argument('--hz', type=float, default=10.0)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--ticks', type=int, default=600)
    ap.add_argument('--max-wall-s', type=float, default=160.0)
    ap.add_argument('--curriculum', choices=sorted(helpers.BUILTIN_STREAMS.keys()), default='rich')
    ap.add_argument('--stream-file', type=Path, default=None)
    ap.add_argument('--reafference', action='store_true')
    ap.add_argument('--stim-group-size', type=int, default=4)
    ap.add_argument('--stim-max-units', type=int, default=8)
    ap.add_argument('--stim-amp', type=float, default=0.05)
    ap.add_argument('--motor-group-size', type=int, default=8)
    ap.add_argument('--motor-threshold', type=float, default=40.0)
    ap.add_argument('--motor-decay', type=float, default=0.97)
    ap.add_argument('--motor-cooldown', type=int, default=12)
    ap.add_argument('--bus-capacity', type=int, default=65536)
    ap.add_argument('--bus-drain', type=int, default=4096)
    ap.add_argument('--scout-visits', type=int, default=16)
    ap.add_argument('--scout-edges', type=int, default=8)
    ap.add_argument('--cold-head-k', type=int, default=256)
    ap.add_argument('--cold-half-life-ticks', type=int, default=200)
    ap.add_argument('--use-time-dynamics', action='store_true', default=True)
    ap.add_argument('--save-h5', action='store_true')
    args = ap.parse_args()

    args.repo = args.repo.resolve()
    run_dir = args.run_dir.resolve(); run_dir.mkdir(parents=True, exist_ok=True)
    for name in ['ute_input_stream.jsonl','utd_motor_events.jsonl','io_timeline.jsonl','tick_rows.csv','run_summary.json']:
        p=run_dir/name
        if p.exists(): p.unlink()
    # motor class writes motor_events.jsonl; keep a copy then rename/link in summary
    p=run_dir/'motor_events.jsonl'
    if p.exists(): p.unlink()

    import numpy as np
    np.random.seed(args.seed)
    C,bus,adc,nx_like,eng,world,motor = build(args, run_dir)
    cfg = vars(args).copy(); cfg['mode']='orthad_sensorimotor_logged_v3'; cfg['walker_ratio']=args.walkers/max(1,args.neurons)
    (run_dir/'run_config.json').write_text(json.dumps(cfg, indent=2, default=str), encoding='utf-8')

    from vdm_rt.runtime.events_adapter import observations_to_events, adc_metrics_to_event
    fields = ['tick','source','atom','curriculum_cycle','curriculum_atom','stim_count','stim_hash','obs_count','obs_nodes_count','obs_nodes_unique','adc_territories','adc_boundaries','adc_cycle_hits','vt_visits','vt_unique','vt_coverage','vt_entropy','sie2_valence','sie_gate','motor_fired','top_energy_before','top_energy_after','tick_s']
    start = time.time(); completed=0
    source_counts=Counter(); input_counts=Counter(); motor_counts=Counter(); curr_motor=Counter(); self_motor=Counter()
    with open(run_dir/'tick_rows.csv','w',newline='',encoding='utf-8') as cf:
        writer=csv.DictWriter(cf, fieldnames=fields); writer.writeheader(); cf.flush()
        with helpers.ScanFirewall(C):
            for tick in range(args.ticks):
                if time.time()-start > args.max_wall_s:
                    break
                tt0=time.perf_counter()
                source, atom, cyc, ai = world.next_atom()
                stim = helpers.atom_to_indices(atom, args.neurons, args.stim_group_size, args.stim_max_units, salt=f'orthad-input-v3:{args.seed}')
                append_jsonl(run_dir/'ute_input_stream.jsonl', {'tick':tick,'source':source,'cycle_index':cyc,'atom_index':ai,'atom':atom,'stim_count':len(stim),'stim_hash':sha_list(stim)})
                source_counts[source]+=1; input_counts[atom]+=1
                if stim:
                    C.stimulate_indices(stim, amp=args.stim_amp)
                sie2=float(getattr(C,'_last_sie2_valence',0.0) or 0.0)
                sie_gate=max(0.35, min(1.0, sie2 if sie2>0.0 else 1.0))
                t_model=tick/max(1e-9,args.hz)
                C.step(t_model, domain_modulation=args.domain_modulation, sie_drive=sie_gate, use_time_dynamics=args.use_time_dynamics)
                obs=bus.drain(args.bus_drain)
                adc.update_from(obs); adc_m=adc.get_metrics()
                evs=observations_to_events(obs); evs.append(adc_metrics_to_event(adc_m,tick))
                nx_like._emit_step=tick; eng.step(int(max(1, nx_like.dt*1000.0)), evs)
                obs_nodes=[]
                for o in obs:
                    try: obs_nodes.extend([int(x) for x in (getattr(o,'nodes',[]) or [])])
                    except Exception: pass
                fired, top_b, top_a = motor.observe_nodes_with_energy(tick, obs_nodes, source='walker_observation', weight=1.0)
                for prim in fired:
                    world.push_reafference(prim)
                    append_jsonl(run_dir/'utd_motor_events.jsonl', {'tick':tick,'primitive':prim,'source_input':source,'source_atom':atom,'actuator_source':'walker_observation'})
                    motor_counts[prim]+=1
                    if source == 'curriculum': curr_motor[(atom,prim)] += 1
                    else: self_motor[(atom,prim)] += 1
                findings=dict(getattr(C,'findings',{}) or {})
                rec={'tick':tick,'source':source,'atom':atom,'curriculum_cycle':cyc,'curriculum_atom':ai,'stim_count':len(stim),'stim_hash':sha_list(stim),
                     'obs_count':len(obs),'obs_nodes_count':len(obs_nodes),'obs_nodes_unique':len(set(obs_nodes)),
                     'adc_territories':int(adc_m.get('adc_territories',0)),'adc_boundaries':int(adc_m.get('adc_boundaries',0)),'adc_cycle_hits':int(adc_m.get('adc_cycle_hits',0)),
                     'vt_visits':int(findings.get('vt_visits',0)),'vt_unique':int(findings.get('vt_unique',0)),'vt_coverage':float(findings.get('vt_coverage',0.0)),'vt_entropy':float(findings.get('vt_entropy',0.0)),
                     'sie2_valence':float(getattr(C,'_last_sie2_valence',0.0) or 0.0),'sie_gate':sie_gate,'motor_fired':' '.join(fired),
                     'top_energy_before':json.dumps(top_b),'top_energy_after':json.dumps(top_a),'tick_s':float(time.perf_counter()-tt0)}
                writer.writerow(rec); cf.flush()
                append_jsonl(run_dir/'io_timeline.jsonl', rec)
                completed=tick+1
    final_h5=None
    if args.save_h5:
        try:
            from vdm_rt.core.memory import save_checkpoint
            final_h5 = str(save_checkpoint(str(run_dir), completed, C, fmt='h5', adc=adc))
        except Exception as e:
            final_h5 = 'SAVE_FAILED: '+repr(e)
    summary={
        'run_dir':str(run_dir),'mode':'orthad_sensorimotor_logged_v3','neurons':args.neurons,'walkers':args.walkers,'ticks_requested':args.ticks,'ticks_completed':completed,'elapsed_s':time.time()-start,
        'mean_wall_tick_s':(time.time()-start)/max(1,completed),'source_counts':dict(source_counts),'top_inputs':input_counts.most_common(30),'motor_event_count':sum(motor_counts.values()),'motor_by_primitive':dict(motor_counts),
        'top_curriculum_atom_to_motor':[{'atom':a,'primitive':p,'count':c} for (a,p),c in curr_motor.most_common(30)],
        'top_self_atom_to_motor':[{'atom':a,'primitive':p,'count':c} for (a,p),c in self_motor.most_common(30)],
        'final_h5':final_h5,'scan_firewall':'passed'}
    (run_dir/'run_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
    return 0
if __name__=='__main__':
    raise SystemExit(main())
