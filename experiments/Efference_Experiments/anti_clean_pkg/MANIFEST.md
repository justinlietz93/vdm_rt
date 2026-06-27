# Manifest

Package: `vdm_anti_reafference_whole_three_run_package.zip`

## Main entrypoints

```text
setup_env.sh
run_whole_1500.sh
analyze_whole_1500.sh
tools/run_whole_anti_reafference_suite.py
```

## Core runner files

```text
tools/run_whole_anti_reafference_suite.py      whole-run wrapper; intended entrypoint
tools/run_clean_anti_reafference_suite.py      underlying experiment/reporting runner
tools/base_sensory_occlusion_runner.py         imported VDM harness support
tools/intention_trace_translator.py            2048 intention translator support
```

## Included runtime/index snapshot

```text
codebase/vdm_rt-main/
index/utterance_bank_2048.jsonl
index/utterance_index_2048.npz
index/index_schema_2048.json
index/family_axis_summary.csv
index/curation_audit.json
```

## Dependencies

```text
requirements.txt
```

Required Python modules:

```text
numpy
networkx
scipy
h5py
```

## Default experiment

```text
normal_control:   1500 ticks aligned fused
inverted_control: 1500 ticks signed-centered anti_vector
switch_test:      0-999 aligned fused, 1000-1499 signed-centered anti_vector
```
