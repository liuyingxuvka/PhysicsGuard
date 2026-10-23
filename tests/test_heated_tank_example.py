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


def test_contract_reproduces_only_measured_snapshots(tmp_path: Path) -> None:
    for step in (30, 70):
        for prefix, count, contract in (("first_step_measured", 9, "first_step_contract.yaml"),
                                         ("measured", 11, "tank_run_contract.yaml")):
            name = f"{prefix}_k{step}.yaml"
            result = subprocess.run([sys.executable, "-m", "physicsguard.cli", "testfile", "snapshot",
                                     str(EXAMPLE / contract), "--row", str(step), "--out", str(tmp_path / name)],
                                    capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
            assert yaml.safe_load((tmp_path / name).read_text()) == yaml.safe_load((EXAMPLE / name).read_text())
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


@pytest.mark.parametrize(("coupled", "step"), [(False, 30), (False, 70), (True, 30), (True, 70)])
def test_measured_tank_derivations_are_reported_without_solving(monkeypatch, coupled: bool, step: int) -> None:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.core.solver import BoundedSolver
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    audit_name = "heated_tank.yaml" if coupled else "first_step_level0.yaml"
    prefix = "measured" if coupled else "first_step_measured"
    observed = load_observed_values(EXAMPLE / f"{prefix}_k{step}.yaml")
    before = observed.model_dump(mode="json")
    monkeypatch.setattr(BoundedSolver, "solve", lambda *a, **kw: pytest.fail("measured-only evaluation must not solve"))
    report = HierarchicalAuditRunner(load_hierarchical_audit_spec(EXAMPLE / audit_name)).evaluate_observed(observed)
    assert report.audit_pass is (step == 30)
    assert observed.model_dump(mode="json") == before
    assert set(report.derived_variables).isdisjoint(observed.variables)
    assert report.metadata["observed_variable_count"] == len(observed.variables)
    assert {row.physics_variable for row in report.signal_mapping_ledger} == set(observed.variables)
    assert not report.unchecked_residuals and not report.missing_required_variables
    producers = {item["residual"] for item in report.derived_variables.values()}
    assert producers.isdisjoint(report.checked_residuals)
    assert report.checked_residuals
    number = lambda name: observed.variables[name].value
    mass_flow = 1000. * number("inflow_mass.V_dot_m3_s")
    through_heat = mass_flow * 4186. * (number("heat.T_previous_K") - number("through.T_in_K"))
    wall_loss = 20. * (number("heat.T_previous_K") - number("loss.T_ambient_K"))
    for name, expected in {
        "lvl_prev.volume_m3": .5 * number("lvl_prev.level_m"),
        "inflow_mass.m_dot_kg_s": mass_flow, "through.Q_dot_W": through_heat,
        "loss.Q_loss_W": wall_loss, "heat.Q_out_W": through_heat + wall_loss,
    }.items():
        assert report.derived_variables[name]["value"] == pytest.approx(expected, rel=1e-6)
    assert report.metadata["residual_dependencies"]["qout.sum_relation"] == ["heat.Q_out_W", "loss.Q_loss_W", "through.Q_dot_W"]
    if step == 70:
        assert report.top_blocks[0].block_id == ("heater" if coupled else "thermal")
        assert report.top_residuals[0].name == ("heater_cmd.linear_relation" if coupled else "heat.thermal_mass_temperature_step")
        if coupled:
            thermal = next(block for block in report.top_blocks if block.block_id == "thermal")
            assert thermal.score < 1.0
