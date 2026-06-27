# VDM selector trace control suite

This package contains the selector-trace control runs for the sentence probe experiment.

Runs included:

- `runs/readable_semantic_reference`: readable sentence schedule reference.
- `runs/opaque_token_control`: same schedule with every word replaced by deterministic opaque token IDs.
- `runs/shuffled_words_control`: same schedule with the words inside each sentence deterministically shuffled.

All runs use:

- fresh 1k VDM state per control run
- N=1000
- walkers=1200
- hops=2
- seed=20260627
- ticks=1400
- ticks 0-999 stable curriculum
- ticks 1000-1399 probe mixture
- bursted H5 save/reload continuation

Key reports:

- `reports/RESULTS.md`
- `reports/phase_summary_all_controls.csv`
- `reports/post1000_kind_summary_all_controls.csv`
