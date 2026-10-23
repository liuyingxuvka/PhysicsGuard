from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


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


def test_removed_commands_exit_two_and_diff_remains():
    for args in [('coverage','check','x.yaml'),('dataset','logical-check','x.yaml'),
                 ('dataset','relation-check','x.yaml'),('testfile','project-check','x.yaml')]:
        assert run_cli(*args).returncode == 2
    result=run_cli('testfile','diff',str(PUMP/'contracts/clean_contract.yaml'),str(PUMP/'contracts/renamed_field_contract.yaml'))
    assert result.returncode == 0 and json.loads(result.stdout)['status']=='changed'


def test_cli_validation_run_prints_a_compact_summary() -> None:
    plan = str(PUMP / "validation" / "shallow_time_varying_validation_plan.yaml")
    summary = run_cli("validation", "run", plan)
    full = run_cli("validation", "run", plan, "--json")
    assert summary.returncode == full.returncode == 1
    assert len(summary.stdout) < 4096 < len(full.stdout)
    data = json.loads(summary.stdout)
    assert data["output"] == "summary only; add --json for the full report"
    assert data["status"] == json.loads(full.stdout)["status"]
    assert data["depth_summary"] == json.loads(full.stdout)["depth_summary"]
    assert "depth" not in data and "critical_parameter_uncovered" in {item["type"] for item in data["findings"]}


def test_manifest_out_resolves_source_relative_to_manifest(tmp_path: Path) -> None:
    data_file = tmp_path / "data" / "run.csv"
    data_file.parent.mkdir()
    data_file.write_text("time_s,x\n0,1\n1,2\n", encoding="utf-8")
    output = tmp_path / "val" / "manifest.yaml"
    written = run_cli("testfile", "manifest", str(data_file), "--out", str(output))
    printed = run_cli("testfile", "manifest", str(data_file))
    assert written.returncode == printed.returncode == 0, written.stderr + printed.stderr
    manifest = yaml.safe_load(output.read_text(encoding="utf-8"))
    original = json.loads(printed.stdout)
    assert manifest["source_file"]["path"] == "../data/run.csv"
    assert (output.parent / manifest["source_file"]["path"]).resolve() == data_file.resolve()
    assert original["source_file"]["path"] == str(data_file)
    assert manifest["source_file"] == {**original["source_file"], "path": "../data/run.csv"}


def test_manifest_out_falls_back_to_absolute_path_across_drives(tmp_path: Path, monkeypatch) -> None:
    from physicsguard.cli import testfile_manifest_command

    data_file = tmp_path / "run.csv"
    data_file.write_text("time_s,x\n0,1\n", encoding="utf-8")
    output = tmp_path / "val" / "manifest.yaml"
    def different_drives(*args, **kwargs):
        raise ValueError("path is on a different drive")
    monkeypatch.setattr(os.path, "relpath", different_drives)
    assert testfile_manifest_command(data_file, out=output) == 0
    assert yaml.safe_load(output.read_text(encoding="utf-8"))["source_file"]["path"] == data_file.resolve().as_posix()
