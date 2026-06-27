# Selector-trace implementation note

The previous diagnostic mouth used named actuator pools such as `LATCH`, `STABLE`, and `BOUNDARY`.

This runner replaces that with a selector manifold:

- operation pools: `SELECT`, `HOLD`, `RELEASE`, `INHIBIT`, `ADVANCE`, `RETREAT`, `SPLIT`, `MERGE`, `AMPLIFY`, `DAMP`, `COMPARE`, `CORRECT`, `COMMIT`, `ABORT`
- anonymous lanes: `L0` through `L7`

Void-walker node announcements drive pool energy. Coactive operation + lane pressure updates the private articulation trace. The trace is logged every tick. UTD emits only a compact witness when a lane accumulates enough hold/release pressure. UTE receives only the witness consequence when reafference is enabled.

The private trace is not emitted as output and is not fed back as sensory input.
