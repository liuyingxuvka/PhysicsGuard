from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def test_cli_dummy_system_returns_code_0() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "physicsguard.cli",
            "run",
            str(ROOT / "examples" / "dummy_system.yaml"),
        ],
        cwd=ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_cli_stdout_is_valid_json_with_required_keys() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "physicsguard.cli",
            "run",
            str(ROOT / "examples" / "dummy_system.yaml"),
        ],
        cwd=ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    data = json.loads(result.stdout)
    assert {
        "system_name",
        "optimization_success",
        "audit_pass",
        "audit_threshold",
        "max_abs_normalized_residual",
        "residual_norm",
        "variables",
        "top_residuals",
        "bound_hits",
        "warnings",
        "metadata",
    }.issubset(data)
    assert "role" in data["top_residuals"][0]


def test_cli_invalid_file_returns_nonzero() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "physicsguard.cli",
            "run",
            str(ROOT / "examples" / "missing.yaml"),
        ],
        cwd=ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0


def test_cli_solve_physical_coolant_returns_valid_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "physicsguard.cli",
            "solve",
            str(ROOT / "examples" / "physical_coolant_heat_balance.yaml"),
            "--pretty",
        ],
        cwd=ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["optimization_success"]
    assert data["audit_pass"]


def test_cli_run_still_works_as_alias() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "physicsguard.cli",
            "run",
            str(ROOT / "examples" / "physical_coolant_heat_balance.yaml"),
            "--pretty",
        ],
        cwd=ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["system_name"] == "physical_coolant_heat_balance"


def test_cli_evaluate_clean_observed_returns_audit_pass_true() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "physicsguard.cli",
            "evaluate",
            str(ROOT / "examples" / "physical_coolant_heat_balance.yaml"),
            str(ROOT / "examples" / "observed" / "physical_coolant_observed_clean.yaml"),
            "--pretty",
        ],
        cwd=ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["audit_pass"]
    assert data["metadata"]["mode"] == "evaluate"


def test_cli_evaluate_conflict_observed_returns_audit_pass_false() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "physicsguard.cli",
            "evaluate",
            str(ROOT / "examples" / "physical_coolant_heat_balance.yaml"),
            str(ROOT / "examples" / "observed" / "physical_coolant_observed_conflict.yaml"),
            "--pretty",
        ],
        cwd=ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert not data["audit_pass"]
    assert data["top_residuals"][0]["diagnostic_key"] == "coolant_heat_balance_mismatch"


def test_cli_compare_conflict_observed_includes_variable_deviations() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "physicsguard.cli",
            "compare",
            str(ROOT / "examples" / "physical_coolant_heat_balance.yaml"),
            str(ROOT / "examples" / "observed" / "physical_coolant_observed_conflict.yaml"),
            "--pretty",
        ],
        cwd=ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert not data["observed_audit_pass"]
    assert data["top_variable_deviations"][0]["variable"] == "coolant.Q_dot_W"


def test_cli_invalid_observed_file_returns_nonzero() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "physicsguard.cli",
            "evaluate",
            str(ROOT / "examples" / "physical_coolant_heat_balance.yaml"),
            str(ROOT / "examples" / "observed" / "missing.yaml"),
        ],
        cwd=ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
