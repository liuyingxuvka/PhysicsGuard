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
    result = run_cli("hierarchy", "run", str(FC / "level_0_system_balance.yaml"), "--pretty")
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


def test_hierarchy_run_conflict_returns_code_0_and_audit_false() -> None:
    result = run_cli("hierarchy", "run", str(FC / "conflict_level_0_h2_power.yaml"), "--pretty")
    assert result.returncode == 0, result.stderr
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
    result = run_cli("hierarchy", "plan", str(FC / "conflict_level_0_h2_power.yaml"), "--pretty")
    assert result.returncode == 0, result.stderr
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
    )
    assert result.returncode == 0, result.stderr
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
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["metadata"]["mode"] == "hierarchy_compare"
    assert data["reference_audit_pass"]
    assert not data["observed_audit_pass"]
    assert data["top_variable_deviations"][0]["variable"] == "controller_q_gain.y"
    assert data["observed_hierarchy"]["top_blocks"][0]["block_id"] == "pitch_rate_feedback"


def test_hierarchy_invalid_file_returns_nonzero() -> None:
    result = run_cli("hierarchy", "run", str(FC / "missing.yaml"))
    assert result.returncode != 0


def test_existing_run_command_still_works_after_hierarchy_cli_added() -> None:
    result = run_cli("run", str(ROOT / "examples" / "dummy_system.yaml"), "--pretty")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["system_name"] == "dummy_clean_system"
