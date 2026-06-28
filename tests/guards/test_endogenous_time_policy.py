from pathlib import Path


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "vdm_rt").is_dir():
            return parent
    raise AssertionError("repo root not found")


def test_governance_requires_endogenous_model_time() -> None:
    root = _repo_root()
    contract = (root / "vdm_rt" / "docs" / "contracts" / "runtime-invariants.yml").read_text(
        encoding="utf-8"
    ).lower()
    reference = (root / "vdm_rt" / "docs" / "pages" / "reference" / "runtime-invariants.md").read_text(
        encoding="utf-8"
    ).lower()
    text = contract + "\n" + reference

    assert "m04" in text
    assert "endogenous cognitive time is sovereign" in text
    assert "decoupled from wall time" in text
    assert "fixed-step" in text
    assert "non-cognitive work" in text
    assert "comparison tooling must not redefine the model clock" in text
    assert "dev-references/aura-run/tables/sie_v2/sie_v2_scan_summary.csv" in text
    assert "dev-references/aura-run/json/f8_02_tick_duration_analysis.json" in text


def test_runtime_cli_does_not_expose_fixed_step_clock() -> None:
    root = _repo_root()
    cli = (root / "vdm_rt" / "cli" / "args.py").read_text(encoding="utf-8")

    assert "--steps" not in cli
    assert "--max-steps" not in cli
    assert "--fixed-steps" not in cli
