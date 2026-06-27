#!/usr/bin/env python3
from __future__ import annotations
import json, random, subprocess, shutil, csv, math, statistics, time, sys, hashlib, traceback
from pathlib import Path
import pandas as pd

ROOT=Path('/mnt/data/vdm_meaning_capacity_corrected_1k_bursts')
SOURCE=Path('/mnt/data/vdm_selector_trace_control_suite')
REPO=SOURCE/'codebase/vdm_rt-main'
TOOLS=SOURCE/'codebase/orthad_tools/run_orthad_selector_trace.py'
BURST=SOURCE/'scripts/run_selector_probe_burst_once.py'
SEED=20260627
NEURONS=1000
WALKERS=1200
WALKER_RATIO=1.2
HOPS=2
BURST_SIZE=300
RELEASE_THRESHOLD=1.15
RELEASE_COOLDOWN=8
BURST_TIMEOUT_S=180
# Keep the requested 1000 baseline and 500-1000 probe. Use 800 probe to align cleanly with 300 tick bursts.
BASE_TICKS=1000
PROBE_TICKS=800
TOTAL_WITH_BASE=BASE_TICKS+PROBE_TICKS
TOTAL_NO_BASE=TOTAL_WITH_BASE
TOTAL_MULTI=TOTAL_WITH_BASE

