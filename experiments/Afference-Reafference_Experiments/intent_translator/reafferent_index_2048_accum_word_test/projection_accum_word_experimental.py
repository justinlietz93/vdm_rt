from __future__ import annotations
import json, math, zipfile, shutil
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path('/mnt/data')
PKG = ROOT/'vdm_pkg/07_vdm_meaning_capacity_corrected_1k_bursts_package'
INDEX = ROOT/'reafferent_utterance_index_2048'
OUT = ROOT/'reafferent_index_2048_accum_word_test'
if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir(parents=True)

schema = json.loads((INDEX/'index_schema_2048.json').read_text())
AXES = schema['axes']
A2I = {a:i for i,a in enumerate(AXES)}
OPS = ['SELECT','RELEASE','HOLD','ADVANCE','COMMIT','COMPARE','RETREAT','ABORT','CORRECT','MERGE','SPLIT','DAMP','INHIBIT','AMPLIFY']

def vec(**kw):
    v=np.zeros(len(AXES), dtype=np.float32)
    for k,val in kw.items():
        if k in A2I:
            v[A2I[k]]=max(v[A2I[k]], float(val))
    return v

def add(v, axis, val):
    if axis in A2I:
        v[A2I[axis]] += float(val)

def clamp01_arr(v):
    return np.clip(v,0,1)

def norm01(x, scale=1.0):
    try: x=float(x)
    except Exception: return 0.0
    if x<=0: return 0.0
    return float(1-math.exp(-x/scale))

def get(row, k, default=0.0):
    try:
        x=row.get(k, default)
        if pd.isna(x): return default
        return float(x)
    except Exception:
        return default

def op(row, name):
    return get(row, 'op_'+name, 0.0)

