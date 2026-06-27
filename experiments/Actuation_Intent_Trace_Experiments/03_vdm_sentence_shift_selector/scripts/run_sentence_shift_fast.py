#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, sys, time, importlib.util
from pathlib import Path
from collections import Counter, defaultdict
from types import SimpleNamespace

# Load selector tools from sibling package path

def load_tools(path: Path):
    spec = importlib.util.spec_from_file_location("orthad_selector_tools", str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["orthad_selector_tools"] = mod
    spec.loader.exec_module(mod)
    return mod

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--tools', type=Path, required=True)
    ap.add_argument('--schedule', type=Path, required=True)
    ap.add_argument('--run-dir', type=Path, required=True)
    ap.add_argument('--neurons', type=int, default=1000)
    ap.add_argument('--walkers', type=int, default=1200)
    ap.add_argument('--seed', type=int, default=20260627)
    ap.add_argument('--ticks', type=int, default=1200)
    ap.add_argument('--max-wall-s', type=float, default=300)
    ap.add_argument('--k', type=int, default=12)
    ap.add_argument('--hops', type=int, default=3)
    ap.add_argument('--candidates', type=int, default=64)
    ap.add_argument('--threshold', type=float, default=0.15)
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
    ap.add_argument('--save-h5', action='store_true')
    args=ap.parse_args()
    run_dir=args.run_dir.resolve(); run_dir.mkdir(parents=True, exist_ok=True)
    tools=load_tools(args.tools)
    tools.bootstrap_vdm(args.repo)
    import numpy as np
    np.random.seed(args.seed)
    from vdm_rt.core.sparse_connectome import SparseConnectome
    from vdm_rt.core.bus import AnnounceBus
    from vdm_rt.core.adc import ADC
    from vdm_rt.core.engine import CoreEngine
    from vdm_rt.runtime.events_adapter import observations_to_events, adc_metrics_to_event
    records=[json.loads(line) for line in Path(args.schedule).read_text(encoding='utf-8').splitlines() if line.strip()]
    records=records[:args.ticks]
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
    (run_dir/'run_config.json').write_text(json.dumps(vars(args), indent=2, default=str), encoding='utf-8')
    source_counts=Counter(); id_counts=Counter(); phase_counts=Counter(); kind_counts=Counter(); witness_by_kind=Counter(); witness_by_phase=Counter(); commands_by_kind=Counter(); commands_by_input=Counter(); witness_records=[]; rows=[]; trace_rows=[]
    start=time.time(); completed=0
    with tools.ScanFirewall(C):
        for i,rec0 in enumerate(records):
            if time.time()-start > args.max_wall_s: break
            tick=int(rec0['tick']); text=rec0['text']; kind=rec0['kind']; phase=rec0['phase']; input_id=rec0['input_id']
            t0=time.perf_counter()
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
            for cmd in sel['commands']:
                commands_by_kind[(kind,cmd['op'],cmd['lane'])]+=1; commands_by_input[(input_id,cmd['op'],cmd['lane'])]+=1
            for ev in sel['emitted']:
                ev.update({'kind':kind,'phase':phase,'input_id':input_id,'text':text})
                witness_records.append(ev); witness_by_kind[kind]+=1; witness_by_phase[phase]+=1
            findings=dict(getattr(C,'findings',{}) or {})
            row={'tick':tick,'phase':phase,'kind':kind,'input_id':input_id,'text':text,'stim_count':len(stim),'stim_hash':tools.sha_list(stim),'obs_count':len(obs),'obs_nodes_count':len(obs_nodes),'obs_nodes_unique':len(set(obs_nodes)),'adc_territories':int(adc_m.get('adc_territories',0)),'adc_boundaries':int(adc_m.get('adc_boundaries',0)),'adc_cycle_hits':int(adc_m.get('adc_cycle_hits',0)),'vt_visits':int(findings.get('vt_visits',0)),'vt_unique':int(findings.get('vt_unique',0)),'vt_coverage':float(findings.get('vt_coverage',0.0)),'vt_entropy':float(findings.get('vt_entropy',0.0)),'sie2_valence':float(getattr(C,'_last_sie2_valence',0.0) or 0.0),'active_ops':' '.join(sel['active_ops']),'active_lanes':' '.join(sel['active_lanes']),'commands':json.dumps(sel['commands']),'witnesses':' '.join(ev['witness'] for ev in sel['emitted']),'top_trace':json.dumps(sel['top_trace']),'release_lane':sel['release_lane'],'release_score':sel['release_score'],'gate_pressure':sel['gate_pressure'],'tick_s':time.perf_counter()-t0}
            rows.append(row)
            trace_rows.append({'tick':tick,'phase':phase,'kind':kind,'input_id':input_id,'text':text,'selector':sel})
            source_counts['curriculum']+=1; id_counts[input_id]+=1; phase_counts[phase]+=1; kind_counts[kind]+=1
            completed=i+1
    # write files
    if rows:
        with open(run_dir/'tick_rows.csv','w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with open(run_dir/'trace_log.jsonl','w',encoding='utf-8') as f:
        for r in trace_rows: f.write(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n')
    with open(run_dir/'utd_events.jsonl','w',encoding='utf-8') as f:
        for r in witness_records: f.write(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n')
    with open(run_dir/'ute_input_stream.jsonl','w',encoding='utf-8') as f:
        for r in records[:completed]: f.write(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n')
    with open(run_dir/'first160_io.txt','w',encoding='utf-8') as f:
        for r in rows[:160]:
            cmds=json.loads(r['commands']) if r['commands'] else []
            cmdtxt=' '.join(f"{c['op']}:{c['lane']}" for c in cmds[:4])
            suffix=(" -> "+cmdtxt if cmdtxt else "") + ((" | WIT "+r['witnesses']) if r['witnesses'] else "")
            f.write(f"{r['tick']:04d} [{r['phase']}/{r['kind']}/{r['input_id']}] {r['text']}{suffix}\n")
    with open(run_dir/'first80_after_shift.txt','w',encoding='utf-8') as f:
        for r in [x for x in rows if x['tick']>=1000][:80]:
            cmds=json.loads(r['commands']) if r['commands'] else []
            cmdtxt=' '.join(f"{c['op']}:{c['lane']}" for c in cmds[:4])
            suffix=(" -> "+cmdtxt if cmdtxt else "") + ((" | WIT "+r['witnesses']) if r['witnesses'] else "")
            f.write(f"{r['tick']:04d} [{r['phase']}/{r['kind']}/{r['input_id']}] {r['text']}{suffix}\n")
    final_h5=None
    if args.save_h5:
        try:
            from vdm_rt.core.memory import save_checkpoint
            final_h5=str(save_checkpoint(str(run_dir), completed, C, fmt='h5', adc=adc))
        except Exception as e:
            final_h5='SAVE_FAILED: '+repr(e)
    # phase summaries
    phase_summary=[]
    for phase,c in phase_counts.items():
        w=sum(1 for ev in witness_records if ev['phase']==phase)
        phase_summary.append({'phase':phase,'ticks':c,'witnesses':w,'witness_rate':round(w/max(1,c),4)})
    kind_summary=[]
    for kind,c in kind_counts.items():
        w=sum(1 for ev in witness_records if ev['kind']==kind)
        kind_summary.append({'kind':kind,'ticks':c,'witnesses':w,'witness_rate':round(w/max(1,c),4)})
    input_summary=[]
    for iid,c in id_counts.items():
        w=sum(1 for ev in witness_records if ev['input_id']==iid)
        text=next((r['text'] for r in records if r['input_id']==iid), '')
        input_summary.append({'input_id':iid,'text':text,'ticks':c,'witnesses':w,'witness_rate':round(w/max(1,c),4)})
    with open(run_dir/'phase_summary.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=['phase','ticks','witnesses','witness_rate']); w.writeheader(); w.writerows(phase_summary)
    with open(run_dir/'kind_summary.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=['kind','ticks','witnesses','witness_rate']); w.writeheader(); w.writerows(kind_summary)
    with open(run_dir/'input_summary.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=['input_id','text','ticks','witnesses','witness_rate']); w.writeheader(); w.writerows(sorted(input_summary,key=lambda x:x['input_id']))
    summary={'run_dir':str(run_dir),'ticks_requested':args.ticks,'ticks_completed':completed,'elapsed_s':round(time.time()-start,4),'mean_wall_tick_s':round((time.time()-start)/max(1,completed),4),'neurons':args.neurons,'walkers':args.walkers,'seed':args.seed,'phase_summary':phase_summary,'kind_summary':kind_summary,'input_summary':sorted(input_summary,key=lambda x:x['input_id']),'witness_count':len(witness_records),'top_commands_by_kind':[{'kind':k,'op':op,'lane':lane,'count':c} for (k,op,lane),c in commands_by_kind.most_common(50)],'top_commands_by_input':[{'input_id':iid,'op':op,'lane':lane,'count':c} for (iid,op,lane),c in commands_by_input.most_common(50)],'final_h5':final_h5,'scan_firewall':'passed'}
    (run_dir/'run_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
if __name__=='__main__':
    main()
