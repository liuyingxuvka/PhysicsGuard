from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.modules.registry import default_module_registry
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]


def one_module(module_type: str, parameters: dict) -> SystemSpec:
    return SystemSpec.model_validate(
        {"system_name": module_type, "components": [{"id": "m", "type": module_type, "parameters": parameters}]}
    )


def records_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)


def test_registry_includes_component_engine_modules() -> None:
    assert {"EngineSimpleEfficiencyModule", "EngineBSFCMapModule"}.issubset(
        set(default_module_registry().registered_types())
    )


def test_engine_simple_efficiency_zero_residual_and_conflict_key() -> None:
    records = records_for(
        one_module("EngineSimpleEfficiencyModule", {}),
        {
            "m.fuel_m_dot_kg_s": 0.001,
            "m.LHV_J_kg": 50_000_000.0,
            "m.brake_power_W": 10_000.0,
            "m.thermal_efficiency": 0.2,
            "m.torque_Nm": 100.0,
            "m.omega_rad_s": 100.0,
        },
    )
    assert all(record.value == pytest.approx(0.0) for record in records)
    assert {record.diagnostic_key for record in records} == {
        "engine_torque_speed_power_mismatch",
        "engine_fuel_efficiency_mismatch",
    }
    assert all(record.role == "equation" for record in records)

    conflict = records_for(
        one_module("EngineSimpleEfficiencyModule", {}),
        {
            "m.fuel_m_dot_kg_s": 0.001,
            "m.LHV_J_kg": 50_000_000.0,
            "m.brake_power_W": 50_000.0,
            "m.thermal_efficiency": 0.2,
            "m.torque_Nm": 100.0,
            "m.omega_rad_s": 100.0,
        },
    )
    assert max(record.abs_normalized_value for record in conflict) > 1.0


def test_engine_bsfc_map_interpolation_and_invalid_map() -> None:
    records = records_for(
        one_module(
            "EngineBSFCMapModule",
            {
                "speed_points_rad_s": [0.0, 200.0],
                "torque_points_Nm": [0.0, 200.0],
                "bsfc_values_kg_J": [[2e-8, 4e-8], [4e-8, 6e-8]],
            },
        ),
        {
            "m.speed_rad_s": 100.0,
            "m.torque_Nm": 100.0,
            "m.brake_power_W": 10_000.0,
            "m.fuel_m_dot_kg_s": 0.0004,
            "m.bsfc_kg_J": 4e-8,
        },
    )
    assert all(record.value == pytest.approx(0.0) for record in records)
    assert {record.diagnostic_key for record in records} == {
        "engine_bsfc_power_mismatch",
        "engine_bsfc_fuel_flow_mismatch",
        "engine_bsfc_map_mismatch",
    }
    assert all(record.role == "equation" for record in records)

    with pytest.raises(ValueError, match="bsfc_values_kg_J"):
        ResidualBuilder(
            one_module(
                "EngineBSFCMapModule",
                {
                    "speed_points_rad_s": [0.0, 200.0],
                    "torque_points_Nm": [0.0, 200.0],
                    "bsfc_values_kg_J": [[2e-8, 4e-8]],
                },
            )
        ).build_registry()


@pytest.mark.parametrize("name", ["engine_simple_efficiency.yaml", "engine_bsfc_map.yaml"])
def test_component_engine_yaml_examples_solve(name: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "components" / "engine" / name)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass


def test_conflict_engine_simple_efficiency_fails_audit() -> None:
    spec = load_system_spec(ROOT / "examples" / "components" / "engine" / "conflict_engine_simple_efficiency.yaml")
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key in {
        "engine_torque_speed_power_mismatch",
        "engine_fuel_efficiency_mismatch",
    }
