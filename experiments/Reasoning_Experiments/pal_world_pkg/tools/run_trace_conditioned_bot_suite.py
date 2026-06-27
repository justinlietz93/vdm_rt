#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

REQUIRED_MODULES = ["numpy", "h5py"]


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_from_root(root: Path, p: Path) -> Path:
    return p if p.is_absolute() else (root / p)


def check_dependencies(root: Path) -> None:
    missing = [m for m in REQUIRED_MODULES if importlib.util.find_spec(m) is None]
    if not missing:
        return
    req = root / "requirements.txt"
    msg = {
        "error": "missing Python dependencies",
        "missing": missing,
        "python_executable": sys.executable,
        "fix": [
            f"{sys.executable} -m pip install -r {req}",
            "or run: ./setup_env.sh && venv/bin/python tools/run_whole_trace_conditioned_bot_suite.py --reset --run",
        ],
    }
    print(json.dumps(msg, indent=2), file=sys.stderr)
    raise SystemExit(2)


def build_args(ns: argparse.Namespace, root: Path) -> SimpleNamespace:
    suite_dir = resolve_from_root(root, ns.suite_dir).resolve()
    repo = resolve_from_root(root, ns.repo).resolve()
    intent_index_dir = resolve_from_root(root, ns.intent_index_dir).resolve()
    return SimpleNamespace(
        suite_dir=suite_dir,
        repo=repo,
        intent_index_dir=intent_index_dir,
        reset=bool(ns.reset),
        ticks_total=int(ns.ticks_total),
        switch_tick=int(ns.switch_tick),
        burst_ticks=int(ns.ticks_total),
        input_schedule=str(ns.input_schedule),
        neurons=int(ns.neurons),
        walkers=int(ns.walkers),
        k=int(ns.k),
        hops=int(ns.hops),
        candidates=int(ns.candidates),
        threshold=float(ns.threshold),
        lambda_omega=float(ns.lambda_omega),
        domain_modulation=float(ns.domain_modulation),
        hz=float(ns.hz),
        seed=int(ns.seed),
        stim_amp=float(ns.stim_amp),
        reafferent_gain=float(ns.reafferent_gain),
        feature_group_size=int(ns.feature_group_size),
        selector_group_size=int(ns.selector_group_size),
        release_threshold=float(ns.release_threshold),
        current_op_min=int(ns.current_op_min),
        current_lane_min=int(ns.current_lane_min),
        selector_decay=float(ns.selector_decay),
        release_cooldown=int(ns.release_cooldown),
        aperture_group_size=int(ns.aperture_group_size),
        aperture_current_min=int(ns.aperture_current_min),
        close_hold_ticks=int(ns.close_hold_ticks),
        bus_capacity=int(ns.bus_capacity),
        bus_drain=int(ns.bus_drain),
        intent_retain=float(ns.intent_retain),
        intent_trigger_mix=float(ns.intent_trigger_mix),
        intent_top_k=int(ns.intent_top_k),
        after_window_ticks=int(ns.after_window_ticks),
        bot_event_lag=int(ns.bot_event_lag),
        live_terminal=not bool(ns.no_live),
        tick_print_stride=int(ns.tick_print_stride),
        live_topn=int(ns.live_topn),
    )


def main() -> int:
    root = package_root()
    ap = argparse.ArgumentParser(
        description="Run the trace-conditioned deterministic bot comparison suite as whole runs."
    )
    ap.add_argument("--run", action="store_true", help="run the graph-bot comparison runs and analyze")
    ap.add_argument("--status", action="store_true", help="print suite status")
    ap.add_argument("--analyze", action="store_true", help="analyze existing suite")
    ap.add_argument("--reset", action="store_true", help="delete/rebuild the suite directory before running")
    ap.add_argument("--suite-dir", type=Path, default=Path("runs/trace_conditioned_bot_3000"))
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--intent-index-dir", type=Path, default=Path("index"))

    ap.add_argument("--ticks-total", type=int, default=3000)
    ap.add_argument("--switch-tick", type=int, default=2000)
    ap.add_argument("--input-schedule", choices=["single", "cycle"], default="single")
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
    ap.add_argument("--no-live", action="store_true", help="disable live terminal telemetry")
    ap.add_argument("--tick-print-stride", type=int, default=50, help="print every N ticks; witness ticks always print")
    ap.add_argument("--live-topn", type=int, default=3, help="number of true/emitted trace candidates printed at each witness")
    ns = ap.parse_args()

    if not (ns.run or ns.status or ns.analyze):
        ns.run = True

    check_dependencies(root)
    sys.path.insert(0, str(root / "tools"))
    import run_trace_conditioned_bot_suite_core as clean
    import analyze_trace_conditioned_bot_results as bot_analysis

    args = build_args(ns, root)
    cfg = clean.ensure_suite_config(args)

    if int(cfg.get("burst_ticks", -1)) != int(cfg.get("ticks_total", -2)):
        print(json.dumps({
            "error": "existing suite_config.json is configured for burst mode",
            "suite_dir": str(args.suite_dir),
            "configured_burst_ticks": cfg.get("burst_ticks"),
            "configured_ticks_total": cfg.get("ticks_total"),
            "fix": "rerun with --reset or choose a fresh --suite-dir",
        }, indent=2), file=sys.stderr)
        return 2

    if ns.status:
        print(json.dumps(clean.suite_status(args.suite_dir, cfg), indent=2))
        return 0

    if ns.run:
        print(json.dumps({
            "mode": "trace_conditioned_bot_comparison_suite",
            "suite_dir": str(args.suite_dir),
            "ticks_total_per_run": cfg["ticks_total"],
            "switch_tick": cfg["switch_tick"],
            "runs": clean.RUN_NAMES,
            "note": "Each run is executed as one continuous run. Default run set: graph matched, graph lagged, graph yoked replay.",
        }, indent=2), flush=True)
        for run_name in clean.RUN_NAMES:
            print(f"\n=== full run: {run_name} ===\n", flush=True)
            clean.run_one_burst(args, cfg, run_name)
        print("\n=== analysis ===\n", flush=True)
        legacy_report = clean.analyze_suite(args, cfg)
        bot_report = bot_analysis.analyze(args.suite_dir, after_window_ticks=int(cfg.get("after_window_ticks", 25)), ticks_total=int(cfg.get("ticks_total", 0)))
        print(json.dumps({"legacy_report": legacy_report, "bot_report": bot_report}, indent=2))
        return 0

    if ns.analyze:
        legacy_report = clean.analyze_suite(args, cfg)
        bot_report = bot_analysis.analyze(args.suite_dir, after_window_ticks=int(cfg.get("after_window_ticks", 25)), ticks_total=int(cfg.get("ticks_total", 0)))
        print(json.dumps({"legacy_report": legacy_report, "bot_report": bot_report}, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
