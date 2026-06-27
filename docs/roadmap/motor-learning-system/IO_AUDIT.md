# IO Boundary Audit

Status: P1 decoder removal executed; receptor/actuator rewrite not yet implemented.

Authority: `docs/roadmap/neurobiology-upgrade/VDM_Hard_Implementation_Matrix_v0.2_motor_addendum.md`.

## Governing Result

The `io/` directory is not one runtime category. The source authority
requires UTE to be receptor transduction and UTD to be actuator transduction,
while prohibiting live lexical, Markov, phrase-template, macro, and
release-time output authorship. The removed live path violated that rule:
`runtime/helpers/speak.py` gates then calls the composer, and the composer
uses learned n-grams, phrase templates, and keyword fallback before sending a
`say` macro through UTD.

The audit also found that the removed text stimulus mapping removed repeated
symbols before stimulation, and that inbound UTE messages are echoed through
the outbound UTD path. Those are separate receptor and boundary violations;
they must not be hidden by decoder removal.

## Classification

| Surface | Disposition | Evidence and required action |
| --- | --- | --- |
| `io/cognition/composer.py`, `io/cognition/speaker.py`, `io/lexicon/`, `io/lexicon/phrase_bank_min.json` | deleted from the live runtime | They implemented the forbidden lexical/n-gram/template/keyword output path. No live compatibility import is retained. |
| `runtime/helpers/speak.py`, lexical state in `nexus.py`, and the lexicon save call in `runtime/loop/main.py` | deleted or removed | These callers made the prohibited decoder live. The release gate no longer composes content. |
| `io/actuators/macros.py`, `runtime/emitters.py`, `runtime/helpers/macro_board.py`, and macro smoke output | deleted from the live output path | The macro registry and its canned text emitters were not an actuator basis. |
| `io/actuators/thoughts.py` and thought smoke output | deleted | It had no runtime producer beyond optional smoke material and was not required provenance logging. |
| `io/cognition/stimulus.py` and the text portion of `runtime/helpers/ingest.py` | deleted or disabled | The unique-symbol mapping is removed. `process_messages()` does not map text. It accepts only explicit receptor/stimulation node-index fields, which the loop can pass to `SparseConnectome.stimulate_indices()`, and it does not echo through UTD. |
| `io/ute.py` | boundary port only | UTE now exposes an explicit queue and no stdin, chat-inbox, or synthetic ticker source. |
| `io/utd.py` and `runtime/helpers/emission.py` | boundary port only | The status/text/macro emission helper is deleted. UTD has no text or macro API and records only explicit `utd_actuation` rows in `motor_traces.jsonl.zst`. |
| `io/logging/rolling_jsonl.py` | keep | Bounded external audit logging is allowed when it does not feed cognition or stand in for reafference. |

## Static Reachability

The removed decoder path was carried by these imports and calls:

- `nexus.py` imported UTE, UTD, the lexicon store, stimulus mapping, and composer.
- `runtime/helpers/speak.py` imported the composer and speaker scoring, then emitted `say` through UTD.
- `runtime/helpers/ingest.py` updated lexical/n-gram state, applied the unique-symbol map, and echoed inbound messages through UTD.
- `runtime/loop/main.py` invoked ingestion, periodically saved the lexicon, and invoked autonomous speaking.
- `runtime/emitters.py`, `runtime/helpers/macro_board.py`, `runtime/helpers/emission.py`, and `runtime/helpers/smoke.py` retained macro and thought-output paths.

No `core/` module imported this family. `utils/logging_setup.py` remains the
non-decoder consumer of `io/logging/rolling_jsonl.py`.

## Removal Gate

The P1 removal patch removes the live decoder import path and adds
`tests/guards/test_no_live_decoder_authorship.py`, which rejects lexical
authoring under live runtime roots. It proves:

1. No live output path imports the composer, speaker, lexicon, phrase bank, or macro emitter.
2. The runtime has no release-time sentence composition or `say` macro path.
3. Input receipt never causes outbound UTD emission.
4. Explicit receptor-node indices can stimulate the connectome without restoring text mapping.
5. The remaining UTE and UTD surfaces are documented as incomplete receptor and actuator ports, not compliant motor-learning implementations.

This audit does not claim that the future motor actuator, articulation trace,
or sequential receptor is implemented. The live loop now records stimulation,
efferent observation-node summaries, and optional attached-actuator witness/UTD
handoffs into `motor_traces.jsonl.zst`; a default actuator implementation
remains roadmap work.
