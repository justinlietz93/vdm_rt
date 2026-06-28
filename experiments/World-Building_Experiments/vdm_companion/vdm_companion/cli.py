"""
vdm_companion CLI.

  live           Tail an active run dir, push coax atoms to VDM, measure
                 orientation closed-loop. This is the real deployment.
  shadow         Replay a finished run dir with no sink: log every Logic-gate
                 decision and the coax atom that would have been emitted, with
                 full posture context. Validates read/posture/logic/coax.
  validate-metric  Compute the orientation metric on the run's own real atoms,
                 proving the instrument yields sensible aperture/witness/gate/
                 drift numbers on real logs before any live loop is run.
"""
from __future__ import annotations
import argparse
import json
from statistics import mean

from .config import CompanionConfig
from .channels import (ReplayTraceSource, FileTailTraceSource,
                       QueueFileAfferentSink, SocketAfferentSink, AfferentSink)
from .runtime import CompanionRuntime
from .instrument import measure_orientation, summarize


def _make_sink(spec: str) -> AfferentSink:
    if spec.startswith("queue:"):
        return QueueFileAfferentSink(spec[len("queue:"):])
    if spec.startswith("socket:"):
        _, host, port = spec.split(":")
        return SocketAfferentSink(host=host, port=int(port))
    raise SystemExit(f"unknown sink spec: {spec} (use queue:PATH or socket:host:port)")


def cmd_live(args):
    cfg = CompanionConfig(seed=args.seed)
    src = FileTailTraceSource(args.run_dir)
    sink = _make_sink(args.sink)

    def on_emit(atom, tick):
        print(json.dumps({"tick": tick, "emit": atom.arm, "atom": atom.text}, ensure_ascii=False))

    rt = CompanionRuntime(src, sink, cfg, closed_loop=True, on_emit=on_emit)
    res = rt.run(max_ticks=args.max_ticks)
    out = res.to_dict()
    sink.close()
    print(json.dumps(out, indent=2, ensure_ascii=False))


def cmd_shadow(args):
    cfg = CompanionConfig(seed=args.seed)
    src = ReplayTraceSource(args.run_dir)
    rt = CompanionRuntime(src, sink=None, cfg=cfg, closed_loop=False)
    res = rt.run()
    decs = res.decisions
    emits = [d for d in decs if d.emitted]
    print(f"witness decision points : {len(decs)}")
    print(f"receptive               : {sum(d.receptive for d in decs)}")
    print(f"would emit               : {len(emits)}")
    if decs:
        print(f"posture score range      : "
              f"{min(d.posture_score for d in decs):+.3f} .. {max(d.posture_score for d in decs):+.3f}")
    print("\nfirst emit decisions:")
    for d in emits[: args.show]:
        print(json.dumps({
            "witness_tick": d.witness_tick, "topic": d.topic[:48],
            "score": d.posture_score, "dominant": d.dominant_axis,
            "arm": d.arm, "atom": d.atom,
        }, ensure_ascii=False))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(res.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\nwrote {args.json_out}")


def cmd_validate_metric(args):
    """Drive the orientation metric over the real atoms in a finished run."""
    cfg = CompanionConfig(seed=args.seed)
    src = ReplayTraceSource(args.run_dir)
    rows = list(src.ticks())
    baseline = mean(float(r.get(cfg.col_gate, 0) or 0) for r in rows)

    # first appearance tick of each distinct atom
    first: dict[str, int] = {}
    order: list[str] = []
    for r in rows:
        a = r.get(cfg.col_atom, "")
        if a and a not in first:
            first[a] = int(float(r[cfg.col_tick]))
            order.append(a)

    # alternate arm labels just to exercise the contrast machinery on real atoms
    orientations = []
    for i, a in enumerate(order):
        arm = "presence" if i % 2 == 0 else "null"
        orientations.append(
            measure_orientation(src, rows, a, arm, first[a], baseline, cfg)
        )
    rep = summarize(orientations)
    print(json.dumps({
        "note": "metric validation on REAL atoms (arms assigned alternately, "
                "not real coax arms) -- proves the instrument computes on real logs",
        "baseline_gate": round(baseline, 4),
        "per_atom": [{
            "atom": o.atom[:48], "arm": o.arm, "n_ticks": o.n_ticks,
            "aperture_net": o.aperture_net, "open": o.aperture_open,
            "narrow": o.aperture_narrow, "witness_lock": o.witness_lock,
            "gate_response": o.gate_response, "drift": o.drift,
        } for o in orientations],
        "report": rep.to_dict()["contrasts"],
    }, indent=2, ensure_ascii=False))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vdm_companion")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("live", help="tail an active run and coax closed-loop")
    p.add_argument("run_dir")
    p.add_argument("--sink", required=True, help="queue:PATH or socket:host:port")
    p.add_argument("--max-ticks", type=int, default=None)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_live)

    p = sub.add_parser("shadow", help="replay a finished run, log gate decisions")
    p.add_argument("run_dir")
    p.add_argument("--show", type=int, default=8)
    p.add_argument("--json-out", default=None)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_shadow)

    p = sub.add_parser("validate-metric", help="run orientation metric on real atoms")
    p.add_argument("run_dir")
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_validate_metric)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
