# data_analysis_cleaned_no_say

Cleaned data-analysis package with the old mouth/output-channel scripts removed.

What changed:

- Removed scripts that parse `macro: say`, `did_say`, `utd_say_*`, composer output, reply lag, neologism output, LCS/Jaccard copy audits, and boundary motifs over emitted text.
- Replaced the two most useful ingestion scripts with no-say versions:
  - `01_ingest/00_build_tick_table_core.py`
  - `01_ingest/01_dashboard_metrics_core.py`
- Added a state-only operator differentiation script:
  - `06_operator_input_state/d5_1_operator_state_differentiation_no_say.py`
- Added a current-safe scalar H derivation utility:
  - `03_dynamics_timeseries/derive_h.py`

The remaining scripts are organized around current-use analysis families:

```text
01_ingest/                tick/event ingestion without say-event flags
02_snapshot_connectome/   H5 sparse snapshot, connectome, node matching
03_dynamics_timeseries/   scalar dynamics, H derivation, recurrence, phase-transition, timing
04_higher_order_info/     O-info / higher-order landscape reproductions
05_territory_structure/   territory/community structural phenotypes
06_operator_input_state/  operator-input state response without reply/say analysis
07_manifest_utilities/    package inventory helpers
```

Notes:

- `REMOVED_OBSOLETE_SCRIPTS.md` lists exactly what was removed and why.
- `ACTIVE_SCRIPT_INVENTORY.md` lists what remains.

Example use:

```bash
cd data_analysis_cleaned_no_say
PYTHONPATH=. python 01_ingest/00_build_tick_table_core.py   --events /path/to/events.jsonl   --out_csv_gz tables/tick_table_full.csv.gz

PYTHONPATH=. python 02_snapshot_connectome/01_compute_snapshot_metrics.py   --h5_dir /path/to/snapshots   --out_csv tables/snapshot_metrics.csv

PYTHONPATH=. python 06_operator_input_state/d5_1_operator_state_differentiation_no_say.py   --data-dir /path/to/Aura_Analysis_Tables   --exchange /path/to/aura_justin_exchange.md   --out-dir out/operator_state_no_say

python 03_dynamics_timeseries/derive_h.py   --input tables/tick_table_full.csv.gz   --output tables/derived_h.csv
```