def tick_delta(row, prev_input=None, interval_input_seen=None, final_trigger=False):
    # Domain-agnostic tick -> posture64 delta. This is intentionally local: every tick contributes a word-stroke.
    v=np.zeros(len(AXES), dtype=np.float32)
    gate=get(row,'gate_pressure'); rel=get(row,'release_score')
    gate_n=min(1, gate/1.4); rel_n=min(1, rel/1.0)
    # Input recurrence/familiarity, without looking at content domain.
    inp=str(row.get('input_id',''))
    prev_same = (prev_input is not None and inp==prev_input)
    seen_count = interval_input_seen.get(inp,0) if interval_input_seen else 0
    if prev_same:
        add(v,'familiarity',0.16); add(v,'recognition',0.12); add(v,'memory',0.08); add(v,'expectation',0.04)
    elif seen_count>0:
        s=min(1,seen_count/5)
        add(v,'familiarity',0.04+0.08*s); add(v,'memory',0.04+0.06*s); add(v,'recognition',0.03+0.05*s)
    # Modulation evidence.
    add(v,'salience',0.10*gate_n + 0.08*rel_n)
    add(v,'intensity',0.10*gate_n + 0.06*op(row,'AMPLIFY'))
    if str(row.get('kind','')).lower()=='novel' or 'novel' in str(row.get('phase','')).lower():
        add(v,'novelty',0.08); add(v,'curiosity',0.05); add(v,'search',0.03)
    # Ops as posture strokes.
    s=min(1,op(row,'SELECT')/3.0)
    if s:
        add(v,'attention',0.18*s); add(v,'orientation',0.08*s); add(v,'search',0.06*s); add(v,'recognition',0.06*s); add(v,'comparison',0.03*s)
    r=min(1,op(row,'RELEASE')/3.0)
    if r:
        add(v,'release_pressure',0.18*r); add(v,'readiness',0.08*r); add(v,'transition',0.08*r); add(v,'approach',0.04*r)
    h=min(1,op(row,'HOLD')/3.0)
    if h:
        add(v,'restraint',0.18*h); add(v,'hesitation',0.11*h); add(v,'stability',0.09*h); add(v,'containment',0.05*h)
    a=min(1,op(row,'ADVANCE')/3.0)
    if a:
        add(v,'readiness',0.18*a); add(v,'transition',0.12*a); add(v,'commitment',0.07*a); add(v,'approach',0.05*a)
    c=min(1,op(row,'COMMIT')/3.0)
    if c:
        add(v,'commitment',0.16*c); add(v,'acceptance',0.10*c); add(v,'confidence',0.07*c); add(v,'completion',0.04*c)
    cmp=min(1,op(row,'COMPARE')/3.0)
    if cmp:
        add(v,'comparison',0.18*cmp); add(v,'uncertainty',0.08*cmp); add(v,'ambiguity',0.07*cmp); add(v,'difference',0.06*cmp); add(v,'search',0.06*cmp)
    ret=min(1,op(row,'RETREAT')/3.0)
    if ret:
        add(v,'withdrawal',0.16*ret); add(v,'avoidance',0.12*ret); add(v,'hesitation',0.08*ret); add(v,'doubt',0.06*ret)
    ab=min(1,op(row,'ABORT')/3.0)
    if ab:
        add(v,'rejection',0.18*ab); add(v,'mismatch',0.12*ab); add(v,'restraint',0.08*ab); add(v,'conflict',0.06*ab)
    cor=min(1,op(row,'CORRECT')/3.0)
    if cor:
        add(v,'repair',0.16*cor); add(v,'correction',0.16*cor); add(v,'alignment',0.08*cor); add(v,'search',0.04*cor)
    m=min(1,op(row,'MERGE')/3.0)
    if m:
        add(v,'connection',0.16*m); add(v,'similarity',0.10*m); add(v,'coherence',0.08*m); add(v,'alignment',0.04*m)
    sp=min(1,op(row,'SPLIT')/3.0)
    if sp:
        add(v,'separation',0.16*sp); add(v,'boundary',0.10*sp); add(v,'difference',0.08*sp); add(v,'ambiguity',0.04*sp)
    damp=min(1,op(row,'DAMP')/3.0)
    if damp:
        add(v,'calm',0.08*damp); add(v,'restraint',0.06*damp); add(v,'friction',0.04*damp)
    inh=min(1,op(row,'INHIBIT')/3.0)
    if inh:
        add(v,'restraint',0.10*inh); add(v,'friction',0.07*inh); add(v,'avoidance',0.03*inh)
    amp=min(1,op(row,'AMPLIFY')/3.0)
    if amp:
        add(v,'intensity',0.15*amp); add(v,'salience',0.08*amp); add(v,'saturation',0.08*amp); add(v,'importance',0.06*amp)
    if gate > 0.9:
        add(v,'urgency',0.08*gate_n); add(v,'salience',0.08*gate_n); add(v,'intensity',0.05*gate_n)
    if rel > 0.7:
        add(v,'readiness',0.08*rel_n); add(v,'release_pressure',0.08*rel_n)
    # Final trigger adds the witness act as a trigger-stroke, not a separate query.
    if final_trigger:
        add(v,'agency',0.10); add(v,'confirmation',0.12); add(v,'completion',0.08)
        if op(row,'SELECT')>0 and op(row,'RELEASE')>0:
            add(v,'recognition',0.12); add(v,'acceptance',0.08); add(v,'readiness',0.08)
        if op(row,'HOLD')>0 and op(row,'RELEASE')>0:
            add(v,'restraint',0.08); add(v,'stability',0.08); add(v,'confirmation',0.06)
        if op(row,'ADVANCE')>0:
            add(v,'transition',0.08); add(v,'readiness',0.08)
        if gate>1.0:
            add(v,'confidence',0.07); add(v,'certainty',0.05)
    return clamp01_arr(v)

