# Trace-conditioned deterministic bot experiment package

Files:

- `tools/run_trace_conditioned_bot_suite.py` - user-facing whole-run suite runner.
- `tools/run_trace_conditioned_bot_suite_core.py` - experiment core adapted from the anti-reafference harness.
- `tools/analyze_trace_conditioned_bot_results.py` - bot-specific report generator.
- `tools/base_sensory_occlusion_runner.py` - VDM runtime harness helper.
- `tools/intention_trace_translator.py` - 2048 phrase-index translator.
- `src/deterministic_vdm_bot/` - deterministic bot rule engine.
- `index/` - 2048 phrase bank and vector index.
- `setup_env.sh` - creates local venv and installs wrapper dependencies.
- `run_trace_bot_3000.sh` - runs six 3000-tick comparison runs.
- `run_trace_bot_5000.sh` - longer six-run version.
- `analyze_trace_bot.sh` - reruns report generation on existing results.

The package does not bundle a stale `vdm_rt-main`. Pass your live official repo with `--repo` or the first shell-script argument.
