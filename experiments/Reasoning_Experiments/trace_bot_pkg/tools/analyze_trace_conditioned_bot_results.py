#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

RUN_NAMES = [
    "no_return_control",
    "true_phrase_return",
    "bot_matched_trace",
    "bot_lagged_trace",
    "anti_trace_return",
    "bot_yoked_replay",
]
RAW_EVENT_JSONL = "event_translation_raw.jsonl"
TOPK_JSONL = "topk_true_vs_emitted.jsonl"


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


def read_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields=[]
    seen=set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k); fields.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def fnum(x: Any, default: float = math.nan) -> float:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def mean(xs: Iterable[Any]) -> float:
    vals=[fnum(x) for x in xs]
    vals=[v for v in vals if not math.isnan(v)]
    return round(sum(vals)/len(vals), 6) if vals else math.nan


def first_score(row: Dict[str, Any]) -> float:
    raw=row.get("true_topk_scores") or row.get("cosine_scores") or "[]"
    try:
        arr=json.loads(raw)
        return fnum(arr[0]) if arr else math.nan
    except Exception:
        return math.nan


def dominant(xs: Iterable[Any]) -> str:
    vals=[str(x) for x in xs if x is not None and str(x).strip()]
    if not vals:
        return ""
    return Counter(vals).most_common(1)[0][0]