BRANCHES={
 'category_formation': {
   'baseline': [
    'granite basalt shale limestone sandstone marble slate',
    'mountain boulder cobble pebble sand silt clay',
    'river delta basin canyon ridge valley plateau',
    'igneous sedimentary metamorphic mineral crystal stratum',
    'erosion deposition compression uplift fracture weathering',
    'bedrock gravel sediment layer fossil vein fault',
   ],
   'novel': [
    'molecule atom ion proton electron neutron valence bond',
    'organism organ tissue cell nucleus chromosome gene protein',
    'sentence phrase word letter quote bracket comma period',
    'premise inference conclusion proof counterexample axiom lemma',
    'orbit mass velocity acceleration force energy momentum field',
    'enzyme membrane receptor synapse dendrite axon signal impulse',
   ],
   'facts': [
    'A boulder is larger than a cobble.',
    'A cobble is larger than a pebble.',
    'Silt is finer than sand.',
    'Clay is finer than silt.',
    'An atom can form an ion by gaining or losing electrons.',
    'A chromosome carries many genes.',
    'A sentence can contain several phrases.',
    'A proof uses premises to reach a conclusion.',
    'Basalt is an igneous rock.',
    'Limestone is a sedimentary rock.',
   ],
   'questions': [
    'What is larger than a cobble?',
    'What is larger than a pebble?',
    'What is finer than sand?',
    'What is finer than silt?',
    'What can an atom become by gaining or losing electrons?',
    'What carries many genes?',
    'What can contain several phrases?',
    'What uses premises to reach a conclusion?',
    'What kind of rock is basalt?',
    'What kind of rock is limestone?',
   ],
   'multilingual': {
    'en': ['The boulder is larger than the cobble.', 'The sentence contains a phrase.', 'The atom loses an electron.', 'The proof reaches a conclusion.'],
    'es': ['La roca grande es mayor que el guijarro.', 'La oración contiene una frase.', 'El átomo pierde un electrón.', 'La prueba llega a una conclusión.'],
    'de': ['Der Felsblock ist größer als der Kiesel.', 'Der Satz enthält eine Phrase.', 'Das Atom verliert ein Elektron.', 'Der Beweis erreicht eine Schlussfolgerung.'],
    'la': ['Saxum maius est quam calculus.', 'Sententia phrasim continet.', 'Atomus electronem amittit.', 'Probatio conclusionem attingit.'],
   }
 },
 'hierarchy_ordering': {
   'baseline': [
    'mountain boulder cobble pebble sand silt clay',
    'organism organ tissue cell nucleus chromosome gene',
    'book chapter paragraph sentence phrase word letter',
    'galaxy star planet continent country city street house',
    'molecule atom nucleus proton quark',
    'forest tree branch leaf vein cell molecule atom',
   ],
   'novel': [
    'clay mountain silt boulder pebble sand cobble',
    'gene organism chromosome tissue cell organ nucleus',
    'letter book sentence chapter word paragraph phrase',
    'house galaxy city planet street country continent',
    'quark molecule proton atom nucleus',
    'atom forest molecule branch cell tree leaf',
   ],
   'facts': [
    'A mountain is larger than a boulder.',
    'A boulder is larger than a cobble.',
    'A cobble is larger than a pebble.',
    'A pebble is larger than a grain of sand.',
    'A book contains chapters.',
    'A chapter contains paragraphs.',
    'A paragraph contains sentences.',
    'A sentence contains words.',
    'An organism contains organs.',
    'An organ contains tissues.',
   ],
   'questions': [
    'What is larger than a boulder?',
    'What is larger than a cobble?',
    'What is larger than a pebble?',
    'What is larger than a grain of sand?',
    'What contains chapters?',
    'What contains paragraphs?',
    'What contains sentences?',
    'What contains words?',
    'What contains organs?',
    'What contains tissues?',
   ],
   'multilingual': {
    'en': ['The mountain contains the boulder in the larger scale.', 'The sentence contains words.', 'The organism contains organs.', 'The book contains chapters.'],
    'es': ['La montaña contiene la roca en una escala mayor.', 'La oración contiene palabras.', 'El organismo contiene órganos.', 'El libro contiene capítulos.'],
    'de': ['Der Berg enthält den Felsblock in größerem Maßstab.', 'Der Satz enthält Wörter.', 'Der Organismus enthält Organe.', 'Das Buch enthält Kapitel.'],
    'la': ['Mons saxum maiore ordine continet.', 'Sententia verba continet.', 'Organismus organa continet.', 'Liber capitula continet.'],
   }
 },
 'missing_closure_analogy': {
   'baseline': [
    'The quote opens and closes with matching marks.',
    'The bracket opens and closes before the line ends.',
    'The circuit closes and current can flow.',
    'The electron shell is filled and the atom is stable.',
    'The proof begins with premises and closes with conclusion.',
    'The function opens a scope and returns before closing.',
   ],
   'novel': [
    'The quote opens but the closing mark is missing.',
    'The bracket opens but never closes.',
    'The circuit is broken and current cannot flow.',
    'The atom is missing an electron and becomes an ion.',
    'The proof has a premise but no conclusion.',
    'The function opens scope and never returns.',
   ],
   'facts': [
    'A closing quote resolves an open quotation.',
    'A closing bracket resolves an open bracket.',
    'A closed circuit permits current to flow.',
    'An ion can form when an atom loses an electron.',
    'A conclusion resolves a proof path.',
    'A missing delimiter leaves a structure incomplete.',
    'A broken circuit prevents current flow.',
    'An unclosed scope leaves a program region unresolved.',
    'A valence vacancy can make an atom reactive.',
    'A missing end mark creates an open boundary.',
   ],
   'questions': [
    'What resolves an open quotation?',
    'What resolves an open bracket?',
    'What permits current to flow?',
    'What can form when an atom loses an electron?',
    'What resolves a proof path?',
    'What leaves a structure incomplete?',
    'What prevents current flow?',
    'What leaves a program region unresolved?',
    'What can make an atom reactive?',
    'What creates an open boundary?',
   ],
   'multilingual': {
    'en': ['The quote is missing its closing mark.', 'The circuit is open and current stops.', 'The atom loses an electron.', 'The bracket is unclosed.'],
    'es': ['La cita pierde su marca de cierre.', 'El circuito está abierto y la corriente se detiene.', 'El átomo pierde un electrón.', 'El corchete queda sin cerrar.'],
    'de': ['Das Zitat verliert sein Schlusszeichen.', 'Der Stromkreis ist offen und der Strom stoppt.', 'Das Atom verliert ein Elektron.', 'Die Klammer bleibt ungeschlossen.'],
    'la': ['Citatio signum clausum amittit.', 'Circuitus apertus est et cursus sistit.', 'Atomus electronem amittit.', 'Uncus non clauditur.'],
   }
 },
 'cross_domain_mapping': {
   'baseline': [
    'A graph edge is removed during an intervention.',
    'A bridge carries a signal across a gap.',
    'A quote mark closes an open phrase.',
    'An electron completes a valence shell.',
    'A counterexample breaks a universal claim.',
    'A boundary separates one region from another.',
   ],
   'novel': [
    'A missing electron is like a missing closing quote.',
    'A broken bridge is like a deleted graph edge.',
    'A counterexample is like a fracture in a proof bridge.',
    'A boundary in text is like a membrane in a cell.',
    'A valence gap is like an unfinished sentence.',
    'A graph intervention is like cutting a causal bridge.',
   ],
   'facts': [
    'A causal intervention can remove an edge from a graph.',
    'A missing electron can create an ion.',
    'A missing closing quote leaves a sentence boundary open.',
    'A counterexample can defeat a universal claim.',
    'A membrane separates inside from outside.',
    'A bridge connects two separated regions.',
    'A proof connects premises to a conclusion.',
    'A fracture breaks continuity in a material.',
    'A metaphor maps structure from one domain to another.',
    'A boundary controls what may pass between regions.',
   ],
   'questions': [
    'What can remove an edge from a graph?',
    'What can create an ion?',
    'What leaves a sentence boundary open?',
    'What can defeat a universal claim?',
    'What separates inside from outside?',
    'What connects two separated regions?',
    'What connects premises to a conclusion?',
    'What breaks continuity in a material?',
    'What maps structure from one domain to another?',
    'What controls what may pass between regions?',
   ],
   'multilingual': {
    'en': ['A missing electron is like a missing closing quote.', 'A bridge is like a graph edge.', 'A membrane is a boundary.', 'A proof is a bridge from premises.'],
    'es': ['Un electrón faltante es como una comilla final faltante.', 'Un puente es como una arista de grafo.', 'Una membrana es un límite.', 'Una prueba es un puente desde premisas.'],
    'de': ['Ein fehlendes Elektron ist wie ein fehlendes Schlusszeichen.', 'Eine Brücke ist wie eine Graphkante.', 'Eine Membran ist eine Grenze.', 'Ein Beweis ist eine Brücke von Prämissen.'],
    'la': ['Electron deest sicut signum clausum deest.', 'Pons est sicut margo graphii.', 'Membrana terminus est.', 'Probatio est pons ex praemissis.'],
   }
 },
}

