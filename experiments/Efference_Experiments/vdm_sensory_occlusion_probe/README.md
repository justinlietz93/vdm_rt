# VDM sensory occlusion actuator probe

Implements a UTE-side sensory occlusion actuator, separate from resolution aperture.

- `AP_CLOSE` must be held for more than one tick before occlusion increases.
- If `AP_CLOSE` pressure drops, the aperture reopens one notch per tick.
- Closed state dampens ordinary high-resolution receptor layers and sends a dark-field / occluded sensory signal instead of erasing the world.
- UTE still does not decide meaning; it applies the current receptor posture.

Primary smoke run:

- N=1000
- walkers=1200
- ratio=1.2
- ticks=300
- phases: stable readable -> noisy/missing-closure -> return stable
