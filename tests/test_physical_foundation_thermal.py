from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]


def system(module_type: str, parameters: dict) -> SystemSpec:
    return SystemSpec.model_validate(
        {
            "system_name": module_type,
            "components": [
                {"id": "m", "type": module_type, "parameters": parameters},
            ],
        }
    )


def residual_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)[0]


def solve_example(name: str):
    spec = load_system_spec(ROOT / "examples" / "foundation" / name)
    return spec, BoundedSolver(ResidualBuilder(spec), spec.solver).solve()


def test_thermal_conductor_zero_residual_and_sign() -> None:
    spec = system("ThermalConductorModule", {"G_W_K": 50.0})
    record = residual_for(
        spec,
        {"m.T_a_K": 320.0, "m.T_b_K": 300.0, "m.Q_dot_W": 1000.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.role == "equation"
    assert record.diagnostic_key == "thermal_conductor_mismatch"

    negative = residual_for(
        spec,
        {"m.T_a_K": 320.0, "m.T_b_K": 300.0, "m.Q_dot_W": 800.0},
    )
    assert negative.value == pytest.approx(-200.0)


def test_thermal_conductor_invalid_g_fails() -> None:
    with pytest.raises(ValueError, match="G_W_K"):
        ResidualBuilder(system("ThermalConductorModule", {"G_W_K": 0.0})).build_registry()


def test_convection_zero_residual() -> None:
    spec = system(
        "ConvectiveHeatTransferModule",
        {"h_W_m2K": 100.0, "area_m2": 0.5},
    )
    record = residual_for(
        spec,
        {"m.T_surface_K": 330.0, "m.T_fluid_K": 300.0, "m.Q_dot_W": 1500.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "convective_heat_transfer_mismatch"
    assert record.role == "equation"


@pytest.mark.parametrize(
    ("parameters", "match"),
    [
        ({"h_W_m2K": 0.0, "area_m2": 0.5}, "h_W_m2K"),
        ({"h_W_m2K": 100.0, "area_m2": 0.0}, "area_m2"),
    ],
)
def test_convection_invalid_parameters_fail(parameters: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        ResidualBuilder(system("ConvectiveHeatTransferModule", parameters)).build_registry()


def test_thermal_capacitance_rate_zero_residual() -> None:
    spec = system("ThermalCapacitanceRateModule", {"C_J_K": 500.0})
    record = residual_for(spec, {"m.Q_net_W": 1000.0, "m.dT_dt_K_s": 2.0})
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "thermal_capacitance_rate_mismatch"
    assert record.role == "equation"


def test_thermal_capacitance_rate_invalid_c_fails() -> None:
    with pytest.raises(ValueError, match="C_J_K"):
        ResidualBuilder(system("ThermalCapacitanceRateModule", {"C_J_K": 0.0})).build_registry()


@pytest.mark.parametrize(
    "example",
    [
        "thermal_conductor.yaml",
        "convection.yaml",
        "thermal_capacitance_rate.yaml",
    ],
)
def test_thermal_foundation_yaml_examples_solve(example: str) -> None:
    _, result = solve_example(example)
    assert result.optimization_success
    assert result.audit_pass


def test_conflict_thermal_conductor_fails_audit() -> None:
    spec, result = solve_example("conflict_thermal_conductor.yaml")
    report = DiagnosticReporter().generate(spec, ResidualBuilder(spec), result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "thermal_conductor_mismatch"