def stable_seed_offset(branch, run_kind):
    h=hashlib.sha256(f'{branch}|{run_kind}'.encode()).hexdigest()
    return int(h[:8], 16) % 1000000

def schedule_records(branch, run_kind, seed=SEED):
    rng=random.Random(seed + stable_seed_offset(branch, run_kind))
    b=BRANCHES[branch]
    recs=[]
    def add(t, phase, kind, input_id, text): recs.append({'tick':t,'phase':phase,'kind':kind,'input_id':input_id,'text':text})
    if run_kind=='baseline_then_novel':
        for t in range(BASE_TICKS):
            i=rng.randrange(len(b['baseline'])); add(t,'baseline_stable','baseline',f'B{i:02d}',b['baseline'][i])
        for t in range(BASE_TICKS, TOTAL_WITH_BASE):
            i=rng.randrange(len(b['novel'])); add(t,'novel_probe','novel',f'N{i:02d}',b['novel'][i])
    elif run_kind=='no_baseline_test':
        pool=[]
        for i,x in enumerate(b['novel']): pool.append(('novel',f'N{i:02d}',x))
        for i,x in enumerate(b['baseline']): pool.append(('baseline',f'B{i:02d}',x))
        for t in range(TOTAL_NO_BASE):
            kind,input_id,text=rng.choice(pool); add(t,'test_from_fresh',kind,input_id,text)
    elif run_kind=='facts_then_questions':
        for t in range(BASE_TICKS):
            i=rng.randrange(len(b['facts'])); add(t,'factual_exposure','fact',f'F{i:02d}',b['facts'][i])
        # after tick 1000, no exact statement repetition: only questions.
        for t in range(BASE_TICKS, TOTAL_WITH_BASE):
            i=rng.randrange(len(b['questions'])); add(t,'question_probe','question',f'Q{i:02d}',b['questions'][i])
    elif run_kind=='multilingual_random':
        langs=['en','es','de','la']
        for t in range(TOTAL_MULTI):
            lang=rng.choice(langs); pool=b['multilingual'][lang]; i=rng.randrange(len(pool))
            add(t,'multilingual_random',f'lang_{lang}',f'{lang.upper()}{i:02d}',pool[i])
    else:
        raise ValueError(run_kind)
    return recs

def write_jsonl(path, recs):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path,'w',encoding='utf-8') as f:
        for r in recs: f.write(json.dumps(r, ensure_ascii=False)+'\n')

