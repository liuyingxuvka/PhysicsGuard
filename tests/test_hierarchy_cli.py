from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
FC = ROOT / "examples" / "hierarchical" / "fuel_cell_system"
OBSERVED = ROOT / "examples" / "hierarchical" / "observed_debugging"


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "physicsguard.cli", *args],
        cwd=ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def test_hierarchy_run_clean_example_returns_valid_json() -> None:
    result = run_cli("hierarchy", "run", str(FC / "level_0_system_balance.yaml"), "--pretty", "--json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["audit_pass"]
    assert data["optimization_success"]
    assert data["top_blocks"][0]["block_id"] == "fc_system"
    assert {
        "audit_name",
        "system_name",
        "optimization_success",
        "audit_pass",
        "residual_norm",
        "max_abs_normalized_residual",
        "top_residuals",
        "top_blocks",
        "block_assignments",
        "warnings",
    }.issubset(data)


def test_hierarchy_run_conflict_fails_with_code_1_and_audit_false() -> None:
    result = run_cli("hierarchy", "run", str(FC / "conflict_level_0_h2_power.yaml"), "--pretty")
    assert result.returncode == 1, result.stderr
    data = json.loads(result.stdout)
    assert not data["audit_pass"]
    assert data["top_blocks"][0]["block_id"] == "fc_system"
    assert data["recommended_refinements"]


def test_hierarchy_inspect_returns_block_tree_json() -> None:
    result = run_cli("hierarchy", "inspect", str(FC / "level_0_system_balance.yaml"), "--pretty")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["audit_name"] == "fuel_cell_level_0_system_balance"
    assert data["root_blocks"] == ["fc_system"]
    assert data["blocks"][0]["id"] == "fc_system"
    assert data["missing_components"] == []


def test_hierarchy_plan_returns_recommendations_only() -> None:
    result = run_cli("hierarchy", "plan", str(FC / "conflict_level_0_h2_power.yaml"), "--pretty", "--json")
    assert result.returncode == 1, result.stderr
    data = json.loads(result.stdout)
    assert set(data) == {
        "top_blocks",
        "recommended_refinements",
        "signal_mapping_ledger",
        "bug_family_followups",
        "missing_required_variables",
        "missing_required_parameters",
        "warnings",
    }
    assert data["recommended_refinements"][0]["next_template_ids"]


def test_hierarchy_evaluate_observed_fault_returns_block_rollup_without_solver() -> None:
    result = run_cli(
        "hierarchy",
        "evaluate",
        str(OBSERVED / "pitch_feedback_level_0.yaml"),
        str(OBSERVED / "pitch_feedback_observed_fault.yaml"),
        "--pretty",
        "--json",
    )
    assert result.returncode == 1, result.stderr
    data = json.loads(result.stdout)
    assert not data["audit_pass"]
    assert data["metadata"]["mode"] == "hierarchy_evaluate"
    assert data["metadata"]["solver_attempted"] is False
    assert data["top_blocks"][0]["block_id"] == "pitch_rate_feedback"
    assert data["recommended_refinements"][0]["next_template_ids"]


def test_hierarchy_compare_observed_fault_returns_deviations_and_hierarchy() -> None:
    result = run_cli(
        "hierarchy",
        "compare",
        str(OBSERVED / "pitch_feedback_level_0.yaml"),
        str(OBSERVED / "pitch_feedback_observed_fault.yaml"),
        "--pretty",
        "--json",
    )
    assert result.returncode == 1, result.stderr
    data = json.loads(result.stdout)
    assert data["metadata"]["mode"] == "hierarchy_compare"
    assert data["reference_audit_pass"]
    assert not data["observed_audit_pass"]
    assert data["top_variable_deviations"][0]["variable"] == "controller_q_gain.y"
    assert data["observed_hierarchy"]["top_blocks"][0]["block_id"] == "pitch_rate_feedback"


def test_hierarchy_invalid_file_returns_nonzero() -> None:
    result = run_cli("hierarchy", "run", str(FC / "missing.yaml"))
    assert result.returncode == 2


def test_existing_run_command_still_works_after_hierarchy_cli_added() -> None:
    result = run_cli("run", str(ROOT / "examples" / "dummy_system.yaml"), "--pretty")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["system_name"] == "dummy_clean_system"


def test_hierarchy_evaluate_reports_a_partial_snapshot(tmp_path: Path) -> None:
    import yaml

    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.core.solver import BoundedSolver
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec

    audit = ROOT / "examples" / "hierarchical" / "coolant_loop" / "level_1_components.yaml"
    spec = load_hierarchical_audit_spec(audit)
    solved = BoundedSolver(ResidualBuilder(spec.system), spec.system.solver).solve().variables
    snapshot = {"variables": {name: {"value": float(value)} for name, value in solved.items() if name != "cool.Q_stack_heat_W"}}
    (tmp_path / "partial.yaml").write_text(yaml.safe_dump(snapshot), encoding="utf-8")
    result = run_cli("hierarchy", "evaluate", str(audit), str(tmp_path / "partial.yaml"))
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["audit_pass"]
    assert data["missing_required_variables"] == []
    assert data["derived_variables"] == ["cool.Q_stack_heat_W"]
    assert data["checked_residual_count"] > 0
    assert data["unchecked_residual_count"] == 0
    full = run_cli("hierarchy", "evaluate", str(audit), str(tmp_path / "partial.yaml"), "--json")
    assert full.returncode == 0, full.stderr
    report = json.loads(full.stdout)
    producing = report["derived_variables"]["cool.Q_stack_heat_W"]["residual_occurrence"]
    assert producing not in report["metadata"]["checked_residual_occurrences"]
    assert report["metadata"]["observed_variable_count"] == len(snapshot["variables"])

    fault = yaml.safe_load((OBSERVED / "pitch_feedback_observed_fault.yaml").read_text(encoding="utf-8"))
    del fault["variables"]["controller_q_gain.y"]
    (tmp_path / "nothing_left.yaml").write_text(yaml.safe_dump(fault), encoding="utf-8")
    result = run_cli("hierarchy", "evaluate", str(OBSERVED / "pitch_feedback_level_0.yaml"), str(tmp_path / "nothing_left.yaml"))
    assert result.returncode == 2
    assert "no residual can be evaluated without them" in result.stderr


def test_hierarchy_evaluate_prints_a_compact_summary_without_input_echo() -> None:
    args = ("hierarchy", "evaluate", str(OBSERVED / "pitch_feedback_level_0.yaml"), str(OBSERVED / "pitch_feedback_observed_fault.yaml"))
    summary = run_cli(*args)
    full = run_cli(*args, "--json")
    assert summary.returncode == full.returncode == 1, summary.stderr
    assert len(summary.stdout) < 4096 < len(full.stdout)
    data = json.loads(summary.stdout)
    assert data["output"] == "summary only; add --json for the full report"
    assert data["audit_pass"] is False
    assert data["top_blocks"][0]["block_id"] == "pitch_rate_feedback"
    assert {item["followup_id"] for item in data["bug_family_followups"]} == {"linear_gain_sign_family"}
    assert "metadata" not in data and "block_assignments" not in data
    assert "hierarchy" not in json.loads(full.stdout)["metadata"]
