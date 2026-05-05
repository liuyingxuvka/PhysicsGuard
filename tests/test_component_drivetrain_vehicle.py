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
EXAMPLES = ROOT / "examples" / "components" / "drivetrain_vehicle"


def one_module(module_type: str, parameters: dict) -> SystemSpec:
    return SystemSpec.model_validate(
        {"system_name": module_type, "components": [{"id": "m", "type": module_type, "parameters": parameters}]}
    )


def solve_example(name: str):
    spec = load_system_spec(EXAMPLES / name)
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result, top_n=80)
    return result, report


def test_registry_includes_drivetrain_vehicle_modules() -> None:
    assert {
        "GearboxSimpleModule",
        "WheelTorqueForceModule",
        "VehicleRoadLoadModule",
        "VehicleLongitudinalDynamicsStepModule",
        "BrakeSimpleModule",
        "RegenerativeBrakeSplitModule",
    }.issubset(set(default_module_registry().registered_types()))


@pytest.mark.parametrize(
    "name",
    [
        "gearbox_simple.yaml",
        "wheel_torque_force.yaml",
        "vehicle_road_load.yaml",
        "vehicle_longitudinal_dynamics_step.yaml",
        "brake_simple.yaml",
        "regenerative_brake_split.yaml",
    ],
)
def test_drivetrain_vehicle_clean_examples_solve(name: str) -> None:
    result, report = solve_example(name)
    assert result.optimization_success
    assert result.audit_pass
    assert np.isfinite(result.residual_norm)
    assert all(item.role in {"equation", "boundary"} for item in report.top_residuals)


def test_vehicle_longitudinal_conflict_fails_audit() -> None:
    result, report = solve_example("conflict_vehicle_longitudinal_dynamics_step.yaml")
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "vehicle_longitudinal_speed_step_mismatch"


@pytest.mark.parametrize(
    ("module_type", "parameters", "message"),
    [
        ("GearboxSimpleModule", {"gear_ratio": 0.0}, "gear_ratio"),
        ("VehicleRoadLoadModule", {"mass_kg": 0.0}, "mass_kg"),
        ("VehicleLongitudinalDynamicsStepModule", {"mass_kg": 0.0, "dt_s": 1.0}, "mass_kg"),
        ("VehicleLongitudinalDynamicsStepModule", {"mass_kg": 1000.0, "dt_s": 0.0}, "dt_s"),
    ],
)
def test_drivetrain_vehicle_invalid_parameters_fail(module_type: str, parameters: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ResidualBuilder(one_module(module_type, parameters)).build_registry()


def test_wheel_torque_force_denominator_fails_clearly() -> None:
    builder = ResidualBuilder(one_module("WheelTorqueForceModule", {}))
    registry = builder.build_registry()
    vector = registry.dict_to_vector(
        {
            "m.wheel_torque_Nm": 100.0,
            "m.wheel_radius_m": 0.0,
            "m.longitudinal_force_N": 0.0,
        }
    )
    with pytest.raises(ValueError, match="wheel_radius_m"):
        builder.diagnostic_residual_records(vector)


def test_regenerative_brake_split_residual_key_and_role() -> None:
    builder = ResidualBuilder(one_module("RegenerativeBrakeSplitModule", {}))
    registry = builder.build_registry()
    records = builder.diagnostic_residual_records(registry.initial_vector())
    keys = {record.diagnostic_key for record in records}
    assert "regen_brake_power_split_mismatch" in keys
    assert "friction_brake_power_split_mismatch" in keys
    assert "brake_power_balance_mismatch" in keys
    assert all(record.role == "equation" for record in records)
