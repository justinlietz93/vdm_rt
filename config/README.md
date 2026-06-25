# Runtime Config

The runtime reads every `*.toml` file in this folder and deep-merges the
top-level tables. Keep related knobs together in named files instead of growing
one large config file.

Discovery checks `config/` from the current working directory, then
`vdm_rt/config/`, then this package directory. Missing config falls back to code
defaults; malformed TOML fails loudly so bad operator input is visible.

Current files:

- `runtime.toml` - cross-cutting loop, event, territory, and composer knobs.
- `sparse_connectome.toml` - sparse graph maintenance controls.
- `learning.toml` - optional REVGSP/GDSP adapter controls.
- `scouts.toml` - void-walker scout budgets and per-scout enable flags.
- `io.toml` - emitters, smoke checks, HTTP status, and Redis status output.
- `logging.toml` - JSONL and zip spool limits.
