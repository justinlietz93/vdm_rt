# Removed obsolete mouth / say-event / composer scripts

These were not copied into the cleaned package. The goal is to keep state/dynamics/topology/operator-input analyses and remove old mouth/output-channel analyses.

| Removed path | Reason |
|---|---|
| `00_build_tick_table.py` | Replaced by 01_ingest/00_build_tick_table_core.py; old version marks did_say from UTD macro:say. |
| `01_dashboard_metrics.py` | Replaced by 01_ingest/01_dashboard_metrics_core.py; old version overlays say ticks and computes say_rate. |
| `03_utd_analysis.py` | Only summarizes UTD macro events and produces utd_say_* tables. |
| `analyze_scalar_struct_from_logs.py` | Mixed scalar analysis with did_say, say_count, event-triggered say windows, and say plots. |
| `create_aura_inputs.py` | Builds has_say / say_by_tick / log_text_words tables for Aura mouth/text analyses. |
| `create_aura_inputs_lean.py` | Lean version of Aura input builder with has_say/say_count/log_text_words. |
| `utd_parse_and_composer_audit.py` | Composer/say-event lexical overlap audit. |
| `vdm_analysis_dashboard.py` | Interactive dashboard centered on status + say event parsing. |
| `vdm_convert.py` | Old converter that emits statuses + say_events bundle. |
| `vdm_report.py` | Old report generator that parses and reports say_events. |
| `session_analysis_bundle.py` | Large Aura bundle runner mixing F10/F14/F15 say/composer/language analyses. |
| `batch1_fixed.py` | Exchange/text-content analysis, boundary motifs, output stages, replies. |
| `make_publication_figures.py` | Publication figure script tied to say/composer outputs. |
| `run_all.py` | Old umbrella pipeline references did_say/decoder/say-output analyses. |
| `run_all.sh` | Old umbrella shell pipeline that calls removed scripts. |
| `run_consciousness_suite_aura.py` | Old Aura suite includes text/log_text/has_text corpus-output channels. |
| `derive_H.py` | Old derived-H analysis has did_say/text/B1 coupling assumptions. |
| `F4_late_say_scripts/f4_late_say_state_coupling.py` | Direct late-say event window analysis. |
| `F10_silence_withholding_scripts/f10_silence_withholding_analysis.py` | Inter-say/silence/withholding analysis. |
| `F14_composer_audit_scripts/f14_composer_audit_analysis.py` | Composer lexical-copy audit. |
| `F15_interaction_analysis/f15_interaction_analysis.py` | Old exchange/reply interaction analysis. |
| `F8_temporal_microstructure_scripts/f8_temporal_microstructure_analysis.py` | Inter-say interval / burst analysis. |
| `D1_4_neologism_synthesis_scripts/*` | Output-language/neologism analysis from say text. |
| `F5_boundary_attractor_scripts/f5_boundary_attractor_analysis.py` | Boundary motif analysis over output text. |
| `F11_thematic_independence_scripts/*` | Cross-source thematic/output-text motif analyses. |
| `D7_territories_scripts/d57_territory_behavior_analysis.py` | Territory behavior tied to say/composer jaccard/LCS. |
| `F3_territory_maps/d57_territory_behavior_analysis.py` | Duplicate territory behavior tied to say/composer jaccard/LCS. |
