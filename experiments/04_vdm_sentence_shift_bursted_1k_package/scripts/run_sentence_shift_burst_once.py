#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, sys, time, importlib.util, pickle, hashlib
from pathlib import Path
from types import SimpleNamespace
from collections import Counter


def load_tools(path: Path):
    spec = importlib.util.spec_from_file_location("orthad_selector_tools", str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["orthad_selector_tools"] = mod
    spec.loader.exec_module(mod)
    return mod


def append_jsonl(path: Path, rec: dict):
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True)+'\n')


def np_state_to_pickle(np):
    return pickle.dumps(np.random.get_state(), protocol=4)


def np_state_from_pickle(np, b: bytes):
    np.random.set_state(pickle.loads(b))


def dump_selector(selector):
    return {
        'op_energy': selector.op_energy,
        'lane_energy': selector.lane_energy,
        'lane_hold': selector.lane_hold,
        'lane_inhibit': selector.lane_inhibit,
        'lane_release': selector.lane_release,
        'lane_correct': selector.lane_correct,
        'last_emit': selector.last_emit,
        'witness_count': selector.witness_count,
    }


def load_selector(selector, d):
    for name in ['op_energy','lane_energy','lane_hold','lane_inhibit','lane_release','lane_correct']:
        if name in d:
            target = getattr(selector, name)
            for k,v in d[name].items():
                if k in target: target[k] = float(v)
    selector.last_emit = int(d.get('last_emit', selector.last_emit))
    selector.witness_count = int(d.get('witness_count', selector.witness_count))


def make_ext_state(C, selector, np, completed_tick:int):
    return {
        'completed_tick': int(completed_tick),
        'np_random_state': np_state_to_pickle(np),
        'connectome_rng_state': getattr(C.rng.bit_generator, 'state', None),
        'stim': getattr(C, '_stim', None),
        'connectome_tick': int(getattr(C, '_tick', 0)),
        'last_sie2_reward': float(getattr(C, '_last_sie2_reward', 0.0) or 0.0),
        'last_sie2_valence': float(getattr(C, '_last_sie2_valence', 0.0) or 0.0),
        'sie2': getattr(C, '_sie2', None),
        'frag_dsu': getattr(C, '_frag_dsu', None),
        'frag_components_lb': int(getattr(C, '_frag_components_lb', 0)),
        'frag_dirty_since': getattr(C, '_frag_dirty_since', None),
        'edges_active': int(getattr(C, '_edges_active', 0)),
        'vertices_active': int(getattr(C, '_vertices_active', 0)),
        'last_edges_active': int(getattr(C, '_last_edges_active', 0)),
        'last_vertices_active': int(getattr(C, '_last_vertices_active', 0)),
        'findings': dict(getattr(C, 'findings', {}) or {}),
        'selector': dump_selector(selector),
    }


def restore_ext_state(C, selector, np, ext):
    if ext.get('np_random_state'):
        np_state_from_pickle(np, ext['np_random_state'])
    if ext.get('connectome_rng_state') is not None:
        C.rng.bit_generator.state = ext['connectome_rng_state']
    if ext.get('stim') is not None:
        C._stim = ext['stim']
    C._tick = int(ext.get('connectome_tick', getattr(C, '_tick', 0)))
    if ext.get('sie2') is not None:
        C._sie2 = ext['sie2']
    C._last_sie2_reward = float(ext.get('last_sie2_reward', getattr(C, '_last_sie2_reward', 0.0) or 0.0))
    C._last_sie2_valence = float(ext.get('last_sie2_valence', getattr(C, '_last_sie2_valence', 0.0) or 0.0))
    if ext.get('frag_dsu') is not None: C._frag_dsu = ext['frag_dsu']
    C._frag_components_lb = int(ext.get('frag_components_lb', getattr(C, '_frag_components_lb', 0)))
    C._frag_dirty_since = ext.get('frag_dirty_since', getattr(C, '_frag_dirty_since', None))
    for name in ['edges_active','vertices_active','last_edges_active','last_vertices_active']:
        if name in ext: setattr(C, '_'+name if not name.startswith('_') else name, int(ext[name]))
    C.findings = dict(ext.get('findings', getattr(C, 'findings', {}) or {}))
    load_selector(selector, ext.get('selector', {}))