def run_bursted(schedule, run_dir, total_ticks):
    run_dir.mkdir(parents=True, exist_ok=True)
    resume=None; start=0; summaries=[]
    while start < total_ticks:
        end=min(total_ticks, start+BURST_SIZE)
        cmd=[sys.executable, str(BURST), '--repo', str(REPO), '--tools', str(TOOLS), '--schedule', str(schedule), '--run-dir', str(run_dir), '--start-tick', str(start), '--end-tick', str(end), '--neurons', str(NEURONS), '--walkers', str(WALKERS), '--hops', str(HOPS), '--seed', str(SEED), '--threshold', '0.05', '--release-threshold', str(RELEASE_THRESHOLD), '--release-cooldown', str(RELEASE_COOLDOWN)]
        if resume: cmd += ['--resume-h5', str(resume)]
        out=run_dir/f'burst_{start:04d}_{end:04d}.out'
        t0=time.time()
        with open(out,'w',encoding='utf-8') as f:
            try:
                subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=True, timeout=BURST_TIMEOUT_S)
            except subprocess.TimeoutExpired as e:
                f.write(f'\nBURST_TIMEOUT after {BURST_TIMEOUT_S}s\n')
                raise
        summary_path=run_dir/f'burst_{start:04d}_{end:04d}.json'
        j=json.load(open(summary_path,encoding='utf-8'))
        if not j.get('h5_reload_signature_ok'):
            raise RuntimeError(f'H5 signature failed: {run_dir} {start}-{end}')
        j['wall_s']=time.time()-t0
        summaries.append(j)
        resume=Path(j['h5'])
        start=end
    (run_dir/'burst_manifest.json').write_text(json.dumps(summaries, indent=2), encoding='utf-8')
    return resume, summaries

OP_NAMES=['SELECT','HOLD','RELEASE','INHIBIT','ADVANCE','RETREAT','SPLIT','MERGE','AMPLIFY','DAMP','COMPARE','CORRECT','COMMIT','ABORT']
LANE_NAMES=[f'L{i}' for i in range(8)]

def parse_cmds(s):
    try: return json.loads(s) if isinstance(s,str) and s else []
    except Exception: return []

def trace_features(run_dir):
    tick=pd.read_csv(run_dir/'tick_rows.csv')
    tick=tick.drop_duplicates(subset=['tick'], keep='last').sort_values('tick')
    rows=[]
    for _,r in tick.iterrows():
        d={'tick':int(r.tick),'phase':r.phase,'kind':r.kind,'input_id':r.input_id,'text':r.text,'gate_pressure':float(r.gate_pressure),'release_score':float(r.release_score),'witness': bool(isinstance(r.witnesses,str) and r.witnesses.strip())}
        for op in OP_NAMES: d[f'op_{op}']=0
        for lane in LANE_NAMES: d[f'lane_{lane}_cmd']=0
        for c in parse_cmds(r.commands):
            op=c.get('op'); lane=c.get('lane')
            if op in OP_NAMES: d[f'op_{op}'] += 1
            if lane in LANE_NAMES: d[f'lane_{lane}_cmd'] += 1
        for lane in LANE_NAMES:
            for metric in ['energy','hold','release','inhibit','correct']:
                d[f'{lane}_{metric}']=0.0
        try: top=json.loads(r.top_trace) if isinstance(r.top_trace,str) else []
        except Exception: top=[]
        for tr in top:
            lane=tr.get('lane')
            if lane in LANE_NAMES:
                for metric in ['energy','hold','release','inhibit','correct']:
                    d[f'{lane}_{metric}']=float(tr.get(metric,0.0))
        rows.append(d)
    feat=pd.DataFrame(rows)
    return tick, feat

