#!/usr/bin/env python3
"""
Scaffold: project a witness-window trace composite into posture64_v1 axes.

This intentionally does NOT hard-code lane meanings. It turns generic trace evidence
into a domain-agnostic posture vector. Tune the weights against your real runs.
"""
from __future__ import annotations
import argparse, json, math, csv
from pathlib import Path

AXES = json.loads((Path(__file__).resolve().parent / 'index_schema_2048.json').read_text())['axes']

def clamp01(x): return max(0.0, min(1.0, float(x)))

def add(axis, amount, out):
    if axis in out:
        out[axis] = clamp01(out[axis] + amount)

def decay_weight(age, tau):
    return math.exp(-age / tau)

def load_rows_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def f(row, key, default=0.0):
    try: return float(row.get(key, default) or default)
    except Exception: return default

def has_op(row, op):
    text = ' '.join(str(row.get(k,'')) for k in row.keys() if 'op' in k.lower() or 'active' in k.lower() or 'cmd' in k.lower())
    return op.upper() in text.upper()

def project_rows(rows, tau=10.0):
    """rows should cover the interval since previous witness through current witness."""
    out = {a:0.0 for a in AXES}
    if not rows: return out
    end_tick = int(float(rows[-1].get('tick', len(rows)-1))) if 'tick' in rows[-1] else len(rows)-1
    total_w = 0.0
    # crude but useful generic evidence aggregation
    near_release_no_witness = 0.0
    repeated_input = 0.0
    last_input = rows[-1].get('input_id') or rows[-1].get('input') or ''
    prev_input = rows[-2].get('input_id') if len(rows) > 1 else None
    if prev_input and prev_input == last_input:
        repeated_input = 1.0
    for row in rows:
        tick = int(float(row.get('tick', 0))) if 'tick' in row else 0
        w = decay_weight(max(0, end_tick - tick), tau)
        total_w += w
        gate = f(row, 'gate_pressure')
        rel = f(row, 'release_score')
        witness = bool(str(row.get('witness','')).lower() in ('1','true','yes')) or bool(row.get('witness_id') or row.get('witness'))
        if rel > .45 and not witness:
            near_release_no_witness += w * rel
        if has_op(row, 'SELECT'):
            add('attention', .05*w, out); add('recognition', .04*w, out); add('comparison', .02*w, out)
        if has_op(row, 'COMPARE'):
            add('comparison', .08*w, out); add('uncertainty', .04*w, out); add('difference', .03*w, out)
        if has_op(row, 'HOLD'):
            add('restraint', .08*w, out); add('hesitation', .05*w, out); add('stability', .03*w, out)
        if has_op(row, 'RELEASE'):
            add('release_pressure', .06*w, out); add('transition', .04*w, out); add('readiness', .03*w, out)
        if has_op(row, 'ADVANCE'):
            add('readiness', .07*w, out); add('transition', .05*w, out); add('commitment', .03*w, out)
        if has_op(row, 'RETREAT'):
            add('withdrawal', .08*w, out); add('avoidance', .06*w, out); add('hesitation', .04*w, out)
        if has_op(row, 'ABORT'):
            add('rejection', .08*w, out); add('restraint', .05*w, out); add('mismatch', .04*w, out)
        if has_op(row, 'CORRECT'):
            add('repair', .07*w, out); add('correction', .07*w, out); add('alignment', .03*w, out)
        if has_op(row, 'MERGE'):
            add('connection', .07*w, out); add('similarity', .04*w, out); add('coherence', .03*w, out)
        if has_op(row, 'SPLIT'):
            add('separation', .07*w, out); add('boundary', .04*w, out); add('difference', .04*w, out)
        if gate > .9:
            add('intensity', .04*w*gate, out); add('salience', .03*w*gate, out); add('urgency', .03*w*gate, out)
        if rel > .7:
            add('readiness', .04*w*rel, out); add('completion', .02*w*rel, out)
    # window-level modifiers
    if repeated_input:
        add('familiarity', .22, out); add('recognition', .20, out); add('memory', .12, out)
    if near_release_no_witness > 0.25:
        add('hesitation', .18, out); add('restraint', .14, out); add('release_pressure', .10, out)
    # final tick modifiers
    final = rows[-1]
    if has_op(final, 'SELECT') and has_op(final, 'RELEASE'):
        add('recognition', .18, out); add('readiness', .12, out)
    if has_op(final, 'HOLD') and has_op(final, 'RELEASE'):
        add('restraint', .12, out); add('confirmation', .08, out)
    if has_op(final, 'ADVANCE'):
        add('readiness', .15, out); add('transition', .10, out)
    if str(final.get('witness','')).lower() in ('1','true','yes') or final.get('witness_id') or final.get('witness'):
        add('confirmation', .18, out); add('completion', .12, out); add('confidence', .10, out)
    return {k: round(clamp01(v), 6) for k,v in out.items() if v > 0}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv_path')
    ap.add_argument('--tau', type=float, default=10.0)
    args = ap.parse_args()
    rows = load_rows_csv(args.csv_path)
    print(json.dumps(project_rows(rows, tau=args.tau), indent=2))

if __name__ == '__main__': main()