# Load index and bank.
bank=[json.loads(l) for l in open(INDEX/'utterance_bank_2048.jsonl', encoding='utf-8') if l.strip()]
npz=np.load(INDEX/'utterance_index_2048.npz', allow_pickle=True)
X=npz['vectors'].astype(np.float32)
axes=[str(x) for x in npz['axes']]
# axis weights: keep posture axes sharp; damp generic axes.
weights=np.ones(len(axes), dtype=np.float32)
for a,w in {
    'salience':0.25,'intensity':0.25,'valence':0.1,'attention':0.45,
    'engagement':0.55,'interest':0.55,'urgency':0.35,'release_pressure':0.35,
    'stability':0.65,'transition':0.65,'restraint':0.8,'readiness':0.8,'hesitation':0.85,
    'agency':0.55,'orientation':0.65,'importance':0.45,'saturation':0.55
}.items():
    if a in A2I: weights[A2I[a]]=w
Y=X*weights
Y=Y/(np.linalg.norm(Y,axis=1,keepdims=True)+1e-9)

def axis_dict(v, minv=1e-4):
    return {axes[i]: round(float(x),6) for i,x in enumerate(v) if x>minv}

def query(v,k=8):
    vv=v.astype(np.float32)*weights
    vv=vv/(np.linalg.norm(vv)+1e-9)
    sims=Y@vv
    idx=np.argsort(-sims)[:120]
    d=axis_dict(v)
    conf_raw=d.get('confidence',0)+d.get('confirmation',0)+d.get('certainty',0)-0.55*d.get('uncertainty',0)-0.55*d.get('doubt',0)
    conf=max(0,min(1,conf_raw/1.5))
    uncertainty=max(d.get('uncertainty',0),d.get('doubt',0),d.get('ambiguity',0),d.get('confusion',0),d.get('hesitation',0)*0.7)
    outs=[]
    for i in idx:
        b=bank[int(i)]
        bonus=0.0
        form=b.get('form',''); strength=b.get('strength',''); utt=b.get('utterance','')
        if conf>0.35:
            if form=='direct': bonus+=0.055
            elif form=='medium': bonus+=0.03
            elif form=='question': bonus-=0.05
            elif form=='weak': bonus-=0.025
            if strength in ('high','very_high'): bonus+=0.018
        if uncertainty>0.55 and conf<0.35:
            if form=='question': bonus+=0.04
            if form=='direct': bonus-=0.03
        # penalize oddly phrased high-confidence questions that the generation template created.
        if utt.startswith(('Do I certainly','Do I clearly','Do I strongly')) or 'without doubt?' in utt:
            bonus-=0.035
        outs.append({
            'id': b['id'], 'utterance': utt, 'family': b.get('family'), 'leaf': b.get('leaf'),
            'form': form, 'strength': strength, 'cosine': float(sims[i]), 'bonus': float(bonus),
            'score': float(sims[i]+bonus), 'distance': float(1-sims[i])
        })
    outs=sorted(outs, key=lambda r:-r['score'])[:k]
    for n,r in enumerate(outs,1): r['rank']=n
    return outs


def accumulate_interval(df, start_tick, end_tick, tau=12.0, retain=None, trigger_mix=0.22, max_rows=None):
    # Includes current witness trigger row. If max_rows set, cap only as runtime guard.
    win=df[(df['tick']>=start_tick)&(df['tick']<=end_tick)].copy()
    if max_rows and len(win)>max_rows:
        win=win.iloc[-max_rows:].copy()
    if retain is None:
        retain=math.exp(-1.0/tau)
    acc=np.zeros(len(axes), dtype=np.float32)
    steps=[]
    seen={}
    prev_input=None
    for _, row in win.iterrows():
        t=int(row['tick'])
        final=(t==end_tick)
        delta=tick_delta(row, prev_input=prev_input, interval_input_seen=seen, final_trigger=final)
        acc=retain*acc + delta
        # keep bounded but preserve relative accumulation
        acc=np.clip(acc,0,3.0)
        # visible word token: top axes at this tick after accumulation
        top_idx=np.argsort(-acc)[:5]
        steps.append({
            'tick':t,
            'input_id':str(row.get('input_id','')),
            'final_trigger':final,
            'top_accum_axes': [(axes[i], round(float(acc[i]),4)) for i in top_idx if acc[i]>1e-6],
            'delta_top_axes': [(axes[i], round(float(delta[i]),4)) for i in np.argsort(-delta)[:5] if delta[i]>1e-6],
        })
        seen[str(row.get('input_id',''))]=seen.get(str(row.get('input_id','')),0)+1
        prev_input=str(row.get('input_id',''))
    # Combine accumulated word and trigger stroke, because the trigger is part of the final word, not independent.
    trigger_vec = tick_delta(win.iloc[-1], prev_input=win.iloc[-2]['input_id'] if len(win)>1 else None, interval_input_seen=seen, final_trigger=True) if len(win)>0 else np.zeros(len(axes), dtype=np.float32)
    comp=(1-trigger_mix)*acc + trigger_mix*trigger_vec
    comp=comp/(np.max(comp)+1e-9)  # shape normalization for cosine semantics
    return win, comp, steps

