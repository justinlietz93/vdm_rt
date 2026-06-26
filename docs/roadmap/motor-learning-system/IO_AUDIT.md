# IO Boundary Audit

Status: audit complete; P1 decoder removal not yet executed.

Authority: `docs/sources/neurobiology-upgrade/VDM_Hard_Implementation_Matrix_v0.2_motor_addendum.md`.

## Governing Result

The current `io/` directory is not one runtime category. The source authority
requires UTE to be receptor transduction and UTD to be actuator transduction,
while prohibiting live lexical, Markov, phrase-template, macro, and
release-time output authorship. The present live path violates that rule:
`runtime/helpers/speak.py` gates then calls the composer, and the composer
uses learned n-grams, phrase templates, and keyword fallback before sending a
`say` macro through UTD.

The audit also found that the current text stimulus mapping removes repeated
symbols before stimulation, and that inbound UTE messages are echoed through
the outbound UTD path. Those are separate receptor and boundary violations;
they must not be hidden by decoder removal.

## Classification

| Surface | Disposition | Evidence and required action |
| --- | --- | --- |
| `io/cognition/composer.py`, `io/cognition/speaker.py`, `io/lexicon/`, `io/lexicon/phrase_bank_min.json` | delete from the live runtime | They implement the forbidden lexical/n-gram/template/keyword output path. Preserve no live compatibility import. |
| `runtime/helpers/speak.py`, lexical state in `nexus.py`, and the lexicon save call in `runtime/loop/main.py` | delete or replace in the same batch | These callers make the prohibited decoder live. The release gate must not compose content. |
| `io/actuators/macros.py`, `runtime/emitters.py`, `runtime/helpers/macro_board.py`, and macro smoke output | delete from the live output path | The macro registry and its canned text emitters are not an actuator basis. Do not replace them with another text-authoring facade. |
| `io/actuators/thoughts.py` and thought smoke output | delete | It has no runtime producer beyond optional smoke material and is not required provenance logging. |
| `io/cognition/stimulus.py` and the text portion of `runtime/helpers/ingest.py` | port | A receptor boundary remains required, but the present unique-symbol mapping violates ordered, repetition-preserving receptor transduction. Replace it with bounded sequential slices. |
| `io/ute.py` | port | The receptor boundary remains required. Remove the synthetic wall-clock ticker and dashboard-inbox assumptions when defining the medium-specific receptor contract. |
| `io/utd.py` and `runtime/helpers/emission.py` | port | A future actuator boundary remains required, but the current macro board, text payloads, and input echo are not lawful actuator events. Status/provenance belongs in logging, not an output decoder. |
| `io/logging/rolling_jsonl.py` | keep | Bounded external audit logging is allowed when it does not feed cognition or stand in for reafference. |

## Static Reachability

The live decoder path is carried by these imports and calls:

- `nexus.py` imports UTE, UTD, the lexicon store, stimulus mapping, and composer.
- `runtime/helpers/speak.py` imports the composer and speaker scoring, then emits `say` through UTD.
- `runtime/helpers/ingest.py` updates lexical/n-gram state, applies the unique-symbol map, and echoes inbound messages through UTD.
- `runtime/loop/main.py` invokes ingestion, periodically saves the lexicon, and invokes autonomous speaking.
- `runtime/emitters.py`, `runtime/helpers/macro_board.py`, `runtime/helpers/emission.py`, and `runtime/helpers/smoke.py` retain macro and thought-output paths.

No `core/` module imports this family. `utils/logging_setup.py` is the only
non-decoder consumer of `io/logging/rolling_jsonl.py`.

## Removal Gate

The P1 removal patch must remove the live decoder import path and add guards
that reject lexical authoring under live runtime roots. It must prove:

1. No live output path imports the composer, speaker, lexicon, phrase bank, or macro emitter.
2. The runtime has no release-time sentence composition or `say` macro path.
3. Input receipt never causes outbound UTD emission.
4. The remaining UTE and UTD surfaces are documented as incomplete receptor and actuator ports, not compliant motor-learning implementations.

This audit does not claim that the future motor actuator, articulation trace,
or sequential receptor is implemented. Those remain roadmap work.