def op_indices(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    interaction=revision=withdrawal=0.0
    for r in rows:
        active=set(str(r.get("active_ops", "")).split())
        interaction += (1.0 if "COMMIT" in active else 0.0) + (1.0 if "RELEASE" in active else 0.0)
        revision += (1.0 if "COMPARE" in active else 0.0) + (1.0 if "CORRECT" in active else 0.0) + (1.0 if "RETREAT" in active else 0.0)
        withdrawal += (1.0 if "ABORT" in active else 0.0) + (1.0 if "INHIBIT" in active else 0.0)
    n=max(1, len(rows))
    interaction/=n; revision/=n; withdrawal/=n
    return {
        "interaction": round(interaction, 6),
        "revision": round(revision, 6),
        "withdrawal": round(withdrawal, 6),
        "engaged_score": round(interaction + revision - withdrawal, 6),
        "guardedness": round(withdrawal - revision, 6),
    }


def family_coherence(row: Dict[str, Any]) -> float:
    raw=row.get("true_topk_families") or "[]"
    try:
        fams=[str(x) for x in json.loads(raw) if x is not None]
    except Exception:
        return math.nan
    if not fams:
        return math.nan
    return round(sum(1 for x in fams if x == fams[0])/len(fams), 6)


def witness_interval(events: List[Dict[str, Any]]) -> float:
    ticks=sorted(int(fnum(e.get("tick"), -1)) for e in events if fnum(e.get("tick"), -1) >= 0)
    if len(ticks) < 2:
        return math.nan
    return round(sum(b-a for a,b in zip(ticks, ticks[1:]))/(len(ticks)-1), 6)


def summary_for(run_name: str, tick_rows: List[Dict[str, Any]], events: List[Dict[str, Any]], label: str="whole") -> Dict[str, Any]:
    ticks=[int(fnum(r.get("tick"), -1)) for r in tick_rows if fnum(r.get("tick"), -1) >= 0]
    ev_ticks=[int(fnum(e.get("tick"), -1)) for e in events if fnum(e.get("tick"), -1) >= 0]
    out={
        "run_label": run_name,
        "window": label,
        "tick_start": min(ticks) if ticks else "",
        "tick_end": max(ticks) if ticks else "",
        "tick_count": len(tick_rows),
        "witness_count": len(events),
        "mean_witness_interval": witness_interval(events),
        "mean_true_top1_score": mean(first_score(e) for e in events),
        "mean_true_margin": mean(e.get("true_rank_margin") for e in events),
        "mean_topk_family_coherence": mean(family_coherence(e) for e in events),
        "mean_emitted_similarity_to_true": mean(e.get("emitted_similarity_to_true_vector") for e in events),
        "mean_signed_centered_similarity_to_true": mean(e.get("signed_centered_similarity_to_true") for e in events),
        "mean_gate": mean(r.get("gate_pressure") for r in tick_rows),
        "mean_release": mean(r.get("release_score") for r in tick_rows),
        "mean_occlusion": mean(r.get("occlusion_level") for r in tick_rows),
        "dominant_true_family": dominant(e.get("true_top1_family") for e in events),
        "dominant_emitted_family": dominant(e.get("emitted_family") for e in events),
        "dominant_bot_action": dominant(e.get("bot_action") for e in events),
        "dominant_bot_source": dominant(e.get("bot_source") for e in events),
        "bot_action_counts": json.dumps(Counter(str(e.get("bot_action", "")) for e in events if str(e.get("bot_action", "")).strip()), sort_keys=True),
        "true_family_counts": json.dumps(Counter(str(e.get("true_top1_family", "")) for e in events if str(e.get("true_top1_family", "")).strip()), sort_keys=True),
        "emitted_family_counts": json.dumps(Counter(str(e.get("emitted_family", "")) for e in events if str(e.get("emitted_family", "")).strip()), sort_keys=True),
    }
    out.update(op_indices(tick_rows))
    return out


def next_window_rows(run_name: str, tick_rows: List[Dict[str, Any]], events: List[Dict[str, Any]], after: int) -> List[Dict[str, Any]]:
    by_tick={int(fnum(r.get("tick"), -1)): r for r in tick_rows if fnum(r.get("tick"), -1) >= 0}
    rows=[]
    for e in events:
        t=int(fnum(e.get("tick"), -1))
        if t < 0:
            continue
        win=[by_tick[i] for i in range(t+1, t+1+after) if i in by_tick]
        rec={
            "run_label": run_name,
            "tick": t,
            "witness_event_id": e.get("witness_event_id", ""),
            "condition": e.get("condition", ""),
            "policy": e.get("translation_mode_used_for_emission", ""),
            "true_top1_phrase": e.get("true_top1_phrase", ""),
            "true_top1_family": e.get("true_top1_family", ""),
            "emitted_phrase": e.get("emitted_phrase", ""),
            "emitted_family": e.get("emitted_family", ""),
            "bot_action": e.get("bot_action", ""),
            "bot_source": e.get("bot_source", ""),
            "window_tick_count": len(win),
            "next_mean_gate": mean(r.get("gate_pressure") for r in win),
            "next_mean_release": mean(r.get("release_score") for r in win),
            "next_mean_occlusion": mean(r.get("occlusion_level") for r in win),
            "next_witness_count": sum(1 for r in win if str(r.get("witnesses", "")).strip()),
            "next_active_ops_counts": json.dumps(Counter(op for r in win for op in str(r.get("active_ops", "")).split()), sort_keys=True),
        }
        rec.update({f"next_{k}": v for k,v in op_indices(win).items()})
        rows.append(rec)
    return rows


def windowed_rows(run_name: str, tick_rows: List[Dict[str, Any]], events: List[Dict[str, Any]], total: int) -> List[Dict[str, Any]]:
    if total <= 0:
        ticks=[int(fnum(r.get("tick"), -1)) for r in tick_rows if fnum(r.get("tick"), -1) >= 0]
        total=max(ticks)+1 if ticks else 0
    windows=[]
    if total >= 3000:
        windows=[("formation_0_999",0,999),("middle_1000_1999",1000,1999),("late_2000_end",2000,total-1)]
    else:
        third=max(1, total//3)
        windows=[("early",0,third-1),("middle",third,2*third-1),("late",2*third,total-1)]
    out=[]
    for label,a,b in windows:
        trs=[r for r in tick_rows if a <= int(fnum(r.get("tick"), -1)) <= b]
        evs=[e for e in events if a <= int(fnum(e.get("tick"), -1)) <= b]
        out.append(summary_for(run_name, trs, evs, label))
    return out


def analyze(suite_dir: Path, after_window_ticks: int = 25, ticks_total: int = 0) -> Dict[str, Any]:
    suite_dir=Path(suite_dir).resolve()
    reports=suite_dir/"reports"
    reports.mkdir(parents=True, exist_ok=True)
    all_events=[]; all_topk=[]; all_bot=[]; summaries=[]; windows=[]; nexts=[]
    run_status=[]
    for rn in RUN_NAMES:
        rd=suite_dir/rn
        tick_rows=read_csv(rd/"tick_rows.csv")
        events=read_jsonl(rd/RAW_EVENT_JSONL)
        topk=read_jsonl(rd/TOPK_JSONL)
        bot=read_jsonl(rd/"bot_packets.jsonl")
        for e in events:
            e.setdefault("run_label", rn)
        for r in topk:
            r.setdefault("run_label", rn)
        for b in bot:
            b.setdefault("run_label", rn)
        all_events.extend(events); all_topk.extend(topk); all_bot.extend(bot)
        summaries.append(summary_for(rn, tick_rows, events, "whole"))
        windows.extend(windowed_rows(rn, tick_rows, events, ticks_total))
        nexts.extend(next_window_rows(rn, tick_rows, events, after_window_ticks))
        run_status.append({"run_label": rn, "ticks": len(tick_rows), "witnesses": len(events), "bot_packets": len(bot), "complete": bool((rd/"run_summary.json").exists() or (rd/"run_complete.json").exists())})
    write_csv(reports/"event_translation_log.csv", all_events)
    write_csv(reports/"topk_true_vs_emitted.csv", all_topk)
    write_csv(reports/"bot_interaction_log.csv", all_bot)
    write_csv(reports/"condition_summary.csv", summaries)
    write_csv(reports/"window_summary.csv", windows)
    write_csv(reports/"next_window_effects.csv", nexts)
    lines=[]
    lines.append("# Trace-conditioned deterministic bot comparison suite")
    lines.append("")
    lines.append("No warmup is excluded. The report includes whole-run and windowed summaries.")
    lines.append("")
    lines.append("## Runs")
    for rs in run_status:
        lines.append(f"- `{rs['run_label']}`: ticks={rs['ticks']}, witnesses={rs['witnesses']}, bot_packets={rs['bot_packets']}, complete={rs['complete']}")
    lines.append("")
    lines.append("## Primary question")
    lines.append("")
    lines.append("Does the current true fused intent trace carry usable control information when a deterministic external surface replies from it?")
    lines.append("")
    lines.append("## How to read")
    lines.append("")
    lines.append("Compare `bot_matched_trace` against `bot_lagged_trace` and `bot_yoked_replay`. Matched beating both is stronger than matched beating no-return alone, because it controls for phrase inventory and reply distribution.")
    lines.append("")
    lines.append("Generated CSVs: `condition_summary.csv`, `window_summary.csv`, `event_translation_log.csv`, `bot_interaction_log.csv`, `topk_true_vs_emitted.csv`, `next_window_effects.csv`.")
    (reports/"RESULTS.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return {"reports_dir": str(reports), "run_status": run_status, "condition_summary_rows": len(summaries), "event_rows": len(all_events)}


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--suite-dir", type=Path, required=True)
    ap.add_argument("--after-window-ticks", type=int, default=25)
    ap.add_argument("--ticks-total", type=int, default=0)
    ns=ap.parse_args()
    print(json.dumps(analyze(ns.suite_dir, ns.after_window_ticks, ns.ticks_total), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
