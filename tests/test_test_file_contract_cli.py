from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"


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


def test_cli_testfile_manifest_outputs_json(tmp_path: Path) -> None:
    data_file = tmp_path / "sample.csv"
    data_file.write_text("time_s,x\n0.0,1.0\n0.1,1.5\n", encoding="utf-8")

    result = run_cli("testfile", "manifest", str(data_file), "--time-column", "time_s", "--pretty")

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["shape"]["field_count"] == 2
    assert data["time"]["sampling_mode"] == "time_series"


def test_cli_testfile_contract_check_passes_clean_contract() -> None:
    result = run_cli(
        "testfile",
        "contract-check",
        str(PUMP / "contracts" / "clean_contract.yaml"),
        "--pretty",
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "pass"


def test_cli_testfile_contract_check_fails_added_field() -> None:
    result = run_cli(
        "testfile",
        "contract-check",
        str(PUMP / "contracts" / "added_field_contract.yaml"),
        "--pretty",
    )

    assert result.returncode != 0
    assert json.loads(result.stdout)["summary"]["analysis_claim_gate"] == "blocked_until_contract_errors_are_fixed"


def test_cli_coverage_project_and_diff_commands() -> None:
    coverage = run_cli("coverage", "check", str(PUMP / "contracts" / "clean_contract.yaml"), "--pretty")
    project = run_cli("testfile", "project-check", str(PUMP / "project_index.yaml"), "--pretty")
    diff = run_cli(
        "testfile",
        "diff",
        str(PUMP / "contracts" / "clean_contract.yaml"),
        str(PUMP / "contracts" / "renamed_field_contract.yaml"),
        "--pretty",
    )

    assert coverage.returncode == 0, coverage.stderr
    assert project.returncode == 0, project.stderr
    assert diff.returncode == 0, diff.stderr
    assert json.loads(coverage.stdout)["status"] == "pass"
    assert json.loads(project.stdout)["status"] == "pass"
    assert json.loads(diff.stdout)["status"] == "changed"
