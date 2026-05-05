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
EXAMPLES = ROOT / "examples" / "components" / "engine_aftertreatment"


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


def test_registry_includes_engine_aftertreatment_modules() -> None:
    assert {
        "EngineTorqueMapModule",
        "EngineAirFuelRatioModule",
        "EngineVolumetricEfficiencyModule",
        "EngineExhaustHeatFlowModule",
        "EGRMixingModule",
        "TurboPowerBalanceModule",
        "CatalystThermalMassStepModule",
        "AftertreatmentPressureDropModule",
    }.issubset(set(default_module_registry().registered_types()))


@pytest.mark.parametrize(
    "name",
    [
        "engine_torque_map.yaml",
        "engine_air_fuel_ratio.yaml",
        "engine_volumetric_efficiency.yaml",
        "engine_exhaust_heat_flow.yaml",
        "egr_mixing.yaml",
        "turbo_power_balance.yaml",
        "catalyst_thermal_mass_step.yaml",
        "aftertreatment_pressure_drop.yaml",
    ],
)
def test_engine_aftertreatment_clean_examples_solve(name: str) -> None:
    result, report = solve_example(name)
    assert result.optimization_success
    assert result.audit_pass
    assert np.isfinite(result.max_abs_normalized_residual)
    assert all(item.role in {"equation", "boundary"} for item in report.top_residuals)


def test_engine_air_fuel_ratio_conflict_fails_audit() -> None:
    result, report = solve_example("conflict_engine_air_fuel_ratio.yaml")
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "engine_air_fuel_ratio_mismatch"


@pytest.mark.parametrize(
    ("module_type", "parameters", "message"),
    [
        (
            "EngineTorqueMapModule",
            {"speed_points_rad_s": [0.0, 0.0], "load_points": [0.0, 1.0], "torque_values_Nm": [[0.0, 0.0], [1.0, 1.0]]},
            "speed_points_rad_s",
        ),
        (
            "EngineTorqueMapModule",
            {"speed_points_rad_s": [0.0, 1.0], "load_points": [0.0, 1.0], "torque_values_Nm": [[0.0, 0.0]]},
            "torque_values_Nm",
        ),
        ("EngineVolumetricEfficiencyModule", {"displacement_m3_per_rev": 0.0}, "displacement_m3_per_rev"),
        ("EngineExhaustHeatFlowModule", {"cp_exhaust_J_kgK": 0.0}, "cp_exhaust_J_kgK"),
        ("CatalystThermalMassStepModule", {"C_J_K": 0.0, "dt_s": 1.0}, "C_J_K"),
        ("CatalystThermalMassStepModule", {"C_J_K": 1.0, "dt_s": 0.0}, "dt_s"),
        ("AftertreatmentPressureDropModule", {"K_Pa_per_kg2_s2": -1.0}, "K_Pa_per_kg2_s2"),
    ],
)
def test_engine_aftertreatment_invalid_parameters_fail(module_type: str, parameters: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ResidualBuilder(one_module(module_type, parameters)).build_registry()


def test_engine_torque_map_bilinear_interpolation_has_zero_residual() -> None:
    spec = one_module(
        "EngineTorqueMapModule",
        {
            "speed_points_rad_s": [0.0, 200.0],
            "load_points": [0.0, 1.0],
            "torque_values_Nm": [[0.0, 0.0], [100.0, 200.0]],
            "extrapolation": "hold",
        },
    )
    builder = ResidualBuilder(spec)
    registry = builder.build_registry()
    vector = registry.dict_to_vector({"m.speed_rad_s": 100.0, "m.load_command": 0.5, "m.torque_Nm": 75.0})
    records = builder.diagnostic_residual_records(vector)
    assert records[0].diagnostic_key == "engine_torque_map_mismatch"
    assert records[0].role == "equation"
    assert records[0].normalized_value == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("module_type", "values", "message"),
    [
        (
            "EngineAirFuelRatioModule",
            {"m.m_dot_air_kg_s": 0.1, "m.m_dot_fuel_kg_s": 0.0, "m.AFR": 0.0},
            "m_dot_fuel_kg_s",
        ),
        (
            "EGRMixingModule",
            {
                "m.m_dot_fresh_air_kg_s": 0.0,
                "m.T_fresh_air_K": 300.0,
                "m.m_dot_egr_kg_s": 0.0,
                "m.T_egr_K": 700.0,
                "m.m_dot_mixed_kg_s": 0.0,
                "m.T_mixed_K": 300.0,
                "m.egr_fraction": 0.0,
            },
            "m_dot_mixed_kg_s",
        ),
    ],
)
def test_engine_aftertreatment_denominators_fail_clearly(module_type: str, values: dict[str, float], message: str) -> None:
    builder = ResidualBuilder(one_module(module_type, {}))
    registry = builder.build_registry()
    vector = registry.dict_to_vector(values)
    with pytest.raises(ValueError, match=message):
        builder.diagnostic_residual_records(vector)
