from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_every_registered_module_has_a_native_readable_description() -> None:
    from physicsguard.modules.registry import default_module_registry, describe_module_type

    registry = default_module_registry()
    descriptions = {name: describe_module_type(name, registry) for name in registry.registered_types()}
    assert len(descriptions) == 152
    for name, description in descriptions.items():
        json.dumps(description, allow_nan=False)
        assert description["module_type"] == name
        assert description["summary"]
        assert description["metadata"]["module_type"] == name
        assert description["description_context"]["solver_attempted"] is False
        if name == "MappedSignalModule":
            # This native signal declaration deliberately contributes no equation.
            assert description["residuals"] == []
            assert description["description_context"]["empty_residuals_reason"]
        else:
            assert description["residuals"], name
        for record in description["residuals"]:
            assert record["name"] and record["role"] and record["diagnostic_key"] and record["description"]
    tank = descriptions["TankVolumeRateModule"]
    assert len(tank["variables"]) == 4
    assert {record["unit"] for record in tank["variables"]} == {"m^3", "m^3/s"}
    assert tank["parameters"]["required"] == ["dt_s"]
    assert tank["parameters"]["optional"]["residual_scale_m3"] == 0.001
    assert "volume_current - (volume_previous + (V_dot_in - V_dot_out)*dt)" in tank["residuals"][0]["description"]
    assert len(descriptions["LinearRelationModule"]["parameters"]["required"]) == 8
    assert "expected" in descriptions["MapMonotonicityCheckModule"]["parameters"]["required"]
    external = descriptions["ConservationSumModule"]
    assert external["variables"] == []
    assert external["description_context"]["synthetic_external_variables"]
    for reference in ("pump-a.P_W", "水泵.功率_W"):
        actual = describe_module_type("SumModule", parameters={"input_variables": [reference], "output_variable": "meter.sum_W"})
        assert reference in actual["description_context"]["synthetic_external_variables"]
        assert actual["residuals"][0]["diagnostic_key"] == "sum_relation_mismatch"


def test_module_description_restores_existing_profiler_on_success_and_failure() -> None:
    import pytest
    from physicsguard.modules.base import BaseModule
    from physicsguard.modules.registry import ModuleRegistry, default_module_registry, describe_module_type

    previous = sys.getprofile()
    events = []
    def observer(frame, event, arg):
        if frame.f_code is BaseModule.__init__.__code__:
            events.append(event)
    try:
        sys.setprofile(observer)
        describe_module_type("TankVolumeRateModule")
        assert sys.getprofile() is observer and "return" in events
        registry = ModuleRegistry()
        def broken(component_id, parameters):
            raise ValueError("cannot construct this module")
        registry.register("Broken", broken)
        with pytest.raises(ValueError, match="cannot describe Broken"):
            describe_module_type("Broken", registry)
        assert sys.getprofile() is observer
    finally:
        sys.setprofile(previous)
    module = default_module_registry().create("TankVolumeRateModule", "tank", {"dt_s": 1})
    assert type(module.parameters) is dict


