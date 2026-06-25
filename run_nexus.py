"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles. Commercial use requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""

from .nexus import Nexus, make_parser
import time, os

def main():
    ts = time.strftime('%Y%m%d_%H%M%S')
    default_run_dir = os.path.join('runs', ts)
    args = make_parser().parse_args()

    # Resolve load_engram to an actual checkpoint file and adopt its folder as run_dir when --run-dir is omitted.
    load_path = getattr(args, 'load_engram', None)

    def _resolve_latest_ckpt_in_dir(d: str):
        try:
            best = None
            best_step = -1
            best_ext = ""
            for fn in os.listdir(d):
                if not fn.startswith("state_"):
                    continue
                if not (fn.endswith(".h5") or fn.endswith(".npz")):
                    continue
                ext = ".h5" if fn.endswith(".h5") else ".npz"
                step_str = fn[6:-len(ext)] if len(ext) > 0 else fn[6:]
                try:
                    s = int(step_str)
                    # Prefer higher step; on tie prefer .h5
                    if (s > best_step) or (s == best_step and ext == ".h5" and best_ext == ".npz"):
                        best = fn
                        best_step = s
                        best_ext = ext
                except Exception:
                    continue
            return os.path.join(d, best) if best else None
        except Exception:
            return None

    # Normalize load_path (allow directory to mean "latest checkpoint in that dir")
    if load_path:
        p = str(load_path)
        if os.path.isdir(p):
            resolved = _resolve_latest_ckpt_in_dir(p)
            load_path = resolved if resolved else None
        else:
            load_path = p

    # Adopt bundle folder for run_dir if not explicitly set
    run_dir = getattr(args, 'run_dir', None)
    if not run_dir:
        if load_path and os.path.exists(load_path):
            # If a file path, adopt its parent; if previously a dir, we already kept it above
            run_dir = os.path.dirname(load_path)
        else:
            run_dir = default_run_dir

    nx = Nexus(run_dir=run_dir,
               N=args.neurons, k=args.k, hz=args.hz, domain=args.domain,
               use_time_dynamics=args.use_time_dynamics,
               log_every=args.log_every,
               checkpoint_every=args.checkpoint_every, seed=args.seed,
               threshold=args.threshold,
               lambda_omega=args.lambda_omega,
               candidates=args.candidates,
               walkers=args.walkers,
               hops=args.hops,
               status_interval=args.status_interval,
               bundle_size=args.bundle_size,
               prune_factor=args.prune_factor,
               # Checkpoint retention / format (format optional)
               checkpoint_format=args.checkpoint_format,
               checkpoint_keep=args.checkpoint_keep,
               # Text→connectome stimulation (symbol→group)
               stim_group_size=args.stim_group_size,
               stim_amp=args.stim_amp,
               stim_decay=args.stim_decay,
               stim_max_symbols=args.stim_max_symbols,
               # Self-speak / topology spike detection
               speak_auto=args.speak_auto,
               speak_z=args.speak_z,
               speak_hysteresis=args.speak_hysteresis,
               speak_cooldown_ticks=args.speak_cooldown_ticks,
               speak_valence_thresh=args.speak_valence_thresh,
               b1_half_life_ticks=args.b1_half_life_ticks,
               # Announcement bus / ADC tuning
               bus_capacity=args.bus_capacity,
               bus_drain=args.bus_drain,
               r_attach=args.r_attach,
               ttl_init=args.ttl_init,
               split_patience=args.split_patience,
               # Engram loader (forward normalized path into Nexus)
               load_engram_path=load_path,
               # Optional embedded control server (default off)
               start_control_server=args.control_server)
    nx.run(duration_s=args.duration)

if __name__ == '__main__':
    main()
