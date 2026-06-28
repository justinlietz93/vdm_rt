#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
BANK = HERE / 'utterance_bank_2048.jsonl'
INDEX = HERE / 'utterance_index_2048.npz'

def load_bank(path=BANK):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def load_index(path=INDEX):
    z = np.load(path, allow_pickle=True)
    return z['vectors'].astype(np.float32), [str(x) for x in z['axes']]

def vector_from_axis_json(axis_json, axes):
    if isinstance(axis_json, str):
        axis_json = json.loads(axis_json)
    vec = np.zeros((len(axes),), dtype=np.float32)
    for k, v in axis_json.items():
        if k not in axes:
            raise SystemExit(f'Unknown axis: {k}')
        vec[axes.index(k)] = float(v)
    n = np.linalg.norm(vec)
    return vec if n == 0 else vec / n

def query(axis_json, k=8):
    bank = load_bank()
    mat, axes = load_index()
    q = vector_from_axis_json(axis_json, axes)
    scores = mat @ q
    order = np.argsort(-scores)[:k]
    out = []
    for rank, i in enumerate(order, 1):
        cosine = float(scores[i])
        e = bank[int(i)]
        out.append({
            'rank': rank,
            'id': e['id'],
            'utterance': e['utterance'],
            'family': e['family'],
            'leaf': e['leaf'],
            'form': e['form'],
            'strength': e['strength'],
            'cosine': round(cosine, 6),
            'distance': round(1.0 - cosine, 6),
        })
    if len(out) >= 2:
        margin = out[0]['cosine'] - out[1]['cosine']
    else:
        margin = None
    return {'top_utterance': out[0]['utterance'] if out else None, 'rank_margin': margin, 'top_k': out}

EXAMPLES = {
    'recognition': {'recognition': .95, 'familiarity': .70, 'confirmation': .65, 'confidence': .75, 'certainty': .65, 'coherence': .45, 'completion': .30},
    'uncertain_recognition': {'recognition': .75, 'familiarity': .55, 'uncertainty': .70, 'hesitation': .45, 'doubt': .35, 'search': .20},
    'missing': {'incompletion': .90, 'closure_gap': .85, 'need': .65, 'search': .45, 'uncertainty': .35},
    'mismatch': {'mismatch': .95, 'difference': .65, 'friction': .45, 'rejection': .35, 'confidence': .35},
    'curiosity': {'curiosity': .95, 'interest': .75, 'approach': .55, 'search': .50, 'attention': .45, 'novelty': .35},
}

def main():
    ap = argparse.ArgumentParser(description='Query the 2048 first-person reafferent utterance index.')
    ap.add_argument('--axis-json', help='JSON object mapping posture axes to scores')
    ap.add_argument('--axis-file', help='Path to JSON file mapping posture axes to scores')
    ap.add_argument('--example', choices=sorted(EXAMPLES), help='Run a built-in example query')
    ap.add_argument('-k', type=int, default=8)
    args = ap.parse_args()
    if args.example:
        axis_json = EXAMPLES[args.example]
    elif args.axis_file:
        axis_json = json.loads(Path(args.axis_file).read_text(encoding='utf-8'))
    elif args.axis_json:
        axis_json = json.loads(args.axis_json)
    else:
        ap.error('Provide --axis-json, --axis-file, or --example')
    print(json.dumps(query(axis_json, k=args.k), indent=2))

if __name__ == '__main__':
    main()