def test_module_cli_lists_registry_and_reports_unknown_type(capsys) -> None:
    from physicsguard.cli import main
    from physicsguard.modules.registry import default_module_registry

    assert main(["modules", "list"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [line.split(": ", 1)[0] for line in lines] == default_module_registry().registered_types()
    assert all(line.split(": ", 1)[1] for line in lines)
    assert main(["modules", "describe", "TankVolumeRateModule"]) == 0
    assert len(json.loads(capsys.readouterr().out)["variables"]) == 4
    assert main(["modules", "describe", "MissingModule"]) == 2
    assert "MissingModule" in capsys.readouterr().err


def test_hierarchy_description_has_real_tree_connections_and_never_solves(monkeypatch, capsys) -> None:
    from physicsguard.cli import main
    from physicsguard.core.solver import BoundedSolver
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec

    def no_solve(*args, **kwargs):
        raise AssertionError("description must not solve")
    monkeypatch.setattr(BoundedSolver, "solve", no_solve)
    path = ROOT / "examples/hierarchical/heated_tank/heated_tank.yaml"
    spec = load_hierarchical_audit_spec(path)
    assert main(["hierarchy", "describe", str(path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert {block["id"] for block in report["blocks"]} == {block.id for block in spec.hierarchy.blocks}
    assert len(report["blocks"]) == 6 and report["solver_attempted"] is False
    assert {edge["scope"] for edge in report["connections"]} == {"within_block", "between_blocks"}
    assert report["fault_variants"] == [variant.model_dump() for variant in spec.fault_variants]
    assert report["refinement_rules"] == [rule.model_dump() for rule in spec.hierarchy.refinement_rules]
    thermal = next(block for block in report["blocks"] if block["id"] == "thermal")
    assert "heater" in thermal["children"]
    assert all(component["native_description"]["residuals"] for component in thermal["components"])
    assert main(["hierarchy", "describe", str(path), "--mermaid"]) == 0
    mermaid = capsys.readouterr().out
    assert mermaid.startswith("flowchart TD\n")
    assert mermaid.count("subgraph ") == 6
    assert all(f'"{block.id} (level {block.level})"' in mermaid for block in spec.hierarchy.blocks)
    assert "vol.volume_current_m3" in mermaid


def test_hierarchy_compact_summary_preserves_each_assumption_disposition() -> None:
    from physicsguard.cli import _hierarchy_summary
    from physicsguard.core.assumptions import AssumptionManager
    from physicsguard.schema.system_spec import SystemSpec

    system = SystemSpec.model_validate({"system_name": "cards", "components": [{"id": "power", "type": "ElectricalPowerModule"}],
        "assumptions": [{"id": name, "target_type": "context", "target": "scope", "value": "steady DC", "reason": "explicit scoped card", "status": status}
                        for name, status in (("used", "active"), ("pending", "proposed"), ("declined", "rejected"))]})
    manager = AssumptionManager(system)
    manager.apply_parameter_assumptions(system)
    result = _hierarchy_summary({"assumptions": manager.summary_dict()})
    assert result["assumptions"] == [{"id": "used", "status": "active", "applied": True},
                                     {"id": "pending", "status": "proposed", "applied": False},
                                     {"id": "declined", "status": "rejected", "applied": False}]


def test_hierarchy_description_exposes_active_parameter_fills_without_mutating_the_model() -> None:
    from physicsguard.core.hierarchy import describe_hierarchy
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec

    spec = HierarchicalAuditSpec.model_validate({"audit_name": "assumed_step", "system": {"system_name": "tank_step",
        "components": [{"id": "tank", "type": "TankVolumeRateModule"}],
        "assumptions": [{"id": "sample_period", "target_type": "parameter", "target": "tank.dt_s", "value": 10,
                         "reason": "Declared sampling period", "source": "bench specification"}]},
        "hierarchy": {"blocks": [{"id": "plant", "components": ["tank"]}]}})
    before = spec.model_dump()
    result = describe_hierarchy(spec)
    component = result["blocks"][0]["components"][0]
    assert component["parameters"] == {} and component["effective_parameters"] == {"dt_s": 10}
    assert component["native_description"]["parameters"]["supplied"] == {"dt_s": 10}
    assert "optional" not in component["native_description"]["parameters"]
    assert component["native_description"]["residuals"]
    assert result["parameter_assumption_applications"][0]["applied"] is True
    assert spec.model_dump() == before


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def test_cli_dummy_system_passes_with_code_0() -> None:
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
    assert result.returncode == 2


def test_cli_run_physical_coolant_returns_valid_json() -> None:
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
    assert result.returncode == 1, result.stderr
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
    assert result.returncode == 1, result.stderr
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
    assert result.returncode == 2


def test_cli_dummy_conflict_is_checked_and_not_passed() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "physicsguard.cli", "run", str(ROOT / "examples/dummy_conflict_system.yaml")],
        cwd=ROOT, env=cli_env(), text=True, capture_output=True, check=False,
    )
    assert result.returncode == 1, result.stderr
    assert json.loads(result.stdout)["audit_pass"] is False
