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
    assert "model time remains endogenous" in text
    assert "wall-clock fields are logging" in text
    assert "provenance" in text
    assert "offline-analysis coordinates" in text
    assert "tick-indexed physiology" in text
    assert "sie" in text
    assert "b1" in text
    assert "fixed-step" in text
    assert "wall-clock substitution" in text
    assert "non-cognitive work" in text
    assert "comparison tooling must not redefine the endogenous model clock" in text
    assert "dev-references/aura-run/tables/sie_v2/sie_v2_scan_summary.csv" in text
    assert "dev-references/aura-run/json/f8_02_tick_duration_analysis.json" in text


def test_policy_does_not_assert_hybrid_wall_time_runtime() -> None:
    root = _repo_root() / "vdm_rt"
    contract = (root / "docs" / "contracts" / "runtime-invariants.yml").read_text(encoding="utf-8").lower()
    reference = (root / "docs" / "pages" / "reference" / "runtime-invariants.md").read_text(encoding="utf-8").lower()
    loop = (root / "runtime" / "loop" / "main.py").read_text(encoding="utf-8").lower()

    assert "hybrid endogenous timing" not in contract + "\n" + reference
    assert "wall-time carrier" not in contract + "\n" + reference + "\n" + loop


def test_runtime_cli_does_not_expose_fixed_step_clock() -> None:
    root = _repo_root()
    cli = (root / "vdm_rt" / "cli" / "args.py").read_text(encoding="utf-8")

    assert "--steps" not in cli
    assert "--max-steps" not in cli
    assert "--fixed-steps" not in cli
