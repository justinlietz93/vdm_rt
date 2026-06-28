"""
Three-track orchestrator.

  track1  baseline                          0 .. T
  track2  shuffled handles whole run        0 .. T
  track3  baseline 0 .. S, then shuffled    S .. T   (via engine resume)

Track 3 uses your engine's resume_h5 mechanism (present in run_config.json): run
the baseline to the switch tick S, snapshot, then resume from that exact state
with the shuffled handle map. That makes the only difference at S the relocation,
holding history constant -- the within-subject control.

ONE integration point: run_one(). It must invoke your selector-trace runner with
a config and (for the shuffled arms) the permuted handle map. The config fields
mirror the run_config.json shipped in your runs. Confirm the runner CLI flag for
the handle map / permutation; everything else is built here.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

from .permute_handles import make_permutation


@dataclass
class RunConfig:
    schedule: str
    run_dir: str
    start_tick: int
    end_tick: int
    neurons: int = 1000
    walkers: int = 1200
    seed: int = 20260627
    k: int = 12
    hops: int = 2
    candidates: int = 64
    threshold: float = 0.05
    lambda_omega: float = 0.1
    hz: float = 10.0
    domain_modulation: float = 1.15625
    stim_group_size: int = 4
    stim_max_units: int = 10
    resume_h5: Optional[str] = None
    handle_permutation: Optional[list] = None   # None = identity (baseline)

    def to_dict(self):
        return asdict(self)


def build_tracks(schedule: str, out_root: str, total_ticks: int = 1500,
                 switch_tick: int = 1000, neurons: int = 1000, seed: int = 20260627,
                 n_handles: int = 64, perm_seed: int = 20260627):
    """Return the list of RunConfig calls for all three tracks. Track 3 is two
    calls (baseline segment, then resumed shuffled segment)."""
    root = Path(out_root)
    perm = make_permutation(n_handles, perm_seed)

    t1 = RunConfig(schedule=schedule, run_dir=str(root / "track1_baseline"),
                   start_tick=0, end_tick=total_ticks, neurons=neurons, seed=seed)

    t2 = RunConfig(schedule=schedule, run_dir=str(root / "track2_full_shuffle"),
                   start_tick=0, end_tick=total_ticks, neurons=neurons, seed=seed,
                   handle_permutation=perm)

    t3a = RunConfig(schedule=schedule, run_dir=str(root / "track3_switch"),
                    start_tick=0, end_tick=switch_tick, neurons=neurons, seed=seed)
    # resume from the snapshot the baseline segment leaves, then shuffle
    t3b = RunConfig(schedule=schedule, run_dir=str(root / "track3_switch"),
                    start_tick=switch_tick, end_tick=total_ticks, neurons=neurons,
                    seed=seed, resume_h5=str(root / "track3_switch" / f"state_{switch_tick}.h5"),
                    handle_permutation=perm)

    return {"track1": [t1], "track2": [t2], "track3": [t3a, t3b], "permutation": perm}


def run_one(cfg: RunConfig, runner: str, repo: str, tools: str, dry_run: bool = True) -> int:
    """Invoke the selector-trace runner for one config segment.

    CONTRACT: adapt the argv below to your runner's actual CLI. The handle
    permutation is passed as a JSON file path via --handle-perm; if your runner
    takes it another way (env var, config field), change only this function."""
    Path(cfg.run_dir).mkdir(parents=True, exist_ok=True)
    cfg_path = Path(cfg.run_dir) / f"run_config_{cfg.start_tick}_{cfg.end_tick}.json"
    payload = cfg.to_dict()
    payload.update({"repo": repo, "tools": tools})
    cfg_path.write_text(json.dumps(payload, indent=2))

    argv = ["python", runner, "--config", str(cfg_path)]
    if cfg.handle_permutation is not None:
        perm_path = Path(cfg.run_dir) / f"handle_perm_{cfg.start_tick}.json"
        perm_path.write_text(json.dumps(cfg.handle_permutation))
        argv += ["--handle-perm", str(perm_path)]
    if cfg.resume_h5:
        argv += ["--resume", cfg.resume_h5]

    if dry_run:
        print("DRY RUN:", " ".join(argv))
        return 0
    return subprocess.call(argv)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schedule", required=True, help="path to the stimulus schedule jsonl")
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--runner", default="run_orthad_selector_trace.py")
    ap.add_argument("--repo", default="")
    ap.add_argument("--tools", default="")
    ap.add_argument("--total-ticks", type=int, default=1500)
    ap.add_argument("--switch-tick", type=int, default=1000)
    ap.add_argument("--neurons", type=int, default=1000)
    ap.add_argument("--n-handles", type=int, default=64)
    ap.add_argument("--seed", type=int, default=20260627)
    ap.add_argument("--execute", action="store_true", help="actually run (default is dry run)")
    a = ap.parse_args()

    tracks = build_tracks(a.schedule, a.out_root, a.total_ticks, a.switch_tick,
                          a.neurons, a.seed, a.n_handles, a.seed)
    Path(a.out_root).mkdir(parents=True, exist_ok=True)
    Path(a.out_root, "permutation.json").write_text(json.dumps(tracks["permutation"]))

    for name in ("track1", "track2", "track3"):
        for seg in tracks[name]:
            run_one(seg, a.runner, a.repo, a.tools, dry_run=not a.execute)
    print("\nafter the runs, analyze with:")
    print(f"  python -m intent_shuffle_probe.analyze "
          f"--track1 {a.out_root}/track1_baseline "
          f"--track2 {a.out_root}/track2_full_shuffle "
          f"--track3 {a.out_root}/track3_switch --switch-tick {a.switch_tick}")


if __name__ == "__main__":
    main()
