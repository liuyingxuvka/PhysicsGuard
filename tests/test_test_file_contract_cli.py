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


def test_cli_dataset_validation_and_model_library_commands() -> None:
    logical = run_cli(
        "dataset",
        "logical-check",
        str(PUMP / "datasets" / "clean_logical_dataset.yaml"),
        "--pretty",
    )
    relation = run_cli(
        "dataset",
        "relation-check",
        str(PUMP / "relation_index.yaml"),
        "--pretty",
    )
    validation = run_cli(
        "validation",
        "run",
        str(PUMP / "validation" / "clean_validation_plan.yaml"),
        "--pretty",
    )
    library = run_cli(
        "model-library",
        "check",
        str(PUMP / "model_library.yaml"),
        "--pretty",
    )

    assert logical.returncode == 0, logical.stderr
    assert relation.returncode == 0, relation.stderr
    assert validation.returncode == 0, validation.stderr
    assert library.returncode == 0, library.stderr
    assert json.loads(logical.stdout)["status"] == "pass"
    assert json.loads(validation.stdout)["status"] == "pass"


def test_cli_project_evidence_commands() -> None:
    registry = PUMP / "evidence" / "project_evidence_registry.yaml"
    check = run_cli("evidence", "check", str(registry), "--pretty")
    gap = run_cli("evidence", "gap-check", str(registry), "--pretty")
    bundle = run_cli(
        "evidence",
        "bundle-check",
        str(registry),
        "pump_loop_validation_bundle_001",
        "--pretty",
    )
    project_map = run_cli("evidence", "map", str(registry), "--pretty")

    assert check.returncode == 0, check.stderr
    assert gap.returncode == 0, gap.stderr
    assert bundle.returncode == 0, bundle.stderr
    assert project_map.returncode == 0, project_map.stderr
    map_data = json.loads(project_map.stdout)
    assert map_data["coverage_summary"]["unresolved_binding_gap_count"] == 0
    assert "pump_signal_map.x" in map_data["coverage_summary"]["tested_model_targets"]


def test_cli_project_closure_command() -> None:
    result = run_cli(
        "project",
        "closure",
        str(PUMP / "project_closure_plan.yaml"),
        "--pretty",
    )

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["artifact_kind"] == "physicsguard_project_closure_report"
    assert data["closure_status"] == "passed"
