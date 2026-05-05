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
        {
            "system_name": module_type,
            "components": [{"id": "m", "type": module_type, "parameters": parameters}],
        }
    )


def record_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)[0]


def test_default_registry_includes_additional_physical_modules() -> None:
    registered = set(default_module_registry().registered_types())
    assert {
        "PressureRatioModule",
        "EfficiencyModule",
        "TorqueSpeedPowerModule",
        "CellVoltageStackVoltageModule",
        "CurrentDensityModule",
    }.issubset(registered)


def test_pressure_ratio_zero_residual() -> None:
    record = record_for(
        one_module("PressureRatioModule", {}),
        {"m.p_in_Pa": 100000.0, "m.p_out_Pa": 200000.0, "m.pressure_ratio": 2.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "pressure_ratio_mismatch"
    assert record.role == "equation"


def test_pressure_ratio_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="denominator_min_abs"):
        ResidualBuilder(one_module("PressureRatioModule", {"denominator_min_abs": 0.0})).build_registry()


def test_efficiency_zero_residual() -> None:
    record = record_for(
        one_module("EfficiencyModule", {}),
        {"m.input_power_W": 1000.0, "m.useful_output_power_W": 800.0, "m.efficiency": 0.8},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "efficiency_mismatch"
    assert record.role == "equation"


def test_efficiency_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="denominator_min_abs"):
        ResidualBuilder(one_module("EfficiencyModule", {"denominator_min_abs": 0.0})).build_registry()


def test_torque_speed_power_zero_residual() -> None:
    record = record_for(
        one_module("TorqueSpeedPowerModule", {}),
        {"m.torque_Nm": 10.0, "m.omega_rad_s": 100.0, "m.P_W": 1000.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "torque_speed_power_mismatch"
    assert record.role == "equation"


def test_torque_speed_power_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="residual_scale_W"):
        ResidualBuilder(one_module("TorqueSpeedPowerModule", {"residual_scale_W": 0.0})).build_registry()


def test_cell_stack_voltage_zero_residual() -> None:
    record = record_for(
        one_module("CellVoltageStackVoltageModule", {"n_cells": 400.0}),
        {"m.V_cell_V": 0.7, "m.V_stack_V": 280.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "cell_stack_voltage_mismatch"
    assert record.role == "equation"


def test_cell_stack_voltage_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="n_cells"):
        ResidualBuilder(one_module("CellVoltageStackVoltageModule", {"n_cells": 0.0})).build_registry()


def test_current_density_zero_residual() -> None:
    record = record_for(
        one_module("CurrentDensityModule", {"active_area_m2": 0.1}),
        {"m.current_A": 100.0, "m.current_density_A_m2": 1000.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "current_density_mismatch"
    assert record.role == "equation"


def test_current_density_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="active_area_m2"):
        ResidualBuilder(one_module("CurrentDensityModule", {"active_area_m2": 0.0})).build_registry()


@pytest.mark.parametrize(
    "example",
    [
        "pressure_ratio.yaml",
        "efficiency.yaml",
        "torque_speed_power.yaml",
        "cell_stack_voltage.yaml",
        "current_density.yaml",
    ],
)
def test_additional_yaml_examples_solve(example: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "additional" / example)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass


def test_conflict_pressure_ratio_fails_audit() -> None:
    spec = load_system_spec(ROOT / "examples" / "additional" / "conflict_pressure_ratio.yaml")
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "pressure_ratio_mismatch"
