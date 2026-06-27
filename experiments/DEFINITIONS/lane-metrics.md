# Main per-lane metrics

Each lane has these values:

| Metric             | Plain meaning                                    | In runner terms                                                                                    | Effect                                                                                              |
| ------------------ | ------------------------------------------------ | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `lane_energy[Lx]`  | General actuator contact strength for lane `Lx`. | Increases when walker observations touch that lane’s neuron pool. Decays each tick.                | Shows which lanes are being recruited by VDM activity.                                              |
| `lane_hold[Lx]`    | Prepared / retained motor pressure.              | Increases from `SELECT`, `ADVANCE`, `SPLIT`, `MERGE`, `AMPLIFY`, `COMPARE`, and especially `HOLD`. | Makes a lane more eligible for later release.                                                       |
| `lane_inhibit[Lx]` | Suppression / containment pressure.              | Increases from `INHIBIT`.                                                                          | Reduces release likelihood. High inhibit means “pressure exists, but mouth stays closed.”           |
| `lane_release[Lx]` | Release / commit pressure.                       | Increases from `RELEASE` and `COMMIT`.                                                             | Pushes a lane toward witness emission.                                                              |
| `lane_correct[Lx]` | Correction / adjustment pressure.                | Increases from `CORRECT`.                                                                          | Marks corrective posture, but currently does not directly force release. Useful as a trace readout. |