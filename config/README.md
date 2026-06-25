# Runtime Config

The runtime reads every `*.toml` file in this folder and deep-merges the
top-level tables. Keep related knobs together in named files instead of growing
one large config file.

Discovery checks `config/` from the current working directory, then
`vdm_rt/config/`, then this package directory. Missing config falls back to code
defaults; malformed TOML fails loudly so bad operator input is visible.

Current files:

- `launch.toml` - command-line launch defaults and run-directory behavior.
- `runtime.toml` - cross-cutting loop, event, territory, and composer knobs.
- `sparse_connectome.toml` - sparse graph maintenance controls.
- `adc.toml` - announcement bus and ADC defaults.
- `stimulus.toml` - text-to-connectome stimulation defaults.
- `speech.toml` - autonomous speech and B1 detector defaults.
- `maps.toml` - event map and memory/trail view defaults.
- `sie.toml` - Self-Improvement Engine runtime defaults.
- `persistence.toml` - checkpoint and resume defaults.
- `control.toml` - embedded control-plane defaults.
- `learning.toml` - optional REVGSP/GDSP adapter controls.
- `scouts.toml` - void-walker scout budgets and per-scout enable flags.
- `io.toml` - emitters, smoke checks, HTTP status, and Redis status output.
- `logging.toml` - JSONL and zip spool limits.
