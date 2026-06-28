#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

OP_NAMES = [
    "SELECT", "HOLD", "RELEASE", "INHIBIT", "ADVANCE", "RETREAT", "SPLIT", "MERGE",
    "AMPLIFY", "DAMP", "COMPARE", "CORRECT", "COMMIT", "ABORT",
]
AP_NAMES = [
    "AP_RELAX", "AP_WHOLE", "AP_SPAN", "AP_PAIR", "AP_POSITION", "AP_CHAR", "AP_PUNCT", "AP_SHAPE",
    "AP_WIDEN", "AP_NARROW", "AP_CLOSE", "AP_OPEN",
]


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None: return default
        if isinstance(x, str) and not x.strip(): return default
        return float(x)
    except Exception:
        return default


def parse_jsonish(x: Any, default: Any) -> Any:
    if x is None: return default
    if isinstance(x, (list, dict)): return x
    s = str(x)
    if not s or s.lower() == 'nan': return default
    try:
        return json.loads(s)
    except Exception:
        return default


def has_token(text: str, token: str) -> bool:
    return token.upper() in str(text or '').upper().replace(',', ' ').split() or token.upper() in str(text or '').upper()


class UtteranceIndex2048:
    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.bank = [json.loads(line) for line in (self.index_dir/'utterance_bank_2048.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        z = np.load(self.index_dir/'utterance_index_2048.npz', allow_pickle=True)
        self.matrix = z['vectors'].astype(np.float32)
        self.axes = [str(x) for x in z['axes']]
        self.axis_to_i = {a:i for i,a in enumerate(self.axes)}

    def empty_vec(self) -> np.ndarray:
        return np.zeros((len(self.axes),), dtype=np.float32)

    def axis_dict(self, v: np.ndarray, minv: float = 0.025, limit: int = 16) -> Dict[str, float]:
        pairs = [(self.axes[i], float(v[i])) for i in np.argsort(-v) if float(v[i]) >= minv]
        return {k: round(val, 6) for k,val in pairs[:limit]}

    def query_vec(self, v: np.ndarray, k: int = 8) -> Tuple[List[Dict[str, Any]], Optional[float]]:
        q = v.astype(np.float32).copy()
        norm = float(np.linalg.norm(q))
        if norm <= 1e-12:
            q[:] = 0.0
        else:
            q /= norm
        scores = self.matrix @ q
        order = np.argsort(-scores)[:max(1, int(k))]
        out = []
        for rank, idx in enumerate(order, 1):
            e = self.bank[int(idx)]
            cosine = float(scores[int(idx)])
            out.append({
                'rank': rank,
                'id': e.get('id'),
                'phrase': e.get('utterance'),
                'utterance': e.get('utterance'),
                'family': e.get('family'),
                'leaf': e.get('leaf'),
                'form': e.get('form'),
                'strength': e.get('strength'),
                'cosine': round(cosine, 6),
                'distance': round(1.0 - cosine, 6),
            })
        margin = None if len(out) < 2 else round(float(out[0]['cosine'] - out[1]['cosine']), 6)
        return out, margin


class TracePostureProjector:
    """Tick trace -> posture64 delta.

    Modes:
      selector_only: ordinary motor/control trace only.
      aperture_only: UTE-facing receptor/occlusion posture only.
      fused: both surfaces, with no semantic phase-label injection.
    """
    def __init__(self, index: UtteranceIndex2048):
        self.index = index
        self.axes = index.axes
        self.a2i = index.axis_to_i

    def add(self, v: np.ndarray, axis: str, amount: float) -> None:
        i = self.a2i.get(axis)
        if i is not None:
            v[i] += float(amount)

    def norm(self, x: Any, scale: float = 20.0) -> float:
        val = safe_float(x)
        if val <= 0: return 0.0
        return float(1.0 - math.exp(-val / max(1e-6, scale)))

    def _active_ops(self, row: Dict[str, Any]) -> List[str]:
        text = ' '.join(str(row.get(k,'')) for k in ['active_ops','commands','top_ops'])
        top_ops = parse_jsonish(row.get('top_ops'), [])
        if isinstance(top_ops, list):
            for item in top_ops:
                if isinstance(item, (list, tuple)) and item: text += ' ' + str(item[0])
                elif isinstance(item, dict): text += ' ' + str(item.get('op',''))
        return [op for op in OP_NAMES if has_token(text, op)]

    def _active_aperture(self, row: Dict[str, Any]) -> List[str]:
        text = ' '.join(str(row.get(k,'')) for k in ['active_aperture','aperture_commands'])
        return [ap for ap in AP_NAMES if has_token(text, ap)]

    def selector_delta(self, row: Dict[str, Any]) -> np.ndarray:
        v = self.index.empty_vec()
        ops = self._active_ops(row)
        gate = safe_float(row.get('gate_pressure'))
        rel = safe_float(row.get('release_score'))
        witness = bool(str(row.get('witnesses','')).strip() and str(row.get('witnesses','')).lower() != 'nan') or bool(row.get('witness_id'))
        for op in ops:
            if op == 'SELECT':
                self.add(v,'attention',0.060); self.add(v,'orientation',0.050); self.add(v,'recognition',0.025)
            elif op == 'HOLD':
                self.add(v,'persistence',0.070); self.add(v,'restraint',0.060); self.add(v,'stability',0.035)
            elif op == 'RELEASE':
                self.add(v,'release_pressure',0.085); self.add(v,'transition',0.050); self.add(v,'readiness',0.040)
            elif op == 'INHIBIT':
                self.add(v,'restraint',0.090); self.add(v,'avoidance',0.030); self.add(v,'containment',0.045)
            elif op == 'ADVANCE':
                self.add(v,'readiness',0.070); self.add(v,'transition',0.060); self.add(v,'approach',0.030)
            elif op == 'RETREAT':
                self.add(v,'withdrawal',0.090); self.add(v,'hesitation',0.050); self.add(v,'avoidance',0.050)
            elif op == 'SPLIT':
                self.add(v,'separation',0.075); self.add(v,'boundary',0.050); self.add(v,'difference',0.035)
            elif op == 'MERGE':
                self.add(v,'connection',0.075); self.add(v,'coherence',0.040); self.add(v,'similarity',0.035)
            elif op == 'AMPLIFY':
                self.add(v,'intensity',0.070); self.add(v,'salience',0.050); self.add(v,'urgency',0.030)
            elif op == 'DAMP':
                self.add(v,'calm',0.055); self.add(v,'restraint',0.050); self.add(v,'containment',0.035)
            elif op == 'COMPARE':
                self.add(v,'comparison',0.090); self.add(v,'difference',0.045); self.add(v,'search',0.035)
            elif op == 'CORRECT':
                self.add(v,'correction',0.085); self.add(v,'repair',0.080); self.add(v,'alignment',0.045)
            elif op == 'COMMIT':
                self.add(v,'commitment',0.085); self.add(v,'completion',0.055); self.add(v,'confidence',0.045)
            elif op == 'ABORT':
                self.add(v,'rejection',0.080); self.add(v,'avoidance',0.060); self.add(v,'restraint',0.050)
        if gate > 0:
            g = min(0.13, 0.045 * gate)
            self.add(v,'salience',g); self.add(v,'intensity',g*0.9)
            if gate >= 0.75:
                self.add(v,'readiness',0.055); self.add(v,'urgency',0.035)
        if rel > 0:
            self.add(v,'release_pressure',min(0.12, 0.06 * max(0.0, rel)))
            if rel >= 0.55: self.add(v,'readiness',0.040)
        # lane trace JSON provides continuous intent not visible in active op strings.
        traces = parse_jsonish(row.get('top_trace'), [])
        if isinstance(traces, list):
            for tr in traces[:4]:
                if not isinstance(tr, dict): continue
                hold=safe_float(tr.get('hold')); release=safe_float(tr.get('release')); inhibit=safe_float(tr.get('inhibit')); correct=safe_float(tr.get('correct')); energy=safe_float(tr.get('energy'))
                scale=0.030
                self.add(v,'persistence', min(0.05, scale*hold))
                self.add(v,'release_pressure', min(0.05, scale*release))
                self.add(v,'restraint', min(0.05, scale*inhibit))
                self.add(v,'correction', min(0.05, scale*correct))
                if energy > 20: self.add(v,'attention',0.018)
        if witness:
            self.add(v,'completion',0.12); self.add(v,'confirmation',0.10); self.add(v,'commitment',0.08)
        return np.clip(v, 0, 1)

    def aperture_delta(self, row: Dict[str, Any]) -> np.ndarray:
        v = self.index.empty_vec()
        aps = self._active_aperture(row)
        level = str(row.get('aperture_level_name','')).lower()
        commands = str(row.get('aperture_commands',''))
        occlusion = safe_float(row.get('occlusion_level'))
        width = safe_float(row.get('aperture_width'), 3.0)
        # current aperture level is a receptor posture, not semantic meaning.
        if level in ('char','punct','position'):
            self.add(v,'attention',0.065); self.add(v,'salience',0.035); self.add(v,'boundary',0.030)
        if level == 'punct':
            self.add(v,'closure_gap',0.070); self.add(v,'boundary',0.060); self.add(v,'incompletion',0.030)
        elif level == 'char':
            self.add(v,'attention',0.070); self.add(v,'search',0.035); self.add(v,'orientation',0.030)
        elif level == 'position':
            self.add(v,'ordering',0.055); self.add(v,'comparison',0.035); self.add(v,'orientation',0.035)
        elif level == 'pair':
            self.add(v,'comparison',0.060); self.add(v,'connection',0.055); self.add(v,'ordering',0.030)
        elif level == 'span':
            self.add(v,'coherence',0.040); self.add(v,'recognition',0.035); self.add(v,'familiarity',0.025)
        elif level == 'whole':
            self.add(v,'coherence',0.050); self.add(v,'stability',0.030); self.add(v,'orientation',0.025)
        elif level == 'relaxed':
            self.add(v,'calm',0.040); self.add(v,'stability',0.025)
        for ap in aps:
            if ap == 'AP_CLOSE':
                self.add(v,'restraint',0.080); self.add(v,'withdrawal',0.065); self.add(v,'containment',0.055)
            elif ap == 'AP_OPEN':
                self.add(v,'approach',0.065); self.add(v,'release_pressure',0.030); self.add(v,'engagement',0.045)
            elif ap == 'AP_RELAX':
                self.add(v,'calm',0.060); self.add(v,'stability',0.040); self.add(v,'relief',0.025)
            elif ap == 'AP_WIDEN':
                self.add(v,'attention',0.045); self.add(v,'connection',0.035); self.add(v,'approach',0.025)
            elif ap == 'AP_NARROW':
                self.add(v,'attention',0.055); self.add(v,'containment',0.040); self.add(v,'salience',0.035)
            elif ap == 'AP_CHAR':
                self.add(v,'attention',0.050); self.add(v,'search',0.030)
            elif ap == 'AP_PUNCT':
                self.add(v,'boundary',0.055); self.add(v,'closure_gap',0.050); self.add(v,'completion',0.020)
            elif ap == 'AP_POSITION':
                self.add(v,'ordering',0.050); self.add(v,'orientation',0.035)
            elif ap == 'AP_PAIR':
                self.add(v,'comparison',0.040); self.add(v,'connection',0.040)
            elif ap == 'AP_SPAN':
                self.add(v,'recognition',0.035); self.add(v,'coherence',0.035)
            elif ap == 'AP_WHOLE':
                self.add(v,'orientation',0.035); self.add(v,'coherence',0.035)
            elif ap == 'AP_SHAPE':
                self.add(v,'similarity',0.035); self.add(v,'recognition',0.030)
        if 'AP_CLOSE_CONFIRMED' in commands:
            self.add(v,'containment',0.090); self.add(v,'restraint',0.075); self.add(v,'avoidance',0.040)
        if 'AP_REOPEN_STEP' in commands or 'AP_OPEN_OR_RELAX' in commands:
            self.add(v,'transition',0.050); self.add(v,'relief',0.035); self.add(v,'approach',0.025)
        if occlusion > 0:
            self.add(v,'withdrawal',0.04*occlusion); self.add(v,'containment',0.05*occlusion); self.add(v,'calm',0.025*occlusion)
        if width <= 2:
            self.add(v,'attention',0.025); self.add(v,'salience',0.020)
        elif width >= 4:
            self.add(v,'connection',0.025); self.add(v,'orientation',0.020)
        return np.clip(v, 0, 1)

    def tick_delta(self, row: Dict[str, Any], mode: str) -> np.ndarray:
        mode = mode.lower()
        if mode == 'selector_only':
            return self.selector_delta(row)
        if mode == 'aperture_only':
            return self.aperture_delta(row)
        if mode == 'fused':
            return np.clip(0.58*self.selector_delta(row) + 0.42*self.aperture_delta(row), 0, 1)
        raise ValueError(f'unknown translation mode: {mode}')


@dataclass
class AccumulatedIntentWord:
    index: UtteranceIndex2048
    projector: TracePostureProjector
    mode: str
    retain: float = 0.94
    trigger_mix: float = 0.18
    top_k: int = 8
    acc: np.ndarray = field(init=False)
    start_tick: Optional[int] = None
    end_tick: Optional[int] = None
    rows: int = 0
    raw_refs: List[Dict[str, Any]] = field(default_factory=list)
    last_delta: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        self.acc = self.index.empty_vec()

    def reset(self, next_start_tick: Optional[int] = None) -> None:
        self.acc = self.index.empty_vec()
        self.start_tick = next_start_tick
        self.end_tick = None
        self.rows = 0
        self.raw_refs = []
        self.last_delta = None

    def update_tick(self, row: Dict[str, Any], raw_ref: Optional[Dict[str, Any]] = None) -> None:
        tick = int(float(row.get('tick', self.rows)))
        if self.start_tick is None: self.start_tick = tick
        delta = self.projector.tick_delta(row, self.mode)
        self.acc = self.retain * self.acc + delta
        self.acc = np.clip(self.acc, 0, 4.0)
        self.last_delta = delta
        self.end_tick = tick
        self.rows += 1
        if raw_ref is None:
            raw_ref = {'tick': tick}
        self.raw_refs.append(raw_ref)

    def sample(self, event: Dict[str, Any]) -> Dict[str, Any]:
        # Include final trigger stroke in the composite word when available.
        comp = self.acc.copy()
        if self.last_delta is not None:
            comp = (1.0 - self.trigger_mix) * comp + self.trigger_mix * self.last_delta
        maxv = float(np.max(comp))
        if maxv > 1e-9:
            comp = comp / maxv
        top, margin = self.index.query_vec(comp, k=self.top_k)
        top1 = top[0] if top else {}
        dominant_axes = self.index.axis_dict(comp, minv=0.03, limit=12)
        start = self.start_tick if self.start_tick is not None else event.get('tick')
        end = self.end_tick if self.end_tick is not None else event.get('tick')
        return {
            'tick': event.get('tick', end),
            'run_label': event.get('run_label',''),
            'phase_label': event.get('phase_label', event.get('phase','')),
            'source_window_start_tick': start,
            'source_window_end_tick': end,
            'translation_mode': self.mode,
            'top1_phrase': top1.get('phrase'),
            'top1_family': top1.get('family'),
            'top1_leaf': top1.get('leaf'),
            'topk_candidate_phrases': json.dumps([x.get('phrase') for x in top], ensure_ascii=False),
            'topk_families': json.dumps([x.get('family') for x in top], ensure_ascii=False),
            'topk_leaves': json.dumps([x.get('leaf') for x in top], ensure_ascii=False),
            'cosine_scores': json.dumps([x.get('cosine') for x in top]),
            'distances': json.dumps([x.get('distance') for x in top]),
            'rank_margin': margin,
            'dominant_vector_axes': json.dumps(dominant_axes, ensure_ascii=False),
            'witness_event_id': event.get('witness_event_id', event.get('witness','')),
            'event_kind': event.get('event_kind','witness'),
            'raw_trace_window_reference': json.dumps({
                'run_dir': event.get('run_dir',''),
                'tick_rows': event.get('tick_rows_path',''),
                'trace_log': event.get('trace_log_path',''),
                'rows': self.rows,
                'first_ref': self.raw_refs[0] if self.raw_refs else None,
                'last_ref': self.raw_refs[-1] if self.raw_refs else None,
            }, ensure_ascii=False),
            'top_k_detail_json': json.dumps(top, ensure_ascii=False),
        }


class IntentionTraceTranslatorSet:
    def __init__(self, index_dir: Path, modes: Iterable[str] = ('aperture_only','selector_only','fused'), retain: float = 0.94, trigger_mix: float = 0.18, top_k: int = 8):
        self.index = UtteranceIndex2048(Path(index_dir))
        self.projector = TracePostureProjector(self.index)
        self.words = {m: AccumulatedIntentWord(self.index, self.projector, m, retain=retain, trigger_mix=trigger_mix, top_k=top_k) for m in modes}

    def update_tick(self, row: Dict[str, Any], raw_ref: Optional[Dict[str, Any]] = None) -> None:
        for w in self.words.values():
            w.update_tick(row, raw_ref=raw_ref)

    def sample_and_reset(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        out=[]
        next_start = int(float(event.get('tick', 0))) + 1
        for w in self.words.values():
            out.append(w.sample(event))
            w.reset(next_start_tick=next_start)
        return out


def load_tick_rows(path: Path) -> List[Dict[str, Any]]:
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text('', encoding='utf-8'); return
    keys=[]
    seen=set()
    for r in rows:
        for k in r.keys():
            if k not in seen: seen.add(k); keys.append(k)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)


def append_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n')
