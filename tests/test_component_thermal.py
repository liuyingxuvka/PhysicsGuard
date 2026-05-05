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


def test_registry_includes_component_thermal_modules() -> None:
    assert {"RadiatorSimpleModule", "RadiatorFanSimpleModule", "HumidifierEffectivenessModule", "IntercoolerSimpleModule"}.issubset(
        set(default_module_registry().registered_types())
    )


def test_radiator_simple_zero_residual_and_invalid_parameters() -> None:
    records = records_for(
        one_module("RadiatorSimpleModule", {"cp_coolant_J_kgK": 1000.0, "UA_W_K": 333.3333333333333}),
        {
            "m.m_dot_coolant_kg_s": 1.0,
            "m.T_coolant_in_K": 330.0,
            "m.T_coolant_out_K": 320.0,
            "m.T_air_in_K": 300.0,
            "m.Q_rejected_W": 10000.0,
            "m.fan_power_W": 0.0,
        },
    )
    assert all(record.value == pytest.approx(0.0) for record in records)
    assert {r.diagnostic_key for r in records} == {
        "radiator_coolant_heat_balance_mismatch",
        "radiator_ua_heat_rejection_mismatch",
    }
    with pytest.raises(ValueError, match="UA_W_K"):
        ResidualBuilder(one_module("RadiatorSimpleModule", {"UA_W_K": -1.0})).build_registry()


def test_radiator_fan_zero_residual_and_invalid_parameters() -> None:
    records = records_for(
        one_module("RadiatorFanSimpleModule", {"max_air_m_dot_kg_s": 2.0, "max_fan_power_W": 1000.0}),
        {"m.fan_command": 0.5, "m.air_m_dot_kg_s": 1.0, "m.fan_power_W": 125.0},
    )
    assert all(record.value == pytest.approx(0.0) for record in records)
    with pytest.raises(ValueError, match="max_air_m_dot_kg_s"):
        ResidualBuilder(
            one_module("RadiatorFanSimpleModule", {"max_air_m_dot_kg_s": -1.0, "max_fan_power_W": 1000.0})
        ).build_registry()


def test_humidifier_effectiveness_zero_residual_and_invalid_effectiveness() -> None:
    records = records_for(
        one_module("HumidifierEffectivenessModule", {"effectiveness": 0.5}),
        {
            "m.m_dot_dry_air_kg_s": 1.0,
            "m.humidity_ratio_in_kg_kg": 0.01,
            "m.humidity_ratio_out_kg_kg": 0.02,
            "m.humidity_ratio_target_kg_kg": 0.03,
            "m.water_transfer_kg_s": 0.01,
        },
    )
    assert all(record.value == pytest.approx(0.0) for record in records)
    assert {r.diagnostic_key for r in records} == {
        "humidifier_effectiveness_mismatch",
        "humidifier_water_transfer_mismatch",
    }
    with pytest.raises(ValueError, match="effectiveness"):
        ResidualBuilder(one_module("HumidifierEffectivenessModule", {"effectiveness": 1.1})).build_registry()


def test_intercooler_simple_zero_residual_and_invalid_parameters() -> None:
    records = records_for(
        one_module("IntercoolerSimpleModule", {"cp_gas_J_kgK": 1000.0, "UA_W_K": 571.4285714285714}),
        {
            "m.m_dot_gas_kg_s": 1.0,
            "m.T_gas_in_K": 370.0,
            "m.T_gas_out_K": 330.0,
            "m.T_coolant_or_ambient_K": 300.0,
            "m.Q_removed_W": 40000.0,
        },
    )
    assert all(record.value == pytest.approx(0.0) for record in records)
    with pytest.raises(ValueError, match="cp_gas_J_kgK"):
        ResidualBuilder(one_module("IntercoolerSimpleModule", {"cp_gas_J_kgK": 0.0, "UA_W_K": 1.0})).build_registry()


@pytest.mark.parametrize(
    "name",
    ["radiator_simple.yaml", "radiator_fan_simple.yaml", "humidifier_effectiveness.yaml", "intercooler_simple.yaml"],
)
def test_component_thermal_yaml_examples_solve(name: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "components" / "thermal" / name)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("conflict_radiator_simple.yaml", {"radiator_coolant_heat_balance_mismatch", "radiator_ua_heat_rejection_mismatch"}),
        ("conflict_humidifier_effectiveness.yaml", {"humidifier_effectiveness_mismatch", "humidifier_water_transfer_mismatch"}),
    ],
)
def test_component_thermal_conflicts_fail_audit(name: str, expected: set[str]) -> None:
    spec = load_system_spec(ROOT / "examples" / "components" / "thermal" / name)
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key in expected
