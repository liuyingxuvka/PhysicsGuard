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


def test_registry_includes_component_electric_modules() -> None:
    assert {
        "ElectricMotorSimpleModule",
        "ElectricMotorMapModule",
        "DCDCConverterSimpleModule",
        "InverterSimpleModule",
    }.issubset(set(default_module_registry().registered_types()))


def test_electric_motor_simple_zero_and_conflict_residual() -> None:
    records = records_for(
        one_module("ElectricMotorSimpleModule", {}),
        {
            "m.voltage_V": 400.0,
            "m.current_A": 10.0,
            "m.electrical_power_W": 4000.0,
            "m.torque_Nm": 30.0,
            "m.omega_rad_s": 100.0,
            "m.mechanical_power_W": 3000.0,
            "m.efficiency": 0.75,
        },
    )
    assert {record.diagnostic_key for record in records} == {
        "motor_electrical_power_mismatch",
        "motor_mechanical_power_mismatch",
        "motor_efficiency_power_mismatch",
    }
    assert all(record.value == pytest.approx(0.0) for record in records)
    conflict = records_for(
        one_module("ElectricMotorSimpleModule", {}),
        {
            "m.voltage_V": 400.0,
            "m.current_A": 10.0,
            "m.electrical_power_W": 4000.0,
            "m.torque_Nm": 30.0,
            "m.omega_rad_s": 100.0,
            "m.mechanical_power_W": 3000.0,
            "m.efficiency": 0.2,
        },
    )
    assert [r for r in conflict if r.diagnostic_key == "motor_efficiency_power_mismatch"][0].value == pytest.approx(2200.0)


def test_electric_motor_map_interpolation_and_invalid_map() -> None:
    spec = one_module(
        "ElectricMotorMapModule",
        {
            "torque_points": [0.0, 60.0],
            "omega_points": [0.0, 200.0],
            "efficiency_values": [[0.8, 0.85], [0.85, 0.9]],
        },
    )
    records = records_for(
        spec,
        {
            "m.torque_Nm": 30.0,
            "m.omega_rad_s": 100.0,
            "m.efficiency": 0.85,
            "m.electrical_power_W": 3000.0 / 0.85,
            "m.mechanical_power_W": 3000.0,
        },
    )
    assert all(record.value == pytest.approx(0.0) for record in records)
    assert {record.role for record in records} == {"equation"}
    with pytest.raises(ValueError, match="efficiency_values"):
        ResidualBuilder(
            one_module(
                "ElectricMotorMapModule",
                {"torque_points": [0.0, 1.0], "omega_points": [0.0, 1.0], "efficiency_values": [[0.8]]},
            )
        ).build_registry()


def test_dcdc_and_inverter_zero_residuals_and_invalid_scale() -> None:
    dcdc = records_for(
        one_module("DCDCConverterSimpleModule", {}),
        {
            "m.V_in_V": 400.0,
            "m.I_in_A": 10.0,
            "m.P_in_W": 4000.0,
            "m.V_out_V": 200.0,
            "m.I_out_A": 18.0,
            "m.P_out_W": 3600.0,
            "m.efficiency": 0.9,
        },
    )
    assert all(record.value == pytest.approx(0.0) for record in dcdc)
    inverter = records_for(
        one_module("InverterSimpleModule", {}),
        {"m.P_dc_W": 4000.0, "m.P_ac_W": 3600.0, "m.efficiency": 0.9},
    )[0]
    assert inverter.value == pytest.approx(0.0)
    assert inverter.diagnostic_key == "inverter_efficiency_power_mismatch"

    with pytest.raises(ValueError, match="residual_scale_power_W"):
        ResidualBuilder(one_module("DCDCConverterSimpleModule", {"residual_scale_power_W": 0.0})).build_registry()


@pytest.mark.parametrize(
    "name",
    [
        "electric_motor_simple.yaml",
        "electric_motor_map.yaml",
        "dcdc_converter_simple.yaml",
        "inverter_simple.yaml",
    ],
)
def test_component_electric_yaml_examples_solve(name: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "components" / "electric" / name)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass


def test_conflict_electric_motor_simple_fails_audit() -> None:
    spec = load_system_spec(ROOT / "examples" / "components" / "electric" / "conflict_electric_motor_simple.yaml")
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "motor_efficiency_power_mismatch"
