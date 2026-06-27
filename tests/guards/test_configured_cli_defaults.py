from __future__ import annotations

from vdm_rt.cli.args import make_parser
from vdm_rt.config import config_bool, config_float, config_int, config_str


def test_cli_defaults_come_from_config_files() -> None:
    args = make_parser().parse_args([])

    assert args.neurons == config_int("launch.neurons", 1000)
    assert args.k == config_int("launch.k", 12)
    assert args.hz == config_int("launch.hz", 10)
    assert args.domain == config_str("launch.domain", "biology_consciousness")
    assert args.use_time_dynamics == config_bool("launch.use_time_dynamics", True)
    assert args.log_every == config_int("launch.log_every", 1)
    assert args.status_interval == config_int("launch.status_interval", 1)

    assert args.threshold == config_float("sparse_connectome.threshold", 0.15)
    assert args.lambda_omega == config_float("sparse_connectome.lambda_omega", 0.1)
    assert args.candidates == config_int("sparse_connectome.candidates", 64)
    assert args.walkers == config_int("sparse_connectome.traversal_walkers", 256)
    assert args.hops == config_int("sparse_connectome.traversal_hops", 3)
    assert args.bundle_size == config_int("sparse_connectome.bundle_size", 3)
    assert args.prune_factor == config_float("sparse_connectome.prune_factor", 0.10)

    assert args.stim_amp == config_float("stimulus.amp", 0.05)
    assert args.stim_decay == config_float("stimulus.decay", 0.90)

    assert args.b1_z == config_float("b1.z", 1.0)
    assert args.b1_hysteresis == config_float("b1.hysteresis", 1.0)
    assert args.b1_cooldown_ticks == config_int("b1.cooldown_ticks", 10)
    assert args.b1_half_life_ticks == config_int("b1.half_life_ticks", 50)

    assert args.bus_capacity == config_int("bus.capacity", 65536)
    assert args.bus_drain == config_int("bus.drain", 2048)
    assert args.r_attach == config_float("adc.r_attach", 0.25)
    assert args.ttl_init == config_int("adc.ttl_init", 120)
    assert args.split_patience == config_int("adc.split_patience", 6)

    assert args.checkpoint_every == config_int("persistence.checkpoint_every", 0)
    assert args.checkpoint_keep == config_int("persistence.checkpoint_keep", 5)
    assert args.checkpoint_format == config_str("persistence.checkpoint_format", "h5")