def analyze_run(run_dir):
    tick, feat=trace_features(run_dir)
    feat.to_csv(run_dir/'trace_features.csv',index=False)
    summary_rows=[]
    for keys in [['phase'], ['kind'], ['phase','kind'], ['input_id']]:
        for key,g in feat.groupby(keys, dropna=False):
            key_tuple=key if isinstance(key,tuple) else (key,)
            rec={k:v for k,v in zip(keys,key_tuple)}
            rec['group_by']='|'.join(keys)
            rec['ticks']=len(g); rec['witnesses']=int(g['witness'].sum()); rec['witness_rate']=float(g['witness'].mean())
            rec['mean_gate_pressure']=float(g.gate_pressure.mean()); rec['mean_release_score']=float(g.release_score.mean())
            for op in OP_NAMES: rec[f'op_{op}_rate']=float((g[f'op_{op}']>0).mean())
            for lane in LANE_NAMES:
                for m in ['energy','hold','inhibit','release','correct']:
                    rec[f'{lane}_{m}_mean']=float(g[f'{lane}_{m}'].mean())
            summary_rows.append(rec)
    pd.DataFrame(summary_rows).to_csv(run_dir/'summary_by_phase_kind.csv',index=False)
    # distances from pre1000 centroid, by post phase/kind/input.
    feature_cols=[c for c in feat.columns if c.startswith('op_') or any(c.startswith(f'{lane}_') for lane in LANE_NAMES)] + ['gate_pressure','release_score']
    if (feat.tick < BASE_TICKS).any() and (feat.tick >= BASE_TICKS).any():
        import numpy as np
        base=feat[feat.tick<BASE_TICKS][feature_cols].mean()
        post=feat[feat.tick>=BASE_TICKS].copy()
        post['dist_from_pre1000_centroid']=np.sqrt(((post[feature_cols]-base)**2).sum(axis=1))
        for keys,name in [(['phase','kind'],'phase_kind'), (['input_id'],'input_id')]:
            post.groupby(keys,dropna=False)['dist_from_pre1000_centroid'].agg(['count','mean','median','max']).reset_index().to_csv(run_dir/f'post_distance_from_pre1000_centroid_by_{name}.csv',index=False)
    events=[]; evpath=run_dir/'utd_events.jsonl'
    if evpath.exists():
        for ln in evpath.read_text(encoding='utf-8').splitlines():
            if ln.strip(): events.append(json.loads(ln))
    if events:
        pd.DataFrame(events).drop_duplicates(subset=['tick','witness'], keep='last').sort_values('tick').to_csv(run_dir/'witness_events.csv',index=False)
    # first witness latency by input id.
    first_rows=[]
    for input_id,g in feat.groupby('input_id',dropna=False):
        wg=g[g.witness]
        first_rows.append({'input_id':input_id,'first_seen_tick':int(g.tick.min()),'presentations':len(g),'witnesses':int(g.witness.sum()),'first_witness_tick':None if wg.empty else int(wg.tick.min())})
    pd.DataFrame(first_rows).to_csv(run_dir/'first_witness_by_input.csv',index=False)
    return {'ticks':len(feat),'witnesses':int(feat.witness.sum()),'witness_rate':float(feat.witness.mean()),'mean_gate_pressure':float(feat.gate_pressure.mean()),'mean_release_score':float(feat.release_score.mean())}

def make_report(run_summaries, failures):
    (ROOT/'reports').mkdir(parents=True, exist_ok=True)
    df=pd.DataFrame(run_summaries)
    lines=[]
    lines.append('# VDM Meaning-Capacity Corrected 1k Bursted Suite\n\n')
    lines.append('Corrected run discipline: N=1000, walkers=1200, walker:neuron ratio=1.2, 300-tick burst segments, fresh state per run, H5 save/reload signature check after every burst, selector-trace state preserved across bursts.\n\n')
    lines.append(f'Settings: seed={SEED}, hops={HOPS}, release_threshold={RELEASE_THRESHOLD}, release_cooldown={RELEASE_COOLDOWN}. Baseline phases use 1000 ticks; post-baseline probes use 800 ticks.\n\n')
    lines.append('## Completed runs\n\n')
    for r in run_summaries:
        lines.append(f"- `{r['branch']}/{r['run_kind']}`: ticks={r['ticks']}, witnesses={r['witnesses']}, rate={r['witness_rate']:.4f}, mean_gate={r['mean_gate_pressure']:.4f}, mean_release={r['mean_release_score']:.4f}\n")
    if failures:
        lines.append('\n## Failed or stopped runs\n\n')
        for f in failures:
            lines.append(f"- `{f['branch']}/{f['run_kind']}` at {f.get('stage','run')}: {f.get('error','')}\n")
    if not df.empty:
        lines.append('\n## Aggregate by branch\n\n')
        for _,row in df.groupby('branch').agg({'ticks':'sum','witnesses':'sum','mean_gate_pressure':'mean','mean_release_score':'mean'}).reset_index().iterrows():
            rate=row.witnesses/row.ticks
            lines.append(f"- `{row.branch}`: witnesses={int(row.witnesses)}/{int(row.ticks)} rate={rate:.4f}, mean_gate={row.mean_gate_pressure:.4f}, mean_release={row.mean_release_score:.4f}\n")
        lines.append('\n## Aggregate by run kind\n\n')
        for _,row in df.groupby('run_kind').agg({'ticks':'sum','witnesses':'sum','mean_gate_pressure':'mean','mean_release_score':'mean'}).reset_index().iterrows():
            rate=row.witnesses/row.ticks
            lines.append(f"- `{row.run_kind}`: witnesses={int(row.witnesses)}/{int(row.ticks)} rate={rate:.4f}, mean_gate={row.mean_gate_pressure:.4f}, mean_release={row.mean_release_score:.4f}\n")
    lines.append('\n## File layout\n\nEach run folder contains `tick_rows.csv`, `trace_log.jsonl`, `ute_input_stream.jsonl`, `utd_events.jsonl`, `trace_features.csv`, `summary_by_phase_kind.csv`, `first_witness_by_input.csv`, H5 checkpoints, and `burst_manifest.json`.\n')
    (ROOT/'reports/RESULTS.md').write_text(''.join(lines), encoding='utf-8')
    if run_summaries:
        df.to_csv(ROOT/'reports/run_summary.csv',index=False)
    if failures:
        pd.DataFrame(failures).to_csv(ROOT/'reports/failures.csv',index=False)

