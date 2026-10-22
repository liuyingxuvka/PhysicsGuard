from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/hierarchical/heated_tank"


def test_generator_reproduces_committed_csv(tmp_path: Path) -> None:
    output = tmp_path / "run.csv"
    result = subprocess.run([sys.executable, str(EXAMPLE / "sim_tank.py"), str(output)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert output.read_bytes() == (EXAMPLE / "tank_run.csv").read_bytes()


def test_csv_contains_the_heater_fault_and_inflow_step() -> None:
    with (EXAMPLE / "tank_run.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert [float(row["time_s"]) for row in rows] == list(range(0, 1201, 10))
    assert {float(row["I_heater_A"]) for row in rows if float(row["time_s"]) < 600} == {50.0}
    assert {float(row["I_heater_A"]) for row in rows if float(row["time_s"]) >= 600} == {25.0}
    assert {float(row["P_heater_cmd_kW"]) for row in rows} == {20.0}
    assert {float(row["inflow_Lps"]) for row in rows if float(row["time_s"]) < 900} == {1.0}
    assert {float(row["inflow_Lps"]) for row in rows if float(row["time_s"]) >= 900} == {0.6}


def test_coupled_hierarchy_inspection_contains_six_blocks() -> None:
    result = subprocess.run([sys.executable, "-m", "physicsguard.cli", "hierarchy", "inspect", str(EXAMPLE / "heated_tank.yaml")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["root_blocks"] == ["tank"]
    assert {block["id"] for block in data["blocks"]} == {"tank", "hydraulics", "thermal", "heater", "throughflow", "envelope"}


def test_mapper_reproduces_only_measured_snapshots(tmp_path: Path) -> None:
    result = subprocess.run([sys.executable, str(EXAMPLE / "map_measured.py"), str(EXAMPLE / "tank_run.csv"), str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    for step in (30, 70):
        for prefix, count in (("first_step_measured", 9), ("measured", 11)):
            name = f"{prefix}_k{step}.yaml"
            assert (tmp_path / name).read_bytes() == (EXAMPLE / name).read_bytes()
            variables = yaml.safe_load((tmp_path / name).read_text())["variables"]
            assert len(variables) == count
            assert all(item["unit"] and item["external_signal"] and item["mapping_confidence"] for item in variables.values())
            assert not any("derived" in item["external_signal"] for item in variables.values())
            assert "heater_eff.efficiency" not in variables


@pytest.mark.parametrize(("step", "expected_pass"), [(30, True), (70, False)])
def test_coarse_tank_pinned_measurements_preserve_the_energy_fault(tmp_path: Path, step: int, expected_pass: bool) -> None:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec

    data = yaml.safe_load((EXAMPLE / "first_step_level0.yaml").read_text(encoding="utf-8"))
    observed = yaml.safe_load((EXAMPLE / f"first_step_measured_k{step}.yaml").read_text(encoding="utf-8"))
    data["system"]["boundaries"] = [
        {"variable": name, "value": item["value"], "scale": max(abs(item["value"]) * 1e-6, 1e-12),
         "description": item["external_signal"]}
        for name, item in observed["variables"].items()
    ]
    path = tmp_path / f"pinned_k{step}.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    report = HierarchicalAuditRunner(load_hierarchical_audit_spec(path)).run()
    assert report.audit_pass is expected_pass
    if not expected_pass:
        assert report.top_blocks[0].block_id == "thermal"
        assert report.max_abs_normalized_residual > 1.0
