"""Regression coverage for telemetry-fold tick boundaries."""

from __future__ import annotations

from types import SimpleNamespace

from vdm_rt.core.adc import ADC
from vdm_rt.core.announce import Observation
from vdm_rt.core.bus import AnnounceBus
from vdm_rt.runtime.telemetry import tick_fold


def test_tick_fold_does_not_reuse_observations_or_adc_metrics_after_zero_drain() -> None:
    nx = SimpleNamespace(
        bus=AnnounceBus(capacity=8),
        bus_drain=8,
        adc=ADC(),
        _evt_metrics=None,
    )
    first_observation = Observation(
        tick=1,
        kind="region_stat",
        nodes=[3, 4],
        w_mean=0.4,
        w_var=0.1,
        s_mean=0.2,
        coverage_id=2,
        domain_hint="telemetry-test",
    )
    nx.bus.publish(first_observation)

    tick_fold(nx, {}, {}, 0.0, step=1)

    assert nx._last_obs_batch == [first_observation]
    assert nx._last_adc_metrics["adc_territories"] == 1

    tick_fold(nx, {}, {}, 0.0, step=2)

    assert nx._last_obs_batch == []
    assert nx._last_adc_metrics == {}
