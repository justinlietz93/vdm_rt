# Definitions

<!-- TODO: Definitions are stale here and should be expanded with links to the code files each metric is defined at -->

| Metric | Role in the runtime | Current source |
| --- | --- | --- |
| `active_edges` | structural load / active synaptic edge count | events, dashboard, H5-derived analyses |
| `active_synapses` | structural activity proxy closely related to `active_edges` | events |
| `connectome_entropy` | graph-distribution entropy / structural disorder metric | events, dashboard |
| `vt_coverage` | traversal coverage fraction | events, dashboard |
| `vt_entropy` | traversal/topic entropy | events, dashboard |
| `b1_z` | boundary pulse / motor-gate proxy | events, dashboard, UTD `why` |
| `adc_territories` | active hierarchy/territory count | events, dashboard, H5 `adc_json` |
| `adc_boundaries` | boundary count in ADC summary | events |
| `cohesion_components` | topological integration/fragmentation state | events, UTD `why` |
| `sie_total_reward` | SIE-v1 aggregate reward-like signal | events |
| `sie_valence_01` | normalized SIE-v1 valence | events, UTD `why` |
| `sie_td_error` | SIE-v1 TD-like error channel | events |
| `sie_v2_reward_mean` | SIE-v2 reward mean | events |
| `sie_v2_valence_01` | normalized SIE-v2 valence | events, dashboard, UTD `why` |
| `a_mean` | mean `a`/alpha-like field term | events |
| `omega_mean` | mean omega-like field term | events |
| `homeostasis_pruned` | number pruned in current step | events |
| `homeostasis_bridged` | number bridged in current step | events |
| `phase` | runtime phase label in event/UTD output | events, UTD `why` |
| `ute_in_count` / `ute_text_count` | ingress counts | events, UTD |
| `did_say` | offline say-event marker from UTD alignment | derived tick table |