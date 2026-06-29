# Core Sensorimotor Module (core/sensorimotor/)

A hardware-agnostic matrix driven purely by the timing and spatial distribution of neural spikes.

* efference/: Manages outbound motor intentions.
* basis.py / trace.py: Space layout and historical log of output neuron groups.
   * observer.py: Passive diagnostic tracker that logs motor profiles without altering behavior.
* reafference/: Explicit software tracking layer for closed-loop analysis.
* loop_basis.py / loop_trace.py / observation.py: Measures time delays, cross-correlations, and internal state echoes caused by self-generated movement.
* afference/: Processes incoming input arrays.
* basis.py / trace.py: Unyielding entry points and logs for incoming neural indices.
   * sensorimotor_aperture.py: Non-semantic attention gate (thalamic gating). It attenuates or occludes input volume to shield the core from noise based on total network activity.
   * preprocessing/: Handles biological-grade contrast sharpening (lateral_inhibition.py) and scaling normalization (sensory_adaptation.py).

Refer to documentation for more: 
- [IO_PLAN.md](/io/IO_PLAN.md)
- [glossary.md](/docs/pages/architecture/sensorimotor_loop/glossary.md)
- [vdm_sensorimotor_loop.png](/docs/pages/architecture/sensorimotor_loop/vdm_sensorimotor_loop.png)
- [motor-learning-system.md](/docs/pages/architecture/motor-learning-system.md)