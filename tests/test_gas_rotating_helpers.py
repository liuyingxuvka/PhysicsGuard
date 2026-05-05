from __future__ import annotations

from pathlib import Path

import pytest

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


def records_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)


def compressor_power(
    p_in: float = 100000.0,
    p_out: float = 200000.0,
    t_in: float = 300.0,
    m_dot: float = 0.1,
    cp: float = 1000.0,
    gamma: float = 1.4,
    efficiency: float = 0.7,
) -> float:
    pressure_ratio = p_out / p_in
    exponent = (gamma - 1.0) / gamma
    return m_dot * cp * t_in * (pressure_ratio**exponent - 1.0) / efficiency


def outlet_temperature(
    p_in: float = 100000.0,
    p_out: float = 200000.0,
    t_in: float = 300.0,
    gamma: float = 1.4,
    efficiency: float = 0.7,
) -> float:
    pressure_ratio = p_out / p_in
    exponent = (gamma - 1.0) / gamma
    return t_in * (1.0 + (pressure_ratio**exponent - 1.0) / efficiency)


def test_default_registry_includes_gas_rotating_helpers() -> None:
    registered = set(default_module_registry().registered_types())
    assert {
        "CompressibleIsentropicCompressorPowerModule",
        "IsentropicGasTemperatureRiseModule",
        "RotatingMachineAffinityModule",
    }.issubset(registered)


def test_compressor_power_zero_residual_and_low_pressure_ratio_finite() -> None:
    spec = one_module(
        "CompressibleIsentropicCompressorPowerModule",
        {"cp_J_kgK": 1000.0, "gamma": 1.4, "efficiency": 0.7},
    )
    record = records_for(
        spec,
        {
            "m.p_in_Pa": 100000.0,
            "m.p_out_Pa": 200000.0,
            "m.T_in_K": 300.0,
            "m.m_dot_kg_s": 0.1,
            "m.P_shaft_W": compressor_power(),
        },
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "compressible_isentropic_compressor_power_mismatch"
    assert record.role == "equation"

    low_ratio = records_for(
        spec,
        {
            "m.p_in_Pa": 200000.0,
            "m.p_out_Pa": 100000.0,
            "m.T_in_K": 300.0,
            "m.m_dot_kg_s": 0.1,
            "m.P_shaft_W": compressor_power(p_in=200000.0, p_out=100000.0),
        },
    )[0]
    assert low_ratio.value == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("parameters", "match"),
    [
        ({"cp_J_kgK": 0.0}, "cp_J_kgK"),
        ({"gamma": 1.0}, "gamma"),
        ({"efficiency": 0.0}, "efficiency"),
        ({"efficiency": 1.1}, "efficiency"),
    ],
)
def test_compressor_power_invalid_parameters_fail(parameters: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        ResidualBuilder(one_module("CompressibleIsentropicCompressorPowerModule", parameters)).build_registry()


def test_isentropic_temperature_rise_zero_residual_and_invalid_parameters() -> None:
    record = records_for(
        one_module("IsentropicGasTemperatureRiseModule", {"gamma": 1.4, "efficiency": 0.7}),
        {
            "m.p_in_Pa": 100000.0,
            "m.p_out_Pa": 200000.0,
            "m.T_in_K": 300.0,
            "m.T_out_K": outlet_temperature(),
        },
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "isentropic_gas_temperature_rise_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="gamma"):
        ResidualBuilder(one_module("IsentropicGasTemperatureRiseModule", {"gamma": 1.0})).build_registry()


def test_rotating_machine_affinity_zero_residual_and_invalid_nominal_speed() -> None:
    records = records_for(
        one_module(
            "RotatingMachineAffinityModule",
            {
                "nominal_speed_rad_s": 100.0,
                "nominal_m_dot_kg_s": 1.0,
                "nominal_delta_p_Pa": 100000.0,
                "nominal_P_shaft_W": 1000.0,
            },
        ),
        {
            "m.speed_rad_s": 50.0,
            "m.m_dot_kg_s": 0.5,
            "m.delta_p_Pa": 25000.0,
            "m.P_shaft_W": 125.0,
        },
    )
    assert {record.diagnostic_key for record in records} == {
        "rotating_machine_affinity_flow_mismatch",
        "rotating_machine_affinity_pressure_mismatch",
        "rotating_machine_affinity_power_mismatch",
    }
    assert all(record.value == pytest.approx(0.0) for record in records)
    assert all(record.role == "equation" for record in records)

    with pytest.raises(ValueError, match="nominal_speed_rad_s"):
        ResidualBuilder(
            one_module(
                "RotatingMachineAffinityModule",
                {
                    "nominal_speed_rad_s": 0.0,
                    "nominal_m_dot_kg_s": 1.0,
                    "nominal_delta_p_Pa": 100000.0,
                    "nominal_P_shaft_W": 1000.0,
                },
            )
        ).build_registry()


@pytest.mark.parametrize(
    "example",
    [
        "compressible_isentropic_compressor_power.yaml",
        "isentropic_gas_temperature_rise.yaml",
        "rotating_machine_affinity.yaml",
    ],
)
def test_gas_rotating_yaml_examples_solve(example: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "foundation" / example)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
