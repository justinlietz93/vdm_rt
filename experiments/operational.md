# Operation definitions

This is the important table.

| Operation | Plain meaning                           | Trace update effect                             | How I interpret it                        |
| --------- | --------------------------------------- | ----------------------------------------------- | ----------------------------------------- |
| `SELECT`  | Choose a lane / bring a lane into play. | Adds modest `lane_hold`.                        | “This lane is being recruited.”           |
| `HOLD`    | Sustain the selected lane.              | Adds stronger `lane_hold`.                      | “Keep this motor state active.”           |
| `RELEASE` | Push toward outward emission.           | Adds `lane_release`.                            | “Open the mouth / let the act out.”       |
| `INHIBIT` | Suppress outward emission.              | Adds `lane_inhibit`.                            | “Do not release yet.”                     |
| `ADVANCE` | Move the trace forward.                 | Adds modest `lane_hold`.                        | “Continue this trace.”                    |
| `RETREAT` | Pull back from current trace.           | Multiplies `lane_hold` and `lane_release` down. | “Withdraw from acting.”                   |
| `SPLIT`   | Differentiate / branch a trace.         | Adds modest `lane_hold`.                        | “Separate possibilities or lanes.”        |
| `MERGE`   | Combine / integrate a trace.            | Adds modest `lane_hold`.                        | “Fold current structure into a lane.”     |
| `AMPLIFY` | Increase selected pressure.             | Adds modest `lane_hold`.                        | “Strengthen this lane’s posture.”         |
| `DAMP`    | Reduce prepared/release pressure.       | Multiplies `lane_hold` and `lane_release` down. | “Quiet the trace.”                        |
| `COMPARE` | Evaluate relation or mismatch.          | Adds modest `lane_hold`.                        | “Hold this lane while checking relation.” |
| `CORRECT` | Adjustment / repair pressure.           | Adds `lane_correct`.                            | “Something needs adjustment.”             |
| `COMMIT`  | Finalize / push toward act.             | Adds `lane_release`.                            | “This lane is ready to emit.”             |
| `ABORT`   | Cancel prepared action.                 | Multiplies `lane_hold` and `lane_release` down. | “Stop this release path.”                 |
