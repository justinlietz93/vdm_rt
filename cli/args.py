"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles.

Commercial use of proprietary VDM code requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""
from __future__ import annotations

"""
CLI argument parser for the VDM runtime.

Behavior:
- Mirrors the legacy make_parser() previously defined in vdm_rt/nexus.py exactly.
- Kept here to reduce nexus.py size and improve separation of concerns.
"""

import argparse

from vdm_rt.config import config_bool, config_float, config_int, config_str


def _optional_str(key: str) -> str | None:
    value = config_str(key, "").strip()
    return value or None


def _optional_positive_int(key: str) -> int | None:
    value = config_int(key, 0)
    return value if value > 0 else None


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument('--neurons', type=int, default=config_int("launch.neurons", 1000))
    p.add_argument('--k', type=int, default=config_int("launch.k", 12))
    p.add_argument('--hz', type=int, default=config_int("launch.hz", 10))
    p.add_argument('--domain', type=str, default=config_str("launch.domain", "biology_consciousness"))
    p.add_argument('--log-every', type=int, default=config_int("launch.log_every", 1))
    p.add_argument('--checkpoint-every', type=int, default=config_int("persistence.checkpoint_every", 0))
    p.add_argument('--checkpoint-keep', type=int, default=config_int("persistence.checkpoint_keep", 5))
    p.add_argument('--checkpoint-format', dest='checkpoint_format', type=str, default=config_str("persistence.checkpoint_format", "h5"))
    p.add_argument('--duration', type=int, default=_optional_positive_int("launch.duration_seconds"))
    p.add_argument('--use-time-dynamics', dest='use_time_dynamics', action='store_true')
    p.add_argument('--no-time-dynamics', dest='use_time_dynamics', action='store_false')
    p.set_defaults(use_time_dynamics=config_bool("launch.use_time_dynamics", True))
    p.add_argument('--seed', type=int, default=config_int("launch.seed", 0))

    p.add_argument('--threshold', type=float, default=config_float("sparse_connectome.threshold", 0.15))
    p.add_argument('--lambda-omega', dest='lambda_omega', type=float, default=config_float("sparse_connectome.lambda_omega", 0.1))
    p.add_argument('--candidates', type=int, default=config_int("sparse_connectome.candidates", 64))
    p.add_argument('--walkers', type=int, default=config_int("sparse_connectome.traversal_walkers", 256))
    p.add_argument('--hops', type=int, default=config_int("sparse_connectome.traversal_hops", 3))
    p.add_argument('--status-interval', dest='status_interval', type=int, default=config_int("launch.status_interval", 1))
    p.add_argument('--bundle-size', dest='bundle_size', type=int, default=config_int("sparse_connectome.bundle_size", 3))
    p.add_argument('--prune-factor', dest='prune_factor', type=float, default=config_float("sparse_connectome.prune_factor", 0.10))

    # External receptor stimulation amplitude/decay. Receptor-node selection is not done here.
    p.add_argument('--stim-amp', dest='stim_amp', type=float, default=config_float("stimulus.amp", 0.05))
    p.add_argument('--stim-decay', dest='stim_decay', type=float, default=config_float("stimulus.decay", 0.90))

    # Topology-spike detection (void-native, no output authorship)
    p.add_argument('--b1-z', dest='b1_z', type=float, default=config_float("b1.z", 1.0))
    p.add_argument('--b1-hysteresis', dest='b1_hysteresis', type=float, default=config_float("b1.hysteresis", 1.0))
    p.add_argument('--b1-cooldown-ticks', dest='b1_cooldown_ticks', type=int, default=config_int("b1.cooldown_ticks", 10))
    p.add_argument('--b1-half-life-ticks', dest='b1_half_life_ticks', type=int, default=config_int("b1.half_life_ticks", 50))

    # Announcement bus / ADC tuning
    p.add_argument('--bus-capacity', dest='bus_capacity', type=int, default=config_int("bus.capacity", 65536))
    p.add_argument('--bus-drain', dest='bus_drain', type=int, default=config_int("bus.drain", 2048))
    p.add_argument('--r-attach', dest='r_attach', type=float, default=config_float("adc.r_attach", 0.25))
    p.add_argument('--ttl-init', dest='ttl_init', type=int, default=config_int("adc.ttl_init", 120))
    p.add_argument('--split-patience', dest='split_patience', type=int, default=config_int("adc.split_patience", 6))

    # Engram loader (optional)
    p.add_argument('--load-engram', dest='load_engram', type=str, default=_optional_str("persistence.load_engram"))
    # Optional embedded control server (disabled by default to avoid duplicate UI)
    p.add_argument('--control-server', dest='control_server', action='store_true')
    p.add_argument('--no-control-server', dest='control_server', action='store_false')
    p.set_defaults(control_server=config_bool("control.server_enabled", False))
    # Allow explicit reuse of an existing run directory (resume), otherwise a new timestamp dir is used
    p.add_argument('--run-dir', dest='run_dir', type=str, default=_optional_str("launch.run_dir"))

    return p


__all__ = ["make_parser"]