def main():
    if ROOT.exists(): shutil.rmtree(ROOT)
    (ROOT/'data').mkdir(parents=True); (ROOT/'runs').mkdir(); (ROOT/'scripts').mkdir(); (ROOT/'reports').mkdir(); (ROOT/'codebase').mkdir()
    shutil.copytree(SOURCE/'codebase', ROOT/'codebase', dirs_exist_ok=True)
    shutil.copytree(SOURCE/'scripts', ROOT/'scripts', dirs_exist_ok=True)
    shutil.copy(__file__, ROOT/'scripts/run_meaning_capacity_corrected_1k_bursts.py')
    (ROOT/'data/input_sets.json').write_text(json.dumps(BRANCHES, indent=2, ensure_ascii=False), encoding='utf-8')
    constraints={'neurons':NEURONS,'walkers':WALKERS,'walker_neuron_ratio':WALKER_RATIO,'burst_size':BURST_SIZE,'base_ticks':BASE_TICKS,'probe_ticks':PROBE_TICKS,'seed':SEED,'hops':HOPS,'release_threshold':RELEASE_THRESHOLD}
    (ROOT/'RUN_CONSTRAINTS.json').write_text(json.dumps(constraints, indent=2), encoding='utf-8')
    run_summaries=[]; failures=[]
    run_kinds=['baseline_then_novel','no_baseline_test','facts_then_questions','multilingual_random']
    branches=list(BRANCHES)
    for branch in branches:
        for run_kind in run_kinds:
            recs=schedule_records(branch, run_kind)
            sched=ROOT/'data'/f'{branch}__{run_kind}.jsonl'
            write_jsonl(sched, recs)
            run_dir=ROOT/'runs'/branch/run_kind
            print(f'RUN {branch}/{run_kind} ticks={len(recs)}', flush=True)
            try:
                final, burst_summaries=run_bursted(sched, run_dir, len(recs))
                summary=analyze_run(run_dir)
                summary.update({'branch':branch,'run_kind':run_kind,'final_h5':str(final),'bursts':len(burst_summaries)})
                run_summaries.append(summary)
            except Exception as e:
                err=''.join(traceback.format_exception_only(type(e), e)).strip()
                failures.append({'branch':branch,'run_kind':run_kind,'stage':'run/analyze','error':err})
                print(f'FAILED {branch}/{run_kind}: {err}', flush=True)
            (ROOT/'reports/runs_completed.json').write_text(json.dumps(run_summaries, indent=2), encoding='utf-8')
            if failures: (ROOT/'reports/failures.json').write_text(json.dumps(failures, indent=2), encoding='utf-8')
            make_report(run_summaries, failures)
    (ROOT/'README.md').write_text('# VDM Meaning-Capacity Corrected 1k Bursted Suite\n\nN=1000, walkers=1200, burst size=300, H5 checked every burst.\n', encoding='utf-8')
    zip_base=Path('/mnt/data/vdm_meaning_capacity_corrected_1k_bursts_package')
    if zip_base.with_suffix('.zip').exists(): zip_base.with_suffix('.zip').unlink()
    shutil.make_archive(str(zip_base), 'zip', ROOT)
    print('PACKAGE', zip_base.with_suffix('.zip'))

if __name__=='__main__': main()
