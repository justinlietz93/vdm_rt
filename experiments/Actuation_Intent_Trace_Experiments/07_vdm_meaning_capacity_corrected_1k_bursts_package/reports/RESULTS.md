# VDM Meaning-Capacity Corrected 1k Bursted Suite

Corrected run discipline: N=1000, walkers=1200, walker:neuron ratio=1.2, 300-tick burst segments, fresh state per run, H5 save/reload signature check after every burst, selector-trace state preserved across bursts.

Settings: seed=20260627, hops=2, release_threshold=1.15, release_cooldown=8. Baseline phases use 1000 ticks; post-baseline probes use 800 ticks.

## Completed runs

- `category_formation/baseline_then_novel`: ticks=1800, witnesses=97, rate=0.0539, mean_gate=0.8290, mean_release=0.6489
- `category_formation/no_baseline_test`: ticks=1800, witnesses=71, rate=0.0394, mean_gate=0.7899, mean_release=0.5951
- `category_formation/facts_then_questions`: ticks=1800, witnesses=6, rate=0.0033, mean_gate=0.4980, mean_release=0.4086
- `category_formation/multilingual_random`: ticks=1800, witnesses=50, rate=0.0278, mean_gate=0.6778, mean_release=0.5196
- `hierarchy_ordering/baseline_then_novel`: ticks=1800, witnesses=3, rate=0.0017, mean_gate=0.4220, mean_release=0.3268
- `hierarchy_ordering/no_baseline_test`: ticks=1800, witnesses=2, rate=0.0011, mean_gate=0.3673, mean_release=0.2763
- `hierarchy_ordering/facts_then_questions`: ticks=1800, witnesses=15, rate=0.0083, mean_gate=0.5195, mean_release=0.3893
- `hierarchy_ordering/multilingual_random`: ticks=1800, witnesses=66, rate=0.0367, mean_gate=0.7668, mean_release=0.6116
- `missing_closure_analogy/baseline_then_novel`: ticks=1800, witnesses=23, rate=0.0128, mean_gate=0.4015, mean_release=0.2938
- `missing_closure_analogy/no_baseline_test`: ticks=1800, witnesses=10, rate=0.0056, mean_gate=0.3708, mean_release=0.2755
- `missing_closure_analogy/facts_then_questions`: ticks=1800, witnesses=19, rate=0.0106, mean_gate=0.6474, mean_release=0.5501
- `missing_closure_analogy/multilingual_random`: ticks=1800, witnesses=95, rate=0.0528, mean_gate=0.8666, mean_release=0.7158
- `cross_domain_mapping/baseline_then_novel`: ticks=1800, witnesses=22, rate=0.0122, mean_gate=0.4913, mean_release=0.4094
- `cross_domain_mapping/no_baseline_test`: ticks=1800, witnesses=18, rate=0.0100, mean_gate=0.5245, mean_release=0.4455
- `cross_domain_mapping/facts_then_questions`: ticks=1800, witnesses=26, rate=0.0144, mean_gate=0.5853, mean_release=0.4961
- `cross_domain_mapping/multilingual_random`: ticks=1800, witnesses=33, rate=0.0183, mean_gate=0.6303, mean_release=0.5459

## Aggregate by branch

- `category_formation`: witnesses=224/7200 rate=0.0311, mean_gate=0.6987, mean_release=0.5430
- `cross_domain_mapping`: witnesses=99/7200 rate=0.0138, mean_gate=0.5578, mean_release=0.4742
- `hierarchy_ordering`: witnesses=86/7200 rate=0.0119, mean_gate=0.5189, mean_release=0.4010
- `missing_closure_analogy`: witnesses=147/7200 rate=0.0204, mean_gate=0.5716, mean_release=0.4588

## Aggregate by run kind

- `baseline_then_novel`: witnesses=145/7200 rate=0.0201, mean_gate=0.5359, mean_release=0.4197
- `facts_then_questions`: witnesses=66/7200 rate=0.0092, mean_gate=0.5626, mean_release=0.4610
- `multilingual_random`: witnesses=244/7200 rate=0.0339, mean_gate=0.7354, mean_release=0.5982
- `no_baseline_test`: witnesses=101/7200 rate=0.0140, mean_gate=0.5131, mean_release=0.3981

## File layout

Each run folder contains `tick_rows.csv`, `trace_log.jsonl`, `ute_input_stream.jsonl`, `utd_events.jsonl`, `trace_features.csv`, `summary_by_phase_kind.csv`, `first_witness_by_input.csv`, H5 checkpoints, and `burst_manifest.json`.