# Run all witness intervals.
records=[]; topk_records=[]; examples=[]
selected_keys=[
    ('category_formation','baseline_then_novel',1557),
    ('cross_domain_mapping','baseline_then_novel',1794),
    ('hierarchy_ordering','facts_then_questions',1645),
    ('missing_closure_analogy','baseline_then_novel',1707),
]
all_dirs=sorted([p for p in (PKG/'runs').glob('*/*') if (p/'trace_features.csv').exists() and (p/'witness_events.csv').exists()])
for run_dir in all_dirs:
    branch=run_dir.parent.name; run=run_dir.name
    df=pd.read_csv(run_dir/'trace_features.csv')
    # ensure numeric tick
    df['tick']=df['tick'].astype(int)
    wit=pd.read_csv(run_dir/'witness_events.csv')
    wit['tick']=wit['tick'].astype(int)
    last=-1
    for _, wr in wit.sort_values('tick').iterrows():
        tick=int(wr['tick'])
        start=last+1
        win, comp, steps = accumulate_interval(df, start, tick, tau=12.0, max_rows=None)
        top=query(comp,k=8)
        margin = top[0]['score']-top[1]['score'] if len(top)>1 else None
        rec={
            'branch':branch,'run':run,'start_tick':start,'tick':tick,'rows':len(win),
            'witness':wr.get('witness',''), 'input_id':wr.get('input_id',''), 'phase':wr.get('phase',''), 'kind':wr.get('kind',''),
            'output':top[0]['utterance'], 'family':top[0]['family'], 'leaf':top[0]['leaf'],
            'score':top[0]['score'], 'cosine':top[0]['cosine'], 'distance':top[0]['distance'], 'rank_margin': margin,
            'top_axes': json.dumps([(axes[i], round(float(comp[i]),4)) for i in np.argsort(-comp)[:10] if comp[i]>1e-6]),
        }
        records.append(rec)
        for r in top:
            rr={'branch':branch,'run':run,'tick':tick,'witness':wr.get('witness',''), **r}
            topk_records.append(rr)
        if (branch,run,tick) in selected_keys or len(examples)<12 and tick in set(wit['tick'].head(1)):
            examples.append({
                'branch':branch,'run':run,'tick':tick,'witness':wr.get('witness',''), 'input_id':wr.get('input_id',''),
                'start_tick':start,'rows':len(win),'output':top[0]['utterance'],'top_k':top,
                'final_axis_vector': axis_dict(comp, minv=0.02),
                'accumulated_word_tail': steps[-8:]
            })
        last=tick

