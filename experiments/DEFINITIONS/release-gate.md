# Release gate definitions

The runner picks the lane with the strongest release-preparation balance:

```text id="oqh0z4"
strongest_lane = max(lane_hold + lane_release)
```

Then it computes:

```text id="z08a66"
release_score =
  lane_hold
  + lane_release
  - 0.35 * lane_inhibit
```

Then it adds immediate `COMMIT` or `RELEASE` pressure from the current tick:

```text id="s0y3pt"
gate_pressure =
  release_score
  + 0.10 * current_commit_or_release_touch_pressure
```

A witness appears when:

```text id="2hxjg2"
RELEASE or COMMIT is active
and gate_pressure crosses threshold
and cooldown has passed
```

After witness emission, the trace is partially consumed:

```text id="it1ghz"
lane_hold    *= 0.35
lane_release *= 0.20
lane_inhibit *= 0.70
```

That matters because witnesses are not free labels. They deplete the prepared lane.