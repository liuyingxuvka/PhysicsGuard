from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.modules.registry import default_module_registry
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "components" / "thermal_management"


def one_module(module_type: str, parameters: dict) -> SystemSpec:
    return SystemSpec.model_validate(
        {"system_name": module_type, "components": [{"id": "m", "type": module_type, "parameters": parameters}]}
    )


def solve_example(name: str):
    spec = load_system_spec(EXAMPLES / name)
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result, top_n=50)
    return result, report


def test_registry_includes_thermal_management_modules() -> None:
    assert {
        "ColdPlateSimpleModule",
        "ThermalMassStepModule",
        "ThermostatValveModule",
        "ThreeWayValveMixingModule",
        "ChillerSimpleModule",
        "ExpansionTankSimpleModule",
    }.issubset(set(default_module_registry().registered_types()))


@pytest.mark.parametrize(
    "name",
    [
        "cold_plate_simple.yaml",
        "thermal_mass_step.yaml",
        "thermostat_valve.yaml",
        "three_way_valve_mixing.yaml",
        "chiller_simple.yaml",
        "expansion_tank_simple.yaml",
    ],
)
def test_thermal_management_clean_examples_solve(name: str) -> None:
    result, report = solve_example(name)
    assert result.optimization_success
    assert result.audit_pass
    assert np.isfinite(result.residual_norm)
    assert all(item.role in {"equation", "boundary"} for item in report.top_residuals)


def test_conflict_cold_plate_fails_audit() -> None:
    result, report = solve_example("conflict_cold_plate_simple.yaml")
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key in {
        "cold_plate_coolant_heat_balance_mismatch",
        "cold_plate_ua_heat_transfer_mismatch",
    }


@pytest.mark.parametrize(
    ("module_type", "parameters", "message"),
    [
        ("ColdPlateSimpleModule", {"UA_W_K": 100.0, "cp_coolant_J_kgK": 0.0}, "cp_coolant_J_kgK"),
        ("ThermalMassStepModule", {"C_J_K": 0.0, "dt_s": 1.0}, "C_J_K"),
        ("ThermalMassStepModule", {"C_J_K": 1.0, "dt_s": 0.0}, "dt_s"),
        ("ThermostatValveModule", {"T_begin_open_K": 370.0, "T_full_open_K": 350.0}, "T_begin_open_K"),
    ],
)
def test_thermal_management_invalid_parameters_fail(module_type: str, parameters: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ResidualBuilder(one_module(module_type, parameters)).build_registry()