trans=pd.DataFrame(records)
topk=pd.DataFrame(topk_records)
trans.to_csv(OUT/'all_witness_accum_word_translation.csv', index=False)
topk.to_csv(OUT/'all_witness_accum_word_topk.csv', index=False)
# summaries
trans.groupby(['family']).size().sort_values(ascending=False).rename('count').reset_index().to_csv(OUT/'summary_top1_family_counts.csv', index=False)
trans.groupby(['branch','family']).size().rename('count').reset_index().sort_values(['branch','count'], ascending=[True,False]).to_csv(OUT/'summary_top1_family_by_branch.csv', index=False)
trans.groupby(['branch','run']).agg(witnesses=('tick','count'), mean_rows=('rows','mean'), median_margin=('rank_margin','median')).reset_index().to_csv(OUT/'summary_by_run.csv', index=False)
pd.DataFrame([{k:v for k,v in e.items() if k not in ('top_k','final_axis_vector','accumulated_word_tail')} for e in examples]).to_csv(OUT/'selected_example_outputs.csv', index=False)
(OUT/'selected_example_details.json').write_text(json.dumps(examples, indent=2), encoding='utf-8')

# Write scripts for reuse.
script = r'''#!/usr/bin/env python3
"""
QBL-style accumulated intent-word translator for VDM actuator witness events.

Correct input model:
- every tick contributes a posture-vector stroke to an accumulating intent word
- the word resets after each witness event
- at a witness event, the completed accumulated word + trigger stroke queries the 2048 utterance index
- top-1 utterance is emitted; top-k candidates are logged
"""
from __future__ import annotations
# This smoke-test package includes the generated outputs. Copy the implementation from
# projection_accum_word_experimental.py in this folder for the full runnable adapter.
'''
(OUT/'README_ACCUM_WORD_TEST.md').write_text(f'''# 2048 Reafferent Index Accumulated-Word Smoke Test

This corrects the previous smoke test.

The translator input is not independent row snapshots and not a generic window summary.
For each witness event, the system constructs one accumulated intent word across the entire inter-witness interval:

```text
previous witness reset
for each tick until current witness:
    tick_delta = local trace posture stroke
    intent_word = retain * intent_word + tick_delta
at witness tick:
    intent_word += trigger contribution
    query 2048 utterance index
    emit top-1 utterance
    log top-k candidates
```

This matches the requested Phase Calculus/QBL-style accumulation: the word is built every tick and sampled at the actuator witness.

## Outputs

- `all_witness_accum_word_translation.csv` — one row per witness event.
- `all_witness_accum_word_topk.csv` — top-8 candidates per witness.
- `selected_example_outputs.csv` — compact examples.
- `selected_example_details.json` — includes final axis vector and tail of accumulated tick-word evolution.
- `summary_top1_family_counts.csv`
- `summary_top1_family_by_branch.csv`
- `summary_by_run.csv`
- `projection_accum_word_experimental.py` — runnable implementation.

## Tested scope

- Runs: {len(all_dirs)}
- Witness events: {len(trans)}
- Index: 2048 first-person domain-agnostic utterances, 64 axes

## Runtime note

The current projection weights are experimental. The important correction is architectural: every tick contributes to an accumulating word; the witness trigger samples the completed word.
''', encoding='utf-8')
# Save full implementation by copying this build file but cleaner enough.
import inspect
source = Path('/tmp/build_corrected_accum_smoke.py').read_text()
# Trim top builder-specific running? It's okay as a reproducible smoke-test script.
(OUT/'projection_accum_word_experimental.py').write_text(source, encoding='utf-8')
# Also copy index schema summary for convenience
shutil.copy2(INDEX/'index_schema_2048.json', OUT/'index_schema_2048.json')
shutil.copy2(INDEX/'curation_audit.json', OUT/'index_curation_audit.json')
# zip
zip_path=ROOT/'reafferent_index_2048_accum_word_test_package.zip'
if zip_path.exists(): zip_path.unlink()
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for p in OUT.rglob('*'):
        z.write(p, p.relative_to(OUT.parent))
print('wrote', zip_path)
print('records', len(trans), 'topk', len(topk))
print(trans[trans['tick'].eq(1557) & trans['branch'].eq('category_formation') & trans['run'].eq('baseline_then_novel')].to_string(index=False))
print('\nexamples')
print(pd.read_csv(OUT/'selected_example_outputs.csv').head(10).to_string(index=False))