def write_ext_h5(h5_path: Path, ext: dict):
    import h5py, numpy as np
    blob = pickle.dumps(ext, protocol=4)
    with h5py.File(h5_path, 'a') as f:
        if 'sentence_runner' in f:
            del f['sentence_runner']
        g = f.create_group('sentence_runner')
        g.attrs['completed_tick'] = int(ext['completed_tick'])
        g.create_dataset('state_pickle_u8', data=np.frombuffer(blob, dtype=np.uint8), compression='gzip')


def read_ext_h5(h5_path: Path):
    import h5py
    with h5py.File(h5_path, 'r') as f:
        arr = f['sentence_runner/state_pickle_u8'][...]
        return pickle.loads(arr.tobytes())


def csr_bytes(C):
    import numpy as np
    parts=[]
    row=[0]
    col=[]
    total=0
    for nbrs in C.adj:
        total += int(nbrs.size)
        row.append(total)
        if nbrs.size: col.extend([int(x) for x in nbrs])
    return np.asarray(row, dtype=np.int64).tobytes()+np.asarray(col, dtype=np.int32).tobytes()


def state_signature(C, selector, np):
    h=hashlib.sha256()
    h.update(C.W.tobytes())
    h.update(csr_bytes(C))
    h.update(getattr(C, '_stim').tobytes())
    h.update(str(int(getattr(C, '_tick', 0))).encode())
    h.update(pickle.dumps(C.rng.bit_generator.state, protocol=4))
    h.update(pickle.dumps(np.random.get_state(), protocol=4))
    h.update(pickle.dumps(dump_selector(selector), protocol=4))
    h.update(pickle.dumps(getattr(C, '_last_sie2_valence', 0.0), protocol=4))
    return h.hexdigest()


