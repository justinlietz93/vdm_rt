#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

TOOL_DIR = Path(__file__).resolve().parent
PKG_ROOT = TOOL_DIR.parent
SRC_DIR = PKG_ROOT / "src"
for _p in (TOOL_DIR, SRC_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import base_sensory_occlusion_runner as base
from intention_trace_translator import IntentionTraceTranslatorSet, write_csv
from deterministic_vdm_bot import DeterministicConversationBot

RUN_NAMES = [
    "pal_live",
    "pal_static",
    "pal_yoked",
]
DEFAULT_STABLE_ATOM = "The bridge holds while the signal crosses."
STABLE_CYCLE = [
    "The bridge holds while the signal crosses.",
    "The signal waits until the bridge is steady.",
    "The path remains open while the marker moves.",
    "The boundary holds before the transfer begins.",
    "The marker returns after the path remains steady.",
]

FIELDS = [
    "tick","run_label","phase","condition","emit_policy","atom","external_atom",
    "reafferent_payload","reafferent_kind","stim_count","stim_hash","occlusion_level",
    "aperture_level","aperture_level_name","aperture_width","active_aperture",
    "aperture_commands","obs_count","obs_nodes_unique","active_ops","active_lanes",
    "witnesses","release_lane","release_score","gate_pressure","top_ops","top_lanes",
    "top_trace","tick_s",
]
FEATURE_FIELDS=[
    "tick","run_label","phase","condition","whole","norm","span","position","shape",
    "pair","char","punct","dark","stim_total","external_stim_count",
    "reafferent_stim_count","gains",
]
RAW_EVENT_JSONL = "event_translation_raw.jsonl"
TOPK_JSONL = "topk_true_vs_emitted.jsonl"
HARNESS_STATE = "harness_state.json"


def append_jsonl(path: Path, rec: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        if isinstance(rec, list):
            for r in rec:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True)+"\n")
        else:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True)+"\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows=[]
    with open(path, encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def sha_list(xs: Iterable[int]) -> str:
    h=hashlib.sha256()
    for x in xs:
        h.update(str(int(x)).encode())
        h.update(b",")
    return h.hexdigest()[:16]


def safe_float(x: Any, default: float=0.0) -> float:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def mean(xs: List[float]) -> float:
    vals=[float(x) for x in xs if x is not None]
    return float(sum(vals)/len(vals)) if vals else 0.0


def mode_val(rows: List[Dict[str,Any]], key: str) -> str:
    vals=[str(r.get(key,"")) for r in rows if str(r.get(key,""))]
    if not vals:
        return ""
    return Counter(vals).most_common(1)[0][0]


def parse_jsonish(x: Any, default: Any) -> Any:
    if isinstance(x, (dict, list)):
        return x
    try:
        if x is None or str(x).strip()=="":
            return default
        return json.loads(str(x))
    except Exception:
        return default


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    an=float(np.linalg.norm(a)); bn=float(np.linalg.norm(b))
    if an <= 1e-12 or bn <= 1e-12:
        return 0.0
    return float(np.dot(a,b)/(an*bn))


def normalize(v: np.ndarray) -> np.ndarray:
    out=v.astype(np.float32).copy()
    n=float(np.linalg.norm(out))
    if n > 1e-12:
        out /= n
    return out


def stable_atom(tick: int, mode: str) -> str:
    if mode == "cycle":
        return STABLE_CYCLE[tick % len(STABLE_CYCLE)]
    return DEFAULT_STABLE_ATOM

def one_line(x: Any, limit: int = 160) -> str:
    s = "" if x is None else str(x)
    s = " ".join(s.replace("\n", " ").replace("\r", " ").split())
    if len(s) > limit:
        return s[: max(0, limit - 3)] + "..."
    return s


def fmt_score(x: Any) -> str:
    try:
        if x is None or x == "":
            return ""
        return f"{float(x):.4f}"
    except Exception:
        return str(x)


def fmt_top(items: List[Dict[str, Any]], n: int = 3) -> str:
    out = []
    for item in (items or [])[: max(0, n)]:
        phrase = one_line(item.get("phrase") or item.get("utterance"), 64)
        fam = item.get("family", "")
        leaf = item.get("leaf", "")
        score = fmt_score(item.get("cosine"))
        out.append(f"{phrase} [{fam}/{leaf}] {score}")
    return " | ".join(out)


def live_enabled(cfg: Dict[str, Any]) -> bool:
    return bool(cfg.get("live_terminal", True))


def live_tick_line(cfg: Dict[str, Any], *, tick: int, run_name: str, phase: str, condition: str, policy: str,
                   external_atom: str, re_text: str, sel: Dict[str, Any], ap_update: Dict[str, Any],
                   ap_state_before: Dict[str, Any]) -> None:
    if not live_enabled(cfg):
        return
    stride = max(1, int(cfg.get("tick_print_stride", 1)))
    witness_now = bool(sel.get("emitted"))
    re_now = bool(re_text)
    if (tick % stride) != 0 and not witness_now and not re_now:
        return
    active_ops = " ".join(sel.get("active_ops", []) or [])
    active_lanes = " ".join(sel.get("active_lanes", []) or [])
    commands = " ".join(ap_update.get("aperture_commands", []) or [])
    witnesses = " ".join(str(e.get("witness", "")) for e in (sel.get("emitted", []) or []))
    print(
        f"[tick {tick:05d}] run={run_name} phase={phase} condition={condition} emit={policy} "
        f"input=\"{one_line(external_atom, 96)}\"",
        flush=True,
    )
    if re_now:
        print(f"  reafferent_in=\"{one_line(re_text, 140)}\"", flush=True)
    print(
        f"  selector ops={active_ops or '-'} lanes={active_lanes or '-'} "
        f"gate={fmt_score(sel.get('gate_pressure'))} release={fmt_score(sel.get('release_score'))} "
        f"witnesses={witnesses or '-'}",
        flush=True,
    )
    print(
        f"  aperture level={ap_state_before.get('level_name')} occlusion={fmt_score(ap_state_before.get('occlusion_level'))} "
        f"active={' '.join(ap_update.get('active_aperture', []) or []) or '-'} commands={commands or '-'}",
        flush=True,
    )


def live_witness_block(cfg: Dict[str, Any], *, tick: int, run_name: str, ev: Dict[str, Any], policy: str,
                       external_atom: str, re_text: str, samples: Dict[str, Dict[str, Any]],
                       choice: Dict[str, Any], payload: str, kind: str) -> None:
    if not live_enabled(cfg):
        return
    topn = max(0, int(cfg.get("live_topn", 3)))
    true_fused = samples.get("fused", {})
    aperture = samples.get("aperture_only", {})
    selector = samples.get("selector_only", {})
    emitted = choice.get("emitted") or {}
    print(f"  >>> WITNESS tick={tick} run={run_name} id={ev.get('witness', '')} kind={kind}", flush=True)
    print(f"      input_seen=\"{one_line(external_atom if not re_text else external_atom + ' || ' + re_text, 180)}\"", flush=True)
    print(
        f"      true_fused={one_line((true_fused.get('record') or {}).get('top1_phrase'), 96)} "
        f"family={(true_fused.get('record') or {}).get('top1_family')} "
        f"leaf={(true_fused.get('record') or {}).get('top1_leaf')} "
        f"margin={fmt_score(true_fused.get('margin'))}",
        flush=True,
    )
    print(
        f"      aperture_trace={one_line((aperture.get('record') or {}).get('top1_phrase'), 96)} "
        f"selector_trace={one_line((selector.get('record') or {}).get('top1_phrase'), 96)}",
        flush=True,
    )
    print(
        f"      emitted_out={one_line(payload, 120)} family={emitted.get('family') if policy != 'baseline' else 'witness_code'} "
        f"leaf={emitted.get('leaf') if policy != 'baseline' else 'witness_code'} mode={choice.get('emitted_selection_mode')} "
        f"sim_true={fmt_score(choice.get('emitted_similarity_to_true_vector'))} "
        f"signed_sim_true={fmt_score(choice.get('signed_centered_similarity_to_true'))} "
        f"anti_score={fmt_score(choice.get('signed_centered_score_against_anti_query'))}",
        flush=True,
    )
    if topn > 0:
        print(f"      true_top{topn}: {fmt_top(true_fused.get('top', []), topn)}", flush=True)
    emitted_top = choice.get("emitted_topk") or []
    if emitted_top and topn > 0:
        print(f"      emitted_top{topn}: {fmt_top(emitted_top, topn)}", flush=True)


def plan_for(run_name: str, tick: int, switch_tick: int) -> Tuple[str, str, str]:
    if run_name == "no_return_control":
        return "no_return_full", "no_return", "no_return"
    if run_name == "true_phrase_return":
        return "true_phrase_return_full", "aligned_fused", "fused"
    if run_name == "pal_live":
        return "pal_live_full", "pal_live", "pal_live"
    if run_name == "pal_static":
        return "pal_static_full", "pal_static", "pal_static"
    if run_name == "pal_yoked":
        return "pal_yoked_full", "pal_yoked", "pal_yoked"
    raise ValueError(f"unknown run name: {run_name}")

def op_indices_from_rows(rows: List[Dict[str,Any]]) -> Dict[str,float]:
    interaction=revision=withdrawal=0.0
    for r in rows:
        active=set(str(r.get("active_ops","")).split())
        interaction += (1.0 if "COMMIT" in active else 0.0) + (1.0 if "RELEASE" in active else 0.0)
        revision += (1.0 if "COMPARE" in active else 0.0) + (1.0 if "CORRECT" in active else 0.0) + (1.0 if "RETREAT" in active else 0.0)
        withdrawal += (1.0 if "ABORT" in active else 0.0) + (1.0 if "INHIBIT" in active else 0.0)
    n=max(1,len(rows))
    interaction/=n; revision/=n; withdrawal/=n
    return {
        "interaction": round(interaction,6),
        "revision": round(revision,6),
        "withdrawal": round(withdrawal,6),
        "engaged_score": round(interaction+revision-withdrawal,6),
        "guardedness": round(withdrawal-revision,6),
    }


def sample_word_with_vector(word, event: Dict[str,Any], top_k:int=8) -> Dict[str,Any]:
    comp = word.acc.copy()
    if word.last_delta is not None:
        comp = (1.0 - word.trigger_mix) * comp + word.trigger_mix * word.last_delta
    maxv = float(np.max(np.abs(comp)))
    if maxv > 1e-9:
        comp = comp / maxv
    top, margin = word.index.query_vec(comp, k=top_k)
    top1 = top[0] if top else {}
    dominant_axes = word.index.axis_dict(np.maximum(comp,0), minv=0.03, limit=12)
    start = word.start_tick if word.start_tick is not None else event.get("tick")
    end = word.end_tick if word.end_tick is not None else event.get("tick")
    rec = {
        "tick": event.get("tick", end),
        "run_label": event.get("run_label", ""),
        "phase_label": event.get("phase_label", event.get("phase", "")),
        "condition": event.get("condition", ""),
        "source_window_start_tick": start,
        "source_window_end_tick": end,
        "translation_mode": word.mode,
        "top1_phrase": top1.get("phrase"),
        "top1_family": top1.get("family"),
        "top1_leaf": top1.get("leaf"),
        "topk_candidate_phrases": json.dumps([x.get("phrase") for x in top], ensure_ascii=False),
        "topk_families": json.dumps([x.get("family") for x in top], ensure_ascii=False),
        "topk_leaves": json.dumps([x.get("leaf") for x in top], ensure_ascii=False),
        "cosine_scores": json.dumps([x.get("cosine") for x in top]),
        "distances": json.dumps([x.get("distance") for x in top]),
        "rank_margin": margin,
        "dominant_vector_axes": json.dumps(dominant_axes, ensure_ascii=False),
        "witness_event_id": event.get("witness_event_id", event.get("witness", "")),
        "event_kind": event.get("event_kind", "witness"),
        "raw_trace_window_reference": json.dumps({
            "run_dir": event.get("run_dir", ""),
            "tick_rows": event.get("tick_rows_path", ""),
            "trace_log": event.get("trace_log_path", ""),
            "rows": word.rows,
        }, ensure_ascii=False),
        "top_k_detail_json": json.dumps(top, ensure_ascii=False),
    }
    return {"record": rec, "vector": comp.astype(np.float32), "top": top, "margin": margin}


class EmissionSelector:
    def __init__(self, translator: IntentionTraceTranslatorSet, top_k:int=8, seed:int=0):
        self.translator = translator
        self.index = translator.index
        self.top_k = top_k
        self.rng = random.Random(seed)
        self.id_to_i = {str(e.get("id")): i for i,e in enumerate(self.index.bank)}
        self.phrase_to_i = {str(e.get("utterance")): i for i,e in enumerate(self.index.bank)}
        self.prior_real = deque(maxlen=256)
        self.center = self.index.matrix.mean(axis=0).astype(np.float32)
        signed = self.index.matrix.astype(np.float32) - self.center[None, :]
        norms = np.linalg.norm(signed, axis=1, keepdims=True)
        self.signed_matrix = signed / np.maximum(norms, 1e-12)

    def phrase_index(self, item: Dict[str,Any]) -> Optional[int]:
        idx = self.id_to_i.get(str(item.get("id")))
        if idx is None:
            idx = self.phrase_to_i.get(str(item.get("phrase") or item.get("utterance")))
        return None if idx is None else int(idx)

    def phrase_vector(self, item: Dict[str,Any]) -> np.ndarray:
        idx = self.phrase_index(item)
        if idx is None:
            return self.index.empty_vec()
        return self.index.matrix[idx].astype(np.float32)

    def signed_phrase_vector(self, item: Dict[str,Any]) -> np.ndarray:
        idx = self.phrase_index(item)
        if idx is None:
            return self.index.empty_vec()
        return self.signed_matrix[idx].astype(np.float32)

    def bank_item(self, idx: int, rank: int, score: float, score_name: str="cosine") -> Dict[str,Any]:
        e=self.index.bank[int(idx)]
        row={
            "rank": rank,
            "id": e.get("id"),
            "phrase": e.get("utterance"),
            "utterance": e.get("utterance"),
            "family": e.get("family"),
            "leaf": e.get("leaf"),
            "form": e.get("form"),
            "strength": e.get("strength"),
            score_name: round(float(score),6),
        }
        if score_name != "cosine":
            row["cosine"] = round(float(score),6)
        row["distance"] = round(1.0-float(score),6)
        return row

    def choose(self, policy: str, samples: Dict[str,Dict[str,Any]], tick: int) -> Dict[str,Any]:
        true = samples["fused"]
        true_vec = true["vector"].astype(np.float32)
        true_top1 = true["top"][0] if true["top"] else {}
        policy = str(policy)
        emitted_top=[]
        anti_query_score=None
        signed_score_against_anti_query=None
        signed_similarity_to_true=None
        anti_selection_basis=""
        if policy == "baseline":
            emitted = {"phrase": None, "family": "witness_code", "leaf": "witness_code", "id": ""}
        elif policy in ("aperture_only", "selector_only", "fused"):
            emitted = samples[policy]["top"][0] if samples[policy]["top"] else {}
            emitted_top = samples[policy]["top"]
        elif policy == "anti_vector":
            true_signed = normalize(true_vec - self.center)
            anti_query = -true_signed
            scores = self.signed_matrix @ anti_query
            order = np.argsort(-scores)[:self.top_k]
            emitted_top=[]
            for rank, idx in enumerate(order,1):
                item=self.bank_item(int(idx), rank, float(scores[int(idx)]), score_name="signed_centered_score_against_anti_query")
                item["signed_centered_similarity_to_true"] = round(float(self.signed_matrix[int(idx)] @ true_signed), 6)
                item["original_nonnegative_similarity_to_true"] = round(cosine(true_vec, self.index.matrix[int(idx)]), 6)
                emitted_top.append(item)
            emitted = emitted_top[0] if emitted_top else {}
            anti_query_score = emitted.get("signed_centered_score_against_anti_query")
            signed_score_against_anti_query = anti_query_score
            signed_similarity_to_true = emitted.get("signed_centered_similarity_to_true")
            anti_selection_basis = "signed_centered_bank_mean: nearest phrase to -(true_vec-center)"
        elif policy == "orthogonal":
            true_signed = normalize(true_vec - self.center)
            sims = self.signed_matrix @ true_signed
            order = np.argsort(np.abs(sims))[:self.top_k]
            emitted_top=[]
            for rank, idx in enumerate(order,1):
                item=self.bank_item(int(idx), rank, float(sims[int(idx)]), score_name="signed_centered_similarity_to_true")
                item["original_nonnegative_similarity_to_true"] = round(cosine(true_vec, self.index.matrix[int(idx)]), 6)
                emitted_top.append(item)
            emitted = emitted_top[0] if emitted_top else {}
            signed_similarity_to_true = emitted.get("signed_centered_similarity_to_true")
            anti_selection_basis = "signed_centered_near_90_degrees"
        elif policy == "random_matched":
            target_len = len(str(true_top1.get("phrase", "")).split())
            target_strength = true_top1.get("strength")
            candidates=[]
            for i,e in enumerate(self.index.bank):
                if e.get("strength") == target_strength and abs(len(str(e.get("utterance","")).split())-target_len) <= 2:
                    candidates.append((i,e))
            if not candidates:
                candidates=list(enumerate(self.index.bank))
            idx,e=self.rng.choice(candidates)
            sim=cosine(true_vec, self.index.matrix[int(idx)])
            emitted={"rank":1,"id":e.get("id"),"phrase":e.get("utterance"),"utterance":e.get("utterance"),"family":e.get("family"),"leaf":e.get("leaf"),"form":e.get("form"),"strength":e.get("strength"),"cosine":round(sim,6),"distance":round(1.0-sim,6)}
            emitted_top=[emitted]
            anti_selection_basis = "random length/strength matched control"
        elif policy == "shifted_real":
            emitted = self.prior_real[0] if len(self.prior_real) >= 50 else true_top1
            emitted_top=[emitted]
            anti_selection_basis = "lagged real previous true translation"
        else:
            raise ValueError(f"unknown emit policy: {policy}")
        ev = self.phrase_vector(emitted) if emitted else self.index.empty_vec()
        sim_true = cosine(true_vec, ev)
        if signed_similarity_to_true is None and emitted:
            signed_similarity_to_true = cosine(normalize(true_vec - self.center), self.signed_phrase_vector(emitted))
        if true_top1:
            self.prior_real.append(true_top1)
        return {
            "emitted": emitted,
            "emitted_topk": emitted_top,
            "emitted_selection_mode": policy,
            "emitted_score_against_anti_query": anti_query_score,
            "signed_centered_score_against_anti_query": signed_score_against_anti_query,
            "signed_centered_similarity_to_true": None if signed_similarity_to_true is None else round(float(signed_similarity_to_true), 6),
            "anti_selection_basis": anti_selection_basis,
            "emitted_similarity_to_true_vector": round(sim_true,6),
            "emitted_distance_from_true_vector": round(1.0 - sim_true,6),
        }

    def state_dict(self) -> Dict[str, Any]:
        return {"prior_real": list(self.prior_real)}

    def load_state_dict(self, state: Dict[str, Any]) -> None:
        self.prior_real.clear()
        for item in state.get("prior_real", [])[-256:]:
            self.prior_real.append(item)



def _make_bot_record(sample: Dict[str, Any], samples: Optional[Dict[str, Any]] = None, emitted_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rec = dict(sample.get("record") or {})
    top = list(sample.get("top") or [])
    top1 = top[0] if top else {}
    samples = samples or {}
    selector_top = ((samples.get("selector_only") or {}).get("top") or [{}])[0] if samples.get("selector_only") else {}
    aperture_top = ((samples.get("aperture_only") or {}).get("top") or [{}])[0] if samples.get("aperture_only") else {}
    fused_top = ((samples.get("fused") or {}).get("top") or [{}])[0] if samples.get("fused") else top1
    emitted_context = emitted_context or {}

    return {
        "tick": rec.get("tick"),
        "channel": rec.get("condition") or rec.get("emission_policy_at_event") or rec.get("run_label"),
        "true_top1_phrase": fused_top.get("phrase") or rec.get("top1_phrase"),
        "true_top1_family": fused_top.get("family") or rec.get("top1_family"),
        "true_top1_leaf": fused_top.get("leaf") or rec.get("top1_leaf"),
        "selector_phrase": selector_top.get("phrase"),
        "selector_family": selector_top.get("family"),
        "selector_leaf": selector_top.get("leaf"),
        "aperture_phrase": aperture_top.get("phrase"),
        "aperture_family": aperture_top.get("family"),
        "aperture_leaf": aperture_top.get("leaf"),
        "true_topk_phrases": [x.get("phrase") for x in top],
        "true_topk_families": [x.get("family") for x in top],
        "true_topk_leaves": [x.get("leaf") for x in top],
        "true_dominant_axes": rec.get("dominant_vector_axes"),
        "active_ops": rec.get("active_ops", ""),
        "top_ops": rec.get("top_ops", ""),
        "top_trace": rec.get("top_trace", ""),
        "active_lanes": rec.get("active_lanes", ""),
        "aperture_level": rec.get("aperture_level", ""),
        "aperture_commands": rec.get("aperture_commands", ""),
        "occlusion": rec.get("occlusion", ""),
        "emitted_phrase": emitted_context.get("phrase", ""),
        "emitted_family": emitted_context.get("family", ""),
        "emitted_leaf": emitted_context.get("leaf", ""),
    }


def _neutral_bot_packet(bot: DeterministicConversationBot, tick: int, reason: str) -> Dict[str, Any]:
    return bot.neutral_packet(tick=tick, reason=reason).to_dict()


def _packet_to_emitted_item(packet: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "phrase": packet.get("reply_text", ""),
        "utterance": packet.get("reply_text", ""),
        "family": packet.get("response_family") or packet.get("input_family", "unknown"),
        "leaf": packet.get("response_leaf") or packet.get("input_leaf", ""),
        "id": packet.get("response_id") or packet.get("rule_id", "bot"),
        "form": packet.get("selection_mode", "deterministic_bot_reply"),
        "strength": "bot",
    }


def _load_yoked_packets(run_dir: Path) -> List[Dict[str, Any]]:
    path = run_dir / "bot_packets.jsonl"
    return read_jsonl(path) if path.exists() else []

def reset_translator_words(translator: IntentionTraceTranslatorSet, tick: int) -> None:
    for w in translator.words.values():
        w.reset(next_start_tick=tick+1)


def translator_state(translator: IntentionTraceTranslatorSet) -> Dict[str, Any]:
    out={}
    for name,w in translator.words.items():
        out[name]={
            "acc": w.acc.astype(float).tolist(),
            "start_tick": w.start_tick,
            "end_tick": w.end_tick,
            "rows": w.rows,
            "raw_refs": w.raw_refs[-200:],
            "last_delta": None if w.last_delta is None else w.last_delta.astype(float).tolist(),
        }
    return out


def load_translator_state(translator: IntentionTraceTranslatorSet, state: Dict[str, Any]) -> None:
    for name,sd in state.items():
        if name not in translator.words:
            continue
        w=translator.words[name]
        w.acc=np.asarray(sd.get("acc", w.acc), dtype=np.float32)
        w.start_tick=sd.get("start_tick")
        w.end_tick=sd.get("end_tick")
        w.rows=int(sd.get("rows", 0))
        w.raw_refs=list(sd.get("raw_refs", []))
        ld=sd.get("last_delta")
        w.last_delta=None if ld is None else np.asarray(ld, dtype=np.float32)


def selector_state(selector) -> Dict[str, Any]:
    return {
        "op_energy": dict(selector.op_energy),
        "lane_energy": dict(selector.lane_energy),
        "lane_hold": dict(selector.lane_hold),
        "lane_inhibit": dict(selector.lane_inhibit),
        "lane_release": dict(selector.lane_release),
        "lane_correct": dict(selector.lane_correct),
        "last_emit": int(selector.last_emit),
        "witness_count": int(selector.witness_count),
    }


def load_selector_state(selector, state: Dict[str, Any]) -> None:
    for attr in ["op_energy","lane_energy","lane_hold","lane_inhibit","lane_release","lane_correct"]:
        d=getattr(selector, attr)
        for k,v in state.get(attr, {}).items():
            if k in d:
                d[k]=float(v)
    selector.last_emit=int(state.get("last_emit", selector.last_emit))
    selector.witness_count=int(state.get("witness_count", selector.witness_count))


def aperture_state(aperture) -> Dict[str, Any]:
    return {
        "ap_energy": dict(aperture.ap_energy),
        "level": int(aperture.level),
        "width": int(aperture.width),
        "occlusion_level": int(aperture.occlusion_level),
        "close_counter": int(aperture.close_counter),
        "last_commands": list(aperture.last_commands),
        "last_active": list(aperture.last_active),
    }


def load_aperture_state(aperture, state: Dict[str, Any]) -> None:
    for k,v in state.get("ap_energy", {}).items():
        if k in aperture.ap_energy:
            aperture.ap_energy[k]=float(v)
    aperture.level=int(state.get("level", aperture.level))
    aperture.width=int(state.get("width", aperture.width))
    aperture.occlusion_level=int(state.get("occlusion_level", aperture.occlusion_level))
    aperture.close_counter=int(state.get("close_counter", aperture.close_counter))
    aperture.last_commands=list(state.get("last_commands", aperture.last_commands))
    aperture.last_active=list(state.get("last_active", aperture.last_active))


def save_harness_state(path: Path, state: Dict[str, Any]) -> None:
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_harness_state(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def csv_writer(path: Path, fields: List[str], append: bool):
    path.parent.mkdir(parents=True, exist_ok=True)
    exists=path.exists() and path.stat().st_size > 0
    f=open(path, "a" if append else "w", newline="", encoding="utf-8")
    w=csv.DictWriter(f, fieldnames=fields)
    if not append or not exists:
        w.writeheader(); f.flush()
    return f,w


def ensure_suite_config(args) -> Dict[str, Any]:
    suite_dir=args.suite_dir.resolve()
    suite_dir.mkdir(parents=True, exist_ok=True)
    cfg_path=suite_dir/"suite_config.json"
    if cfg_path.exists() and not args.reset:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    if args.reset and suite_dir.exists():
        shutil.rmtree(suite_dir)
        suite_dir.mkdir(parents=True, exist_ok=True)
    cfg={
        "repo": str(args.repo.resolve()),
        "intent_index_dir": str(args.intent_index_dir.resolve()),
        "ticks_total": args.ticks_total,
        "switch_tick": args.switch_tick,
        "burst_ticks": args.burst_ticks,
        "input_schedule": args.input_schedule,
        "seed": args.seed,
        "neurons": args.neurons,
        "walkers": args.walkers,
        "k": args.k,
        "hops": args.hops,
        "candidates": args.candidates,
        "threshold": args.threshold,
        "lambda_omega": args.lambda_omega,
        "domain_modulation": args.domain_modulation,
        "hz": args.hz,
        "stim_amp": args.stim_amp,
        "reafferent_gain": args.reafferent_gain,
        "feature_group_size": args.feature_group_size,
        "selector_group_size": args.selector_group_size,
        "release_threshold": args.release_threshold,
        "current_op_min": args.current_op_min,
        "current_lane_min": args.current_lane_min,
        "selector_decay": args.selector_decay,
        "release_cooldown": args.release_cooldown,
        "aperture_group_size": args.aperture_group_size,
        "aperture_current_min": args.aperture_current_min,
        "close_hold_ticks": args.close_hold_ticks,
        "bus_capacity": args.bus_capacity,
        "bus_drain": args.bus_drain,
        "intent_retain": args.intent_retain,
        "intent_trigger_mix": args.intent_trigger_mix,
        "intent_top_k": args.intent_top_k,
        "after_window_ticks": args.after_window_ticks,
        "bot_event_lag": getattr(args, "bot_event_lag", 50),
        "yoked_event_offset": getattr(args, "yoked_event_offset", 17),
        "live_terminal": getattr(args, "live_terminal", True),
        "tick_print_stride": getattr(args, "tick_print_stride", 1),
        "live_topn": getattr(args, "live_topn", 3),
    }
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg


def ns_from_cfg(cfg: Dict[str, Any], run_dir: Path):
    return argparse.Namespace(
        repo=Path(cfg["repo"]),
        run_dir=run_dir,
        neurons=int(cfg["neurons"]),
        walkers=int(cfg["walkers"]),
        k=int(cfg["k"]),
        hops=int(cfg["hops"]),
        candidates=int(cfg["candidates"]),
        threshold=float(cfg["threshold"]),
        lambda_omega=float(cfg["lambda_omega"]),
        domain_modulation=float(cfg["domain_modulation"]),
        hz=float(cfg["hz"]),
        seed=int(cfg["seed"]),
        ticks=int(cfg["ticks_total"]),
        max_wall_s=10**9,
        stim_amp=float(cfg["stim_amp"]),
        feature_group_size=int(cfg["feature_group_size"]),
        selector_group_size=int(cfg["selector_group_size"]),
        release_threshold=float(cfg["release_threshold"]),
        current_op_min=int(cfg["current_op_min"]),
        current_lane_min=int(cfg["current_lane_min"]),
        selector_decay=float(cfg["selector_decay"]),
        release_cooldown=int(cfg["release_cooldown"]),
        aperture_group_size=int(cfg["aperture_group_size"]),
        aperture_current_min=int(cfg["aperture_current_min"]),
        close_hold_ticks=int(cfg["close_hold_ticks"]),
        bus_capacity=int(cfg["bus_capacity"]),
        bus_drain=int(cfg["bus_drain"]),
    )


def run_one_burst(args, cfg: Dict[str, Any], run_name: str) -> Dict[str, Any]:
    if run_name not in RUN_NAMES:
        raise SystemExit(f"bad run name: {run_name}; expected one of {RUN_NAMES}")
    suite_dir=args.suite_dir.resolve()
    run_dir=suite_dir/run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    state_path=run_dir/HARNESS_STATE
    state=load_harness_state(state_path)
    start_tick=0 if state is None else int(state.get("next_tick", 0))
    total=int(cfg["ticks_total"])
    burst=int(cfg["burst_ticks"])
    end_tick=min(total, start_tick+burst)
    if start_tick >= total:
        return {"run_name": run_name, "status": "complete", "next_tick": start_tick, "ticks_total": total}

    np.random.seed(int(cfg["seed"]))
    run_args=ns_from_cfg(cfg, run_dir)
    C,bus,adc,nx_like,eng,_world,selector,aperture = base.build(run_args, run_dir)
    translator=IntentionTraceTranslatorSet(Path(cfg["intent_index_dir"]), modes=["aperture_only","selector_only","fused"], retain=float(cfg["intent_retain"]), trigger_mix=float(cfg["intent_trigger_mix"]), top_k=int(cfg["intent_top_k"]))
    chooser=EmissionSelector(translator, top_k=int(cfg["intent_top_k"]), seed=int(cfg["seed"]))
    bot = DeterministicConversationBot(seed=int(cfg["seed"]))
    lag_bot = DeterministicConversationBot(seed=int(cfg["seed"]) + 101)
    bot_lag_events = deque(maxlen=max(1, int(cfg.get("bot_event_lag", 50))) + 2)
    witness_index = int(state.get("witness_index", 0)) if state is not None else 0
    yoked_packets = []
    if run_name == "pal_yoked":
        yoked_packets = _load_yoked_packets(suite_dir / "pal_live")

    if state is not None:
        ckpt=state.get("checkpoint")
        if not ckpt or not Path(ckpt).exists():
            raise SystemExit(f"missing checkpoint for resume: {ckpt}")
        from vdm_rt.core.memory import load_engram
        load_engram(str(ckpt), C, adc=adc)
        load_selector_state(selector, state.get("selector", {}))
        load_aperture_state(aperture, state.get("aperture", {}))
        load_translator_state(translator, state.get("translator", {}))
        chooser.load_state_dict(state.get("chooser", {}))
        pending_reafference=list(state.get("pending_reafference", []))
    else:
        pending_reafference=[]
        (run_dir/"run_config.json").write_text(json.dumps({**cfg, "run_name": run_name}, indent=2), encoding="utf-8")
        (run_dir/"aperture_group_map.json").write_text(json.dumps(aperture.ap_groups, indent=2), encoding="utf-8")
        (run_dir/"selector_group_map.json").write_text(json.dumps({"ops": selector.op_groups, "lanes": selector.lane_groups}, indent=2), encoding="utf-8")

    from vdm_rt.runtime.events_adapter import observations_to_events, adc_metrics_to_event

    append_mode=start_tick > 0
    tick_file,tick_writer=csv_writer(run_dir/"tick_rows.csv", FIELDS, append=append_mode)
    feat_file,feat_writer=csv_writer(run_dir/"feature_layer_counts.csv", FEATURE_FIELDS, append=append_mode)

    completed=start_tick
    burst_start=time.time()
    try:
        with base.ScanFirewall(C):
            for tick in range(start_tick, end_tick):
                tt=time.perf_counter()
                phase, condition, policy = plan_for(run_name, tick, int(cfg["switch_tick"]))
                external_atom=stable_atom(tick, str(cfg.get("input_schedule", "single")))
                re_payloads=pending_reafference
                pending_reafference=[]
                re_text=" | ".join([str(x.get("payload", "")) for x in re_payloads])
                atom=external_atom if not re_text else external_atom + " || " + re_text

                ap_state_before=aperture.state_dict()
                gains=ap_state_before["gains"]
                stim_all=[]; ext_all=[]; ref_all=[]; layer_counts={}

                by_layer=aperture.feature_indices_by_layer(external_atom, int(cfg["neurons"]), f"ute-anti-reafference:{cfg['seed']}:external", int(cfg["feature_group_size"]))
                for layer,idxs in by_layer.items():
                    gain=float(gains.get(layer,0.0)); layer_counts[layer]=len(idxs)
                    if idxs and gain>0:
                        C.stimulate_indices(idxs, amp=float(cfg["stim_amp"])*gain)
                        stim_all.extend(idxs); ext_all.extend(idxs)

                for rp in re_payloads:
                    payload=str(rp.get("payload", ""))
                    if not payload:
                        continue
                    r_by=aperture.feature_indices_by_layer(payload, int(cfg["neurons"]), f"ute-anti-reafference:{cfg['seed']}:self", int(cfg["feature_group_size"]))
                    for layer,idxs in r_by.items():
                        gain=float(gains.get(layer,0.0))
                        if idxs and gain>0:
                            C.stimulate_indices(idxs, amp=float(cfg["stim_amp"])*float(cfg["reafferent_gain"])*gain)
                            stim_all.extend(idxs); ref_all.extend(idxs)

                append_jsonl(run_dir/"ute_input_stream.jsonl", {
                    "tick":tick,"run_label":run_name,"phase":phase,"condition":condition,
                    "external_atom":external_atom,"reafferent_payloads":re_payloads,
                    "aperture_before":ap_state_before,"layer_counts":layer_counts,
                    "stim_hash":sha_list(stim_all),"stim_count":len(set(stim_all)),
                    "external_stim_count":len(set(ext_all)),"reafferent_stim_count":len(set(ref_all)),
                })
                feat_writer.writerow({
                    "tick":tick,"run_label":run_name,"phase":phase,"condition":condition,
                    **{k:layer_counts.get(k,0) for k in ["whole","norm","span","position","shape","pair","char","punct","dark"]},
                    "stim_total":len(set(stim_all)), "external_stim_count":len(set(ext_all)),
                    "reafferent_stim_count":len(set(ref_all)), "gains":json.dumps(gains),
                }); feat_file.flush()

                sie2=float(getattr(C,"_last_sie2_valence",0.0) or 0.0)
                sie_gate=max(0.35,min(1.0,sie2 if sie2>0.0 else 1.0))
                C.step(tick/max(1e-9,float(cfg["hz"])), domain_modulation=float(cfg["domain_modulation"]), sie_drive=sie_gate, use_time_dynamics=True)
                obs=bus.drain(int(cfg["bus_drain"]))
                adc.update_from(obs)
                adc_m=adc.get_metrics()
                evs=observations_to_events(obs)
                evs.append(adc_metrics_to_event(adc_m,tick))
                nx_like._emit_step=tick
                eng.step(int(max(1,nx_like.dt*1000.0)), evs)

                obs_nodes=[]
                for o in obs:
                    try:
                        obs_nodes.extend([int(x) for x in (getattr(o,"nodes",[]) or [])])
                    except Exception:
                        pass
                sel=selector.observe(tick,obs_nodes,"stable_input",atom)
                ap_update=aperture.observe_and_update(tick,obs_nodes)
                if any(c.startswith("AP_CLOSE") or c.startswith("AP_REOPEN") or c=="AP_OPEN_OR_RELAX" for c in ap_update["aperture_commands"]):
                    append_jsonl(run_dir/"aperture_events.jsonl", {"tick":tick,"run_label":run_name,"phase":phase,"condition":condition,"external_atom":external_atom,"reafferent_payloads":re_payloads,"active_aperture":ap_update["active_aperture"],"aperture_commands":ap_update["aperture_commands"],"state":ap_update["aperture_state"]})
                append_jsonl(run_dir/"ute_aperture_state.jsonl", {"tick":tick,"run_label":run_name,"phase":phase,"condition":condition,"external_atom":external_atom,"reafferent_payloads":re_payloads,"before":ap_state_before,"after":ap_update["aperture_state"],"active_aperture":ap_update["active_aperture"],"commands":ap_update["aperture_commands"]})
                live_tick_line(cfg, tick=tick, run_name=run_name, phase=phase, condition=condition, policy=policy, external_atom=external_atom, re_text=re_text, sel=sel, ap_update=ap_update, ap_state_before=ap_state_before)
                for ev in sel["emitted"]:
                    ev["run_label"]=run_name; ev["phase"]=phase; ev["condition"]=condition
                    append_jsonl(run_dir/"utd_events.jsonl", ev)

                rec={
                    "tick":tick,"run_label":run_name,"phase":phase,"condition":condition,
                    "emit_policy":policy,"atom":atom,"external_atom":external_atom,
                    "reafferent_payload":re_text,
                    "reafferent_kind":";".join([str(x.get("kind", "")) for x in re_payloads]),
                    "stim_count":len(set(stim_all)),"stim_hash":sha_list(stim_all),
                    "occlusion_level":ap_state_before["occlusion_level"],"aperture_level":ap_state_before["level"],
                    "aperture_level_name":ap_state_before["level_name"],"aperture_width":ap_state_before["width"],
                    "active_aperture":" ".join(ap_update["active_aperture"]),
                    "aperture_commands":" ".join(ap_update["aperture_commands"]),
                    "obs_count":len(obs),"obs_nodes_unique":len(set(obs_nodes)),
                    "active_ops":" ".join(sel["active_ops"]),"active_lanes":" ".join(sel["active_lanes"]),
                    "witnesses":" ".join(e["witness"] for e in sel["emitted"]),
                    "release_lane":sel["release_lane"],"release_score":sel["release_score"],
                    "gate_pressure":sel["gate_pressure"],"top_ops":json.dumps(sel["top_ops"]),
                    "top_lanes":json.dumps(sel["top_lanes"]),"top_trace":json.dumps(sel["top_trace"]),
                    "tick_s":float(time.perf_counter()-tt),
                }
                translator.update_tick(rec, raw_ref={"tick":tick,"phase":phase,"condition":condition,"row_file":"tick_rows.csv"})

                for ev in sel["emitted"]:
                    event_context={
                        "event_kind":"witness","tick":tick,"phase_label":phase,"condition":condition,
                        "run_label":run_name,"run_dir":str(run_dir),
                        "tick_rows_path":str(run_dir/"tick_rows.csv"),
                        "trace_log_path":str(run_dir/"trace_log.jsonl"),
                        "witness_event_id":ev.get("witness", ""),
                    }
                    samples={}
                    for mode,word in translator.words.items():
                        samples[mode]=sample_word_with_vector(word, event_context, top_k=int(cfg["intent_top_k"]))
                    true_fused=samples["fused"]
                    true_top1=true_fused["top"][0] if true_fused["top"] else {}
                    bot_packet = None
                    bot_source = ""
                    bot_source_tick = ""
                    bot_source_witness_index = ""
                    if policy == "no_return":
                        choice = chooser.choose("fused", samples, tick)
                        payload = ""
                        kind = "no_return"
                        choice["emitted"] = {"phrase":"", "family":"no_return", "leaf":"no_return", "id":"no_return"}
                        choice["emitted_selection_mode"] = "no_return"
                    elif policy == "pal_live":
                        choice = chooser.choose("fused", samples, tick)
                        bot_packet = bot.step(_make_bot_record(true_fused, samples=samples)).to_dict()
                        bot_source = "current_full_witness_event"
                        bot_source_tick = bot_packet.get("tick", "")
                        emitted_item = _packet_to_emitted_item(bot_packet)
                        choice["emitted"] = emitted_item
                        choice["emitted_topk"] = [emitted_item]
                        choice["emitted_selection_mode"] = policy
                        payload = str(bot_packet.get("reply_text", ""))
                        kind = "pal_world_reply"
                    elif policy == "pal_static":
                        choice = chooser.choose("fused", samples, tick)
                        bot_packet = bot.step_static(_make_bot_record(true_fused, samples=samples)).to_dict()
                        bot_source = "static_pal_progression"
                        bot_source_tick = bot_packet.get("tick", "")
                        emitted_item = _packet_to_emitted_item(bot_packet)
                        choice["emitted"] = emitted_item
                        choice["emitted_topk"] = [emitted_item]
                        choice["emitted_selection_mode"] = policy
                        payload = str(bot_packet.get("reply_text", ""))
                        kind = "pal_world_reply"
                    elif policy == "pal_yoked":
                        choice = chooser.choose("fused", samples, tick)
                        if yoked_packets:
                            offset = int(cfg.get("yoked_event_offset", 17))
                            src_index = (witness_index + offset) % len(yoked_packets)
                            src = yoked_packets[src_index]
                            bot_packet = dict(src.get("bot_packet") or {})
                            bot_source = f"yoked_replay_from_pal_live_offset_{offset}"
                            bot_source_tick = src.get("tick", "")
                            bot_source_witness_index = src.get("witness_index", src_index)
                        else:
                            bot_packet = _neutral_bot_packet(bot, tick, "pal_yoked_stream_exhausted")
                            bot_source = "neutral_yoked_stream_exhausted"
                            bot_source_tick = tick
                            bot_source_witness_index = witness_index
                        emitted_item = _packet_to_emitted_item(bot_packet)
                        choice["emitted"] = emitted_item
                        choice["emitted_topk"] = [emitted_item]
                        choice["emitted_selection_mode"] = policy
                        payload = str(bot_packet.get("reply_text", ""))
                        kind = "pal_world_reply"
                    else:
                        choice=chooser.choose(policy, samples, tick)
                        emitted=choice["emitted"] or {}
                        payload=ev.get("witness", "") if policy == "baseline" else (emitted.get("phrase") or emitted.get("utterance") or "")
                        kind="witness_code" if policy == "baseline" else "utterance_phrase"
                    emitted=choice["emitted"] or {}
                    if payload:
                        prefix="self witness " if kind == "witness_code" else ("pal says " if kind == "pal_world_reply" else "self utterance ")
                        pending_reafference.append({"tick_emitted":tick,"payload":prefix+str(payload),"kind":kind,"selection_mode":choice.get("emitted_selection_mode")})
                        follow_up_payload = str((bot_packet or {}).get("follow_up_text", "")).strip()
                        if follow_up_payload:
                            pending_reafference.append({"tick_emitted":tick,"payload":"bot followup "+follow_up_payload,"kind":"pal_world_followup","selection_mode":choice.get("emitted_selection_mode"),"follow_up_id":(bot_packet or {}).get("follow_up_id", "")})

                    live_witness_block(cfg, tick=tick, run_name=run_name, ev=ev, policy=policy, external_atom=external_atom, re_text=re_text, samples=samples, choice=choice, payload=payload, kind=kind)

                    for mode,s in samples.items():
                        r=s["record"].copy(); r["condition"]=condition; r["emission_policy_at_event"]=policy
                        append_jsonl(run_dir/"intent_translation_events.jsonl", r)

                    er={
                        "tick":tick,"run_label":run_name,"phase_label":phase,"condition":condition,
                        "translation_mode_used_for_emission":policy,
                        "source_window_start_tick":true_fused["record"].get("source_window_start_tick"),
                        "source_window_end_tick":true_fused["record"].get("source_window_end_tick"),
                        "true_top1_phrase":true_top1.get("phrase"),"true_top1_family":true_top1.get("family"),"true_top1_leaf":true_top1.get("leaf"),
                        "true_topk_phrases":json.dumps([x.get("phrase") for x in true_fused["top"]], ensure_ascii=False),
                        "true_topk_families":json.dumps([x.get("family") for x in true_fused["top"]], ensure_ascii=False),
                        "true_topk_leaves":json.dumps([x.get("leaf") for x in true_fused["top"]], ensure_ascii=False),
                        "true_topk_scores":json.dumps([x.get("cosine") for x in true_fused["top"]]),
                        "true_topk_distances":json.dumps([x.get("distance") for x in true_fused["top"]]),
                        "true_rank_margin":true_fused.get("margin"),"true_dominant_axes":true_fused["record"].get("dominant_vector_axes"),
                        "emitted_phrase": payload if policy == "baseline" else (emitted.get("phrase") or emitted.get("utterance")),
                        "emitted_family":emitted.get("family") if policy != "baseline" else "witness_code",
                        "emitted_leaf":emitted.get("leaf") if policy != "baseline" else "witness_code",
                        "emitted_selection_mode":choice.get("emitted_selection_mode"),
                        "emitted_score_against_anti_query":choice.get("emitted_score_against_anti_query"),
                        "signed_centered_score_against_anti_query":choice.get("signed_centered_score_against_anti_query"),
                        "signed_centered_similarity_to_true":choice.get("signed_centered_similarity_to_true"),
                        "anti_selection_basis":choice.get("anti_selection_basis"),
                        "emitted_similarity_to_true_vector":choice.get("emitted_similarity_to_true_vector"),
                        "emitted_distance_from_true_vector":choice.get("emitted_distance_from_true_vector"),
                        "witness_event_id":ev.get("witness", ""),
                        "actual_reafferent_payload_next_tick": pending_reafference[-1]["payload"] if pending_reafference else "",
                        "raw_trace_window_reference": true_fused["record"].get("raw_trace_window_reference"),
                        "aperture_window_translation": samples["aperture_only"]["record"].get("top1_phrase"),
                        "selector_window_translation": samples["selector_only"]["record"].get("top1_phrase"),
                        "fused_window_translation": true_top1.get("phrase"),
                    }
                    er.update({
                        "bot_reply_text": (bot_packet or {}).get("reply_text", ""),
                        "bot_action": (bot_packet or {}).get("action", ""),
                        "bot_aperture_hint": (bot_packet or {}).get("aperture_hint", ""),
                        "bot_stimulus_policy": (bot_packet or {}).get("stimulus_policy", ""),
                        "bot_reafferent_gain_hint": (bot_packet or {}).get("reafferent_gain_hint", ""),
                        "bot_input_family": (bot_packet or {}).get("input_family", ""),
                        "bot_input_leaf": (bot_packet or {}).get("input_leaf", ""),
                        "bot_rule_id": (bot_packet or {}).get("rule_id", ""),
                        "bot_source": bot_source,
                        "bot_source_tick": bot_source_tick,
                        "bot_source_witness_index": bot_source_witness_index,
                        "witness_index": witness_index,
                    })
                    append_jsonl(run_dir/RAW_EVENT_JSONL, er)
                    if bot_packet is not None:
                        append_jsonl(run_dir/"bot_packets.jsonl", {
                            "tick": tick,
                            "run_label": run_name,
                            "phase_label": phase,
                            "condition": condition,
                            "policy": policy,
                            "witness_event_id": ev.get("witness", ""),
                            "witness_index": witness_index,
                            "true_top1_phrase": true_top1.get("phrase"),
                            "true_top1_family": true_top1.get("family"),
                            "true_top1_leaf": true_top1.get("leaf"),
                            "bot_source": bot_source,
                            "bot_source_tick": bot_source_tick,
                            "bot_source_witness_index": bot_source_witness_index,
                            "bot_packet": bot_packet,
                        })
                    bot_lag_events.append(true_fused)
                    witness_index += 1

                    emitted_topk=choice.get("emitted_topk") or []
                    topk_rows=[]
                    for rank in range(max(len(true_fused["top"]), len(emitted_topk))):
                        tr=true_fused["top"][rank] if rank < len(true_fused["top"]) else {}
                        ar=emitted_topk[rank] if rank < len(emitted_topk) else {}
                        topk_rows.append({
                            "tick":tick,"run_label":run_name,"phase_label":phase,"condition":condition,
                            "witness_event_id":ev.get("witness", ""),"rank":rank+1,
                            "true_phrase":tr.get("phrase"),"true_family":tr.get("family"),"true_leaf":tr.get("leaf"),
                            "true_score":tr.get("cosine"),"true_distance":tr.get("distance"),
                            "emitted_candidate_phrase":ar.get("phrase"),"emitted_candidate_family":ar.get("family"),"emitted_candidate_leaf":ar.get("leaf"),
                            "emitted_candidate_score":ar.get("cosine"),"emitted_candidate_distance":ar.get("distance"),
                            "emitted_candidate_signed_centered_similarity_to_true":ar.get("signed_centered_similarity_to_true"),
                            "emitted_candidate_signed_centered_score_against_anti_query":ar.get("signed_centered_score_against_anti_query"),
                            "emitted_selection_mode":choice.get("emitted_selection_mode"),
                        })
                    append_jsonl(run_dir/TOPK_JSONL, topk_rows)
                    reset_translator_words(translator, tick)

                tick_writer.writerow(rec); tick_file.flush()
                append_jsonl(run_dir/"trace_log.jsonl", {"tick":tick,"run_label":run_name,"phase":phase,"condition":condition,"external_atom":external_atom,"reafferent_payloads":re_payloads,"selector":sel,"aperture":ap_update})
                completed=tick+1
    finally:
        tick_file.close(); feat_file.close()

    from vdm_rt.core.memory import save_checkpoint
    ckpt=str(save_checkpoint(str(run_dir), completed, C, fmt="h5", adc=adc))
    burst_manifest=read_jsonl(run_dir/"burst_manifest.jsonl")
    burst_rec={"run_name":run_name,"burst_start_tick":start_tick,"burst_end_tick_exclusive":completed,"checkpoint":ckpt,"elapsed_s":round(time.time()-burst_start,3)}
    append_jsonl(run_dir/"burst_manifest.jsonl", burst_rec)
    save_harness_state(state_path, {
        "run_name": run_name,
        "next_tick": completed,
        "ticks_total": total,
        "checkpoint": ckpt,
        "pending_reafference": pending_reafference,
        "selector": selector_state(selector),
        "aperture": aperture_state(aperture),
        "translator": translator_state(translator),
        "chooser": chooser.state_dict(),
        "last_burst": burst_rec,
    })
    summary={"run_name":run_name,"status":"complete" if completed>=total else "partial","burst_start_tick":start_tick,"next_tick":completed,"ticks_total":total,"checkpoint":ckpt,"elapsed_s":round(time.time()-burst_start,3)}
    (run_dir/"last_burst_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


def load_tick_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def first_score(row: Dict[str, Any]) -> float:
    vals=parse_jsonish(row.get("true_topk_scores"), [])
    if isinstance(vals, list) and vals:
        return safe_float(vals[0])
    return 0.0


def summarize_group(rows: List[Dict[str, Any]], evs: List[Dict[str, Any]], group_label: str, phase: str, condition: str) -> Dict[str, Any]:
    idx=op_indices_from_rows(rows)
    true_scores=[first_score(e) for e in evs]
    margins=[safe_float(e.get("true_rank_margin")) for e in evs]
    sim=[safe_float(e.get("emitted_similarity_to_true_vector")) for e in evs]
    signed_sim=[safe_float(e.get("signed_centered_similarity_to_true")) for e in evs if e.get("signed_centered_similarity_to_true") not in (None, "")]
    true_fams=[e.get("true_top1_family","") for e in evs if e.get("true_top1_family")]
    emit_fams=[e.get("emitted_family","") for e in evs if e.get("emitted_family")]
    return {
        "group_label": group_label,
        "condition": condition,
        "phase": phase,
        "ticks": len(rows),
        "witness_count": len(evs),
        "mean_true_top1_score": round(mean(true_scores),6),
        "mean_true_margin": round(mean(margins),6),
        "mean_emitted_similarity_to_true": round(mean(sim),6),
        "mean_signed_centered_similarity_to_true": round(mean(signed_sim),6) if signed_sim else "",
        "mean_gate": round(mean([safe_float(r.get("gate_pressure")) for r in rows]),6),
        "mean_release": round(mean([safe_float(r.get("release_score")) for r in rows]),6),
        **idx,
        "dominant_true_family": Counter(true_fams).most_common(1)[0][0] if true_fams else "",
        "dominant_emitted_family": Counter(emit_fams).most_common(1)[0][0] if emit_fams else "",
        "aperture_translation_mode": "logged",
        "selector_translation_mode": "logged",
        "fused_translation_mode": "emitted" if condition == "aligned_fused" else "anti_source_logged",
    }


def analyze_run(run_dir: Path, cfg: Dict[str, Any]) -> Dict[str, Any]:
    tick_rows=load_tick_rows(run_dir/"tick_rows.csv")
    event_rows=read_jsonl(run_dir/RAW_EVENT_JSONL)
    topk_rows=read_jsonl(run_dir/TOPK_JSONL)
    tick_by_t={int(r["tick"]): r for r in tick_rows if str(r.get("tick", "")).strip()}
    event_ticks=[int(e["tick"]) for e in event_rows]
    completed=max([int(r["tick"]) for r in tick_rows], default=-1)+1
    for i,e in enumerate(event_rows):
        t=int(e["tick"])
        nt=event_ticks[i+1] if i+1 < len(event_ticks) else min(completed, t+int(cfg["after_window_ticks"])+1)
        prev_rows=[r for r in tick_rows if max(0,t-int(cfg["after_window_ticks"])) <= int(r["tick"]) < t]
        next_rows=[r for r in tick_rows if t < int(r["tick"]) < nt]
        idx=op_indices_from_rows(next_rows)
        e["gate_before"]=round(mean([safe_float(r.get("gate_pressure")) for r in prev_rows]),6)
        e["gate_after"]=round(mean([safe_float(r.get("gate_pressure")) for r in next_rows]),6)
        e["release_before"]=round(mean([safe_float(r.get("release_score")) for r in prev_rows]),6)
        e["release_after"]=round(mean([safe_float(r.get("release_score")) for r in next_rows]),6)
        e["witness_latency_after_emission"]=(nt-t) if (i+1 < len(event_ticks)) else ""
        e["aperture_level_after_emission"]=mode_val(next_rows, "aperture_level_name")
        e["occlusion_after_emission"]=round(mean([safe_float(r.get("occlusion_level")) for r in next_rows]),6)
        e.update({f"after_{k}":v for k,v in idx.items()})
        if i+1 < len(event_rows):
            e["next_window_aperture_translation"]=event_rows[i+1].get("aperture_window_translation", "")
            e["next_window_selector_translation"]=event_rows[i+1].get("selector_window_translation", "")
            e["next_window_fused_translation"]=event_rows[i+1].get("fused_window_translation", event_rows[i+1].get("true_top1_phrase", ""))
        else:
            e["next_window_aperture_translation"]=""
            e["next_window_selector_translation"]=""
            e["next_window_fused_translation"]=""
    write_csv(run_dir/"event_translation_log.csv", event_rows)
    write_csv(run_dir/"topk_true_vs_emitted.csv", topk_rows)
    write_csv(run_dir/"next_window_effects.csv", event_rows)

    groups=defaultdict(list)
    for r in tick_rows:
        groups[(r.get("condition", ""), r.get("phase", ""))].append(r)
    ev_groups=defaultdict(list)
    for e in event_rows:
        ev_groups[(e.get("condition", ""), e.get("phase_label", ""))].append(e)
    condition_summary=[]
    for (cond, phase), rows in sorted(groups.items()):
        condition_summary.append(summarize_group(rows, ev_groups.get((cond, phase), []), f"{run_dir.name}:{phase}", phase, cond))
    write_csv(run_dir/"condition_summary.csv", condition_summary)

    recovery=[]
    if run_dir.name == "switch_test":
        by_phase={r["phase"]:r for r in condition_summary}
        pre=by_phase.get("switch_normal_pre", {})
        anti=by_phase.get("switch_inverted", {})
        for metric in ["witness_count","mean_true_top1_score","mean_true_margin","mean_emitted_similarity_to_true","mean_signed_centered_similarity_to_true","mean_gate","mean_release","interaction","revision","withdrawal","engaged_score","guardedness"]:
            recovery.append({
                "metric":metric,
                "switch_normal_pre":pre.get(metric,""),
                "switch_inverted":anti.get(metric,""),
                "inverted_minus_normal":round(safe_float(anti.get(metric))-safe_float(pre.get(metric)),6),
            })
    write_csv(run_dir/"recovery_summary.csv", recovery)
    summary={
        "run_name": run_dir.name,
        "ticks_completed": completed,
        "witness_total": len(event_rows),
        "condition_summary_rows": len(condition_summary),
        "complete": completed >= int(cfg["ticks_total"]),
    }
    (run_dir/"run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def copy_report_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dst)


def analyze_suite(args, cfg: Dict[str, Any]) -> Dict[str, Any]:
    suite_dir=args.suite_dir.resolve()
    reports_dir=suite_dir/"reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    run_summaries=[]
    for run_name in RUN_NAMES:
        rd=suite_dir/run_name
        if rd.exists():
            run_summaries.append(analyze_run(rd, cfg))
            for fn in ["condition_summary.csv","event_translation_log.csv","topk_true_vs_emitted.csv","next_window_effects.csv","recovery_summary.csv","run_summary.json","burst_manifest.jsonl"]:
                copy_report_file(rd/fn, reports_dir/run_name/fn)

    comparison=[]
    for run_name in RUN_NAMES:
        rd=suite_dir/run_name
        tick_rows=load_tick_rows(rd/"tick_rows.csv")
        event_rows=read_jsonl(rd/RAW_EVENT_JSONL)
        if not tick_rows:
            continue
        if run_name == "normal_control":
            rows=tick_rows
            evs=event_rows
            comparison.append(summarize_group(rows, evs, "normal_control_full", "normal_control_full", "aligned_fused"))
        elif run_name == "inverted_control":
            rows=tick_rows
            evs=event_rows
            comparison.append(summarize_group(rows, evs, "inverted_control_full", "inverted_control_full", "anti_vector"))
        elif run_name == "switch_test":
            sw=int(cfg["switch_tick"])
            pre_rows=[r for r in tick_rows if int(r["tick"]) < sw]
            inv_rows=[r for r in tick_rows if int(r["tick"]) >= sw]
            pre_evs=[e for e in event_rows if int(e["tick"]) < sw]
            inv_evs=[e for e in event_rows if int(e["tick"]) >= sw]
            comparison.append(summarize_group(pre_rows, pre_evs, "switch_test_normal_segment", "switch_normal_pre", "aligned_fused"))
            comparison.append(summarize_group(inv_rows, inv_evs, "switch_test_inverted_segment", "switch_inverted", "anti_vector"))
    write_csv(reports_dir/"comparison_summary.csv", comparison)

    required=[]
    for run_name in RUN_NAMES:
        state=load_harness_state(suite_dir/run_name/HARNESS_STATE)
        status="missing"
        if state:
            status="complete" if int(state.get("next_tick",0)) >= int(cfg["ticks_total"]) else f"partial:{state.get('next_tick')}/{cfg['ticks_total']}"
        required.append((run_name,status))
    lines=[]
    lines.append("# Pal-World VDM conversation suite")
    lines.append("")
    lines.append("This report is generated by `tools/run_trace_conditioned_bot_suite_core.py --analyze`.")
    lines.append("")
    lines.append("## Design")
    lines.append("")
    lines.append(f"- total ticks per run: `{cfg['ticks_total']}`")
    lines.append(f"- burst size: `{cfg['burst_ticks']}` ticks")
    lines.append(f"- switch tick for `switch_test`: `{cfg['switch_tick']}`")
    lines.append(f"- external input schedule: `{cfg['input_schedule']}`")
    lines.append("- runs: `normal_control`, `inverted_control`, `switch_test`")
    lines.append("- anti-vector basis: signed-centered utterance bank, nearest phrase to `-(true_vec - bank_mean)`")
    lines.append("")
    lines.append("## Completion")
    lines.append("")
    for run_name,status in required:
        lines.append(f"- `{run_name}`: `{status}`")
    lines.append("")
    lines.append("## Main comparison")
    lines.append("")
    if comparison:
        cols=["group_label","ticks","witness_count","mean_true_top1_score","mean_true_margin","mean_emitted_similarity_to_true","mean_signed_centered_similarity_to_true","mean_gate","mean_release","interaction","revision","withdrawal","engaged_score","guardedness","dominant_true_family","dominant_emitted_family"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"]*len(cols)) + " |")
        for r in comparison:
            lines.append("| " + " | ".join(str(r.get(c,"")) for c in cols) + " |")
    else:
        lines.append("No comparison rows yet. Finish at least one run and re-run analysis.")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("- `reports/comparison_summary.csv`")
    for run_name in RUN_NAMES:
        lines.append(f"- `reports/{run_name}/event_translation_log.csv`")
        lines.append(f"- `reports/{run_name}/topk_true_vs_emitted.csv`")
        lines.append(f"- `reports/{run_name}/next_window_effects.csv`")
        lines.append(f"- `reports/{run_name}/condition_summary.csv`")
    (reports_dir/"RESULTS.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return {"reports_dir": str(reports_dir), "run_summaries": run_summaries, "comparison_rows": len(comparison)}


def suite_status(suite_dir: Path, cfg: Dict[str, Any]) -> Dict[str, Any]:
    rows=[]
    total=int(cfg["ticks_total"])
    for rn in RUN_NAMES:
        st=load_harness_state(suite_dir/rn/HARNESS_STATE)
        next_tick=0 if st is None else int(st.get("next_tick", 0))
        rows.append({"run_name": rn, "next_tick": next_tick, "ticks_total": total, "complete": next_tick >= total})
    return {"suite_dir": str(suite_dir), "runs": rows, "complete": all(r["complete"] for r in rows)}


def next_incomplete_run(suite_dir: Path, cfg: Dict[str, Any]) -> Optional[str]:
    total=int(cfg["ticks_total"])
    for rn in RUN_NAMES:
        st=load_harness_state(suite_dir/rn/HARNESS_STATE)
        next_tick=0 if st is None else int(st.get("next_tick", 0))
        if next_tick < total:
            return rn
    return None


def run_all(args, cfg: Dict[str, Any]) -> None:
    while True:
        rn=next_incomplete_run(args.suite_dir.resolve(), cfg)
        if rn is None:
            break
        cmd=[
            sys.executable, str(Path(__file__).resolve()),
            "--suite-dir", str(args.suite_dir.resolve()),
            "--repo", str(Path(cfg["repo"])),
            "--intent-index-dir", str(Path(cfg["intent_index_dir"])),
            "--next-burst-run", rn,
        ]
        print("\n=== burst subprocess:", " ".join(cmd), "===\n", flush=True)
        subprocess.check_call(cmd)
    analyze_suite(args, cfg)


def main() -> int:
    ap=argparse.ArgumentParser(description="Trace-conditioned Pal-World conversation suite core runner.")
    ap.add_argument("--suite-dir", type=Path, default=Path("runs/anti_reafference_clean_1500"))
    ap.add_argument("--repo", type=Path, default=Path("codebase/vdm_rt-main"))
    ap.add_argument("--intent-index-dir", type=Path, default=Path("index"))
    ap.add_argument("--reset", action="store_true")
    action=ap.add_mutually_exclusive_group(required=True)
    action.add_argument("--init", action="store_true")
    action.add_argument("--status", action="store_true")
    action.add_argument("--next-burst", action="store_true", help="run one 300-tick burst for the first incomplete run")
    action.add_argument("--next-burst-run", choices=RUN_NAMES, help="run one burst for a specific run")
    action.add_argument("--run-all", action="store_true", help="run all bursts as separate subprocesses, then analyze")
    action.add_argument("--analyze", action="store_true")

    ap.add_argument("--ticks-total", type=int, default=1500)
    ap.add_argument("--switch-tick", type=int, default=1000)
    ap.add_argument("--burst-ticks", type=int, default=300)
    ap.add_argument("--input-schedule", choices=["single","cycle"], default="single")
    ap.add_argument("--neurons", type=int, default=1000)
    ap.add_argument("--walkers", type=int, default=1200)
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--hops", type=int, default=2)
    ap.add_argument("--candidates", type=int, default=64)
    ap.add_argument("--threshold", type=float, default=0.15)
    ap.add_argument("--lambda-omega", type=float, default=0.1)
    ap.add_argument("--domain-modulation", type=float, default=1.15625)
    ap.add_argument("--hz", type=float, default=10.0)
    ap.add_argument("--seed", type=int, default=20260627)
    ap.add_argument("--stim-amp", type=float, default=0.035)
    ap.add_argument("--reafferent-gain", type=float, default=0.22)
    ap.add_argument("--feature-group-size", type=int, default=1)
    ap.add_argument("--selector-group-size", type=int, default=8)
    ap.add_argument("--release-threshold", type=float, default=0.8)
    ap.add_argument("--current-op-min", type=int, default=2)
    ap.add_argument("--current-lane-min", type=int, default=2)
    ap.add_argument("--selector-decay", type=float, default=0.965)
    ap.add_argument("--release-cooldown", type=int, default=8)
    ap.add_argument("--aperture-group-size", type=int, default=10)
    ap.add_argument("--aperture-current-min", type=int, default=2)
    ap.add_argument("--close-hold-ticks", type=int, default=2)
    ap.add_argument("--bus-capacity", type=int, default=65536)
    ap.add_argument("--bus-drain", type=int, default=4096)
    ap.add_argument("--intent-retain", type=float, default=0.94)
    ap.add_argument("--intent-trigger-mix", type=float, default=0.18)
    ap.add_argument("--intent-top-k", type=int, default=8)
    ap.add_argument("--after-window-ticks", type=int, default=25)
    ap.add_argument("--bot-event-lag", type=int, default=50)
    ap.add_argument("--yoked-event-offset", type=int, default=17)
    ap.add_argument("--live-terminal", action="store_true", default=True)
    ap.add_argument("--no-live-terminal", dest="live_terminal", action="store_false")
    ap.add_argument("--tick-print-stride", type=int, default=1)
    ap.add_argument("--live-topn", type=int, default=3)
    args=ap.parse_args()

    cfg=ensure_suite_config(args)
    if args.init:
        print(json.dumps({"initialized": str(args.suite_dir.resolve()), "config": cfg}, indent=2))
        return 0
    if args.status:
        print(json.dumps(suite_status(args.suite_dir.resolve(), cfg), indent=2))
        return 0
    if args.next_burst:
        rn=next_incomplete_run(args.suite_dir.resolve(), cfg)
        if rn is None:
            print(json.dumps({"status":"complete", "suite_dir": str(args.suite_dir.resolve())}, indent=2))
            return 0
        run_one_burst(args, cfg, rn)
        return 0
    if args.next_burst_run:
        run_one_burst(args, cfg, args.next_burst_run)
        return 0
    if args.run_all:
        run_all(args, cfg)
        print(json.dumps(suite_status(args.suite_dir.resolve(), cfg), indent=2))
        return 0
    if args.analyze:
        print(json.dumps(analyze_suite(args, cfg), indent=2))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