def build_runtime(args, run_dir: Path, tools):
    tools.bootstrap_vdm(args.repo)
    import numpy as np
    from vdm_rt.core.sparse_connectome import SparseConnectome
    from vdm_rt.core.bus import AnnounceBus
    from vdm_rt.core.adc import ADC
    from vdm_rt.core.engine import CoreEngine
    C=SparseConnectome(N=args.neurons, k=args.k, seed=args.seed, threshold=args.threshold,
        lambda_omega=args.lambda_omega, candidates=args.candidates, traversal_walkers=args.walkers,
        traversal_hops=args.hops)
    bus=AnnounceBus(capacity=args.bus_capacity); C.bus=bus
    adc=ADC()
    nx_like=SimpleNamespace(connectome=C, adc=adc, run_dir=str(run_dir), checkpoint_format='h5',
        N=args.neurons,k=args.k,seed=args.seed,dt=1.0/max(1e-9,args.hz),_emit_step=0,_phase={'phase':0},
        scout_visits=args.scout_visits,scout_edges=args.scout_edges,cold_head_k=args.cold_head_k,
        cold_half_life_ticks=args.cold_half_life_ticks,b1_half_life_ticks=50,
        b1_detector=SimpleNamespace(z_spike=1.0,hysteresis=1.0))
    eng=CoreEngine(nx_like)
    selector=tools.SelectorTraceController(n=args.neurons, group_size=args.selector_group_size,
        salt=f'sentence-selector-v1:{args.seed}', op_threshold=16.0, lane_threshold=14.0,
        release_threshold=args.release_threshold, decay=args.selector_decay, cooldown=args.release_cooldown,
        run_dir=run_dir, current_op_min=args.current_op_min, current_lane_min=args.current_lane_min)
    return C,bus,adc,nx_like,eng,selector,np


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--tools', type=Path, required=True)
    ap.add_argument('--schedule', type=Path, required=True)
    ap.add_argument('--run-dir', type=Path, required=True)
    ap.add_argument('--start-tick', type=int, required=True)
    ap.add_argument('--end-tick', type=int, required=True)
    ap.add_argument('--resume-h5', type=Path, default=None)
    ap.add_argument('--neurons', type=int, default=1000)
    ap.add_argument('--walkers', type=int, default=1200)
    ap.add_argument('--seed', type=int, default=20260627)
    ap.add_argument('--k', type=int, default=12)
    ap.add_argument('--hops', type=int, default=2)
    ap.add_argument('--candidates', type=int, default=64)
    ap.add_argument('--threshold', type=float, default=0.05)
    ap.add_argument('--lambda-omega', type=float, default=0.1)
    ap.add_argument('--hz', type=float, default=10.0)
    ap.add_argument('--domain-modulation', type=float, default=1.15625)
    ap.add_argument('--stim-group-size', type=int, default=4)
    ap.add_argument('--stim-max-units', type=int, default=10)
    ap.add_argument('--stim-amp', type=float, default=0.05)
    ap.add_argument('--selector-group-size', type=int, default=8)
    ap.add_argument('--current-op-min', type=int, default=2)
    ap.add_argument('--current-lane-min', type=int, default=2)
    ap.add_argument('--release-threshold', type=float, default=1.15)
    ap.add_argument('--release-cooldown', type=int, default=8)
    ap.add_argument('--selector-decay', type=float, default=0.965)
    ap.add_argument('--bus-capacity', type=int, default=65536)
    ap.add_argument('--bus-drain', type=int, default=4096)
    ap.add_argument('--scout-visits', type=int, default=16)
    ap.add_argument('--scout-edges', type=int, default=8)
    ap.add_argument('--cold-head-k', type=int, default=256)
    ap.add_argument('--cold-half-life-ticks', type=int, default=200)
    args=ap.parse_args()
    run_dir=args.run_dir.resolve(); run_dir.mkdir(parents=True, exist_ok=True)
    tools=load_tools(args.tools)
    C,bus,adc,nx_like,eng,selector,np=build_runtime(args, run_dir, tools)
    from vdm_rt.core.memory import load_engram, save_checkpoint
    from vdm_rt.runtime.events_adapter import observations_to_events, adc_metrics_to_event
    if args.start_tick == 0:
        np.random.seed(args.seed)
    else:
        if not args.resume_h5 or not args.resume_h5.exists():
            raise SystemExit('resume h5 required for nonzero start')
        load_engram(str(args.resume_h5), C, adc=adc)
        restore_ext_state(C, selector, np, read_ext_h5(args.resume_h5))
    cfg_path=run_dir/'run_config.json'
    if not cfg_path.exists():
        cfg=vars(args).copy(); cfg['mode']='sentence_shift_bursted_resume_v1'; cfg['notes']='one Python process per burst; H5 loaded between bursts; extended runner state embedded in H5'
        cfg_path.write_text(json.dumps(cfg, indent=2, default=str), encoding='utf-8')
    records=[json.loads(line) for line in Path(args.schedule).read_text(encoding='utf-8').splitlines() if line.strip()]
    records={int(r['tick']):r for r in records}
    fields=['tick','phase','kind','input_id','text','stim_count','stim_hash','obs_count','obs_nodes_count','obs_nodes_unique','adc_territories','adc_boundaries','adc_cycle_hits','vt_visits','vt_unique','vt_coverage','vt_entropy','sie2_valence','active_ops','active_lanes','commands','witnesses','top_trace','release_lane','release_score','gate_pressure','tick_s']
    csv_path=run_dir/'tick_rows.csv'
    new_csv=not csv_path.exists()
    witness_records=[]; rows_written=0
    t_start=time.time()
    with open(csv_path,'a',newline='',encoding='utf-8') as cf:
        w=csv.DictWriter(cf, fieldnames=fields)
        if new_csv: w.writeheader(); cf.flush()
        with tools.ScanFirewall(C):
            for tick in range(args.start_tick, args.end_tick):
                rec0=records[tick]
                text=rec0['text']; kind=rec0['kind']; phase=rec0['phase']; input_id=rec0['input_id']
                tt0=time.perf_counter()
                stim=tools.atom_to_indices(text, args.neurons, args.stim_group_size, args.stim_max_units, salt=f'sentence-input-v1:{args.seed}')
                if stim: C.stimulate_indices(stim, amp=args.stim_amp)
                sie2=float(getattr(C,'_last_sie2_valence',0.0) or 0.0); sie_gate=max(0.35,min(1.0,sie2 if sie2>0 else 1.0))
                C.step(tick/max(1e-9,args.hz), domain_modulation=args.domain_modulation, sie_drive=sie_gate, use_time_dynamics=True)
                obs=bus.drain(args.bus_drain); adc.update_from(obs); adc_m=adc.get_metrics()
                evs=observations_to_events(obs); evs.append(adc_metrics_to_event(adc_m,tick)); nx_like._emit_step=tick; eng.step(int(max(1,nx_like.dt*1000.0)), evs)
                obs_nodes=[]
                for o in obs:
                    try: obs_nodes.extend([int(x) for x in (getattr(o,'nodes',[]) or [])])
                    except Exception: pass
                sel=selector.observe(tick, obs_nodes, 'curriculum', text)
                for ev in sel['emitted']:
                    ev.update({'kind':kind,'phase':phase,'input_id':input_id,'text':text})
                    witness_records.append(ev)
                    append_jsonl(run_dir/'utd_events.jsonl', ev)
                findings=dict(getattr(C,'findings',{}) or {})
                row={'tick':tick,'phase':phase,'kind':kind,'input_id':input_id,'text':text,'stim_count':len(stim),'stim_hash':tools.sha_list(stim),'obs_count':len(obs),'obs_nodes_count':len(obs_nodes),'obs_nodes_unique':len(set(obs_nodes)),'adc_territories':int(adc_m.get('adc_territories',0)),'adc_boundaries':int(adc_m.get('adc_boundaries',0)),'adc_cycle_hits':int(adc_m.get('adc_cycle_hits',0)),'vt_visits':int(findings.get('vt_visits',0)),'vt_unique':int(findings.get('vt_unique',0)),'vt_coverage':float(findings.get('vt_coverage',0.0)),'vt_entropy':float(findings.get('vt_entropy',0.0)),'sie2_valence':float(getattr(C,'_last_sie2_valence',0.0) or 0.0),'active_ops':' '.join(sel['active_ops']),'active_lanes':' '.join(sel['active_lanes']),'commands':json.dumps(sel['commands']),'witnesses':' '.join(ev['witness'] for ev in sel['emitted']),'top_trace':json.dumps(sel['top_trace']),'release_lane':sel['release_lane'],'release_score':sel['release_score'],'gate_pressure':sel['gate_pressure'],'tick_s':time.perf_counter()-tt0}
                w.writerow(row); cf.flush()
                append_jsonl(run_dir/'trace_log.jsonl', {'tick':tick,'phase':phase,'kind':kind,'input_id':input_id,'text':text,'selector':sel})
                append_jsonl(run_dir/'ute_input_stream.jsonl', rec0)
                rows_written += 1
    completed_tick=args.end_tick
    sig_before=state_signature(C, selector, np)
    h5_path=Path(save_checkpoint(str(run_dir), completed_tick, C, fmt='h5', adc=adc))
    ext=make_ext_state(C, selector, np, completed_tick)
    write_ext_h5(h5_path, ext)
    # Verify H5 reload + extended state restore immediately.
    C2,bus2,adc2,nx2,eng2,selector2,np2=build_runtime(args, run_dir, tools)
    load_engram(str(h5_path), C2, adc=adc2)
    restore_ext_state(C2, selector2, np2, read_ext_h5(h5_path))
    sig_after=state_signature(C2, selector2, np2)
    ok = (sig_before == sig_after)
    burst_summary={'start_tick':args.start_tick,'end_tick':args.end_tick,'rows_written':rows_written,'elapsed_s':time.time()-t_start,'mean_tick_s':(time.time()-t_start)/max(1,rows_written),'witnesses_this_burst':len(witness_records),'h5':str(h5_path),'h5_reload_signature_ok':ok,'signature_before':sig_before,'signature_after':sig_after}
    (run_dir/f'burst_{args.start_tick:04d}_{args.end_tick:04d}.json').write_text(json.dumps(burst_summary, indent=2), encoding='utf-8')
    print(json.dumps(burst_summary, indent=2))
    if not ok:
        raise SystemExit('H5 reload signature mismatch')

if __name__=='__main__': main()
