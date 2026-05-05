from __future__ import annotations

from pathlib import Path

import math

import pytest

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]


def system(components: list[dict]) -> SystemSpec:
    return SystemSpec.model_validate({"system_name": "fluid", "components": components})


def one_module(module_type: str, parameters: dict) -> SystemSpec:
    return system([{"id": "m", "type": module_type, "parameters": parameters}])


def records_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)


def solve_example(name: str):
    spec = load_system_spec(ROOT / "examples" / "foundation" / name)
    return spec, BoundedSolver(ResidualBuilder(spec), spec.solver).solve()


def test_pressure_drop_zero_residual_and_reverse_flow_sign() -> None:
    spec = one_module(
        "IncompressiblePressureDropModule",
        {"K": 2.0, "rho_kg_m3": 1000.0, "area_m2": 0.01, "residual_scale_Pa": 1.0},
    )
    record = records_for(
        spec,
        {"m.p_in_Pa": 100010.0, "m.p_out_Pa": 100000.0, "m.m_dot_kg_s": 1.0},
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "incompressible_pressure_drop_mismatch"
    assert record.role == "equation"

    reverse = records_for(
        spec,
        {"m.p_in_Pa": 100010.0, "m.p_out_Pa": 100000.0, "m.m_dot_kg_s": -1.0},
    )[0]
    assert reverse.value == pytest.approx(20.0)


@pytest.mark.parametrize(
    ("parameters", "match"),
    [
        ({"K": -1.0, "rho_kg_m3": 1000.0, "area_m2": 0.01}, "K"),
        ({"K": 1.0, "rho_kg_m3": 0.0, "area_m2": 0.01}, "rho_kg_m3"),
        ({"K": 1.0, "rho_kg_m3": 1000.0, "area_m2": 0.0}, "area_m2"),
    ],
)
def test_pressure_drop_invalid_parameters_fail(parameters: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        ResidualBuilder(one_module("IncompressiblePressureDropModule", parameters)).build_registry()


def test_orifice_zero_residual_and_negative_pressure_difference_large() -> None:
    spec = one_module(
        "IncompressibleOrificeModule",
        {"CdA_m2": 0.001, "rho_kg_m3": 1000.0},
    )
    m_dot = math.sqrt(10.0)
    record = records_for(
        spec,
        {
            "m.p_upstream_Pa": 105000.0,
            "m.p_downstream_Pa": 100000.0,
            "m.m_dot_kg_s": m_dot,
        },
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "incompressible_orifice_mismatch"
    assert record.role == "equation"

    negative_dp = records_for(
        spec,
        {
            "m.p_upstream_Pa": 100000.0,
            "m.p_downstream_Pa": 105000.0,
            "m.m_dot_kg_s": 0.0,
        },
    )[0]
    assert negative_dp.abs_normalized_value > 1000.0


@pytest.mark.parametrize(
    ("parameters", "match"),
    [
        ({"CdA_m2": 0.0, "rho_kg_m3": 1000.0}, "CdA_m2"),
        ({"CdA_m2": 0.001, "rho_kg_m3": 0.0}, "rho_kg_m3"),
    ],
)
def test_orifice_invalid_parameters_fail(parameters: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        ResidualBuilder(one_module("IncompressibleOrificeModule", parameters)).build_registry()


def test_mass_balance_zero_and_nonzero_residual() -> None:
    spec = system(
        [
            {"id": "i", "type": "DummyResidualModule", "parameters": {"target": 1.0}},
            {"id": "o", "type": "DummyResidualModule", "parameters": {"target": 1.0}},
            {
                "id": "bal",
                "type": "MassBalanceRateModule",
                "parameters": {"input_variables": ["i.x"], "output_variables": ["o.x"]},
            },
        ]
    )
    balance = [
        record
        for record in records_for(spec, {"i.x": 1.0, "o.x": 1.0})
        if record.diagnostic_key == "mass_balance_rate_mismatch"
    ][0]
    assert balance.value == pytest.approx(0.0)
    assert balance.role == "equation"

    unbalanced = [
        record
        for record in records_for(spec, {"i.x": 1.0, "o.x": 0.8})
        if record.diagnostic_key == "mass_balance_rate_mismatch"
    ][0]
    assert unbalanced.value == pytest.approx(0.2)


def test_mass_balance_missing_referenced_variable_fails() -> None:
    spec = system(
        [
            {"id": "i", "type": "DummyResidualModule", "parameters": {"target": 1.0}},
            {
                "id": "bal",
                "type": "MassBalanceRateModule",
                "parameters": {"input_variables": ["i.x"], "output_variables": ["missing.x"]},
            },
        ]
    )
    with pytest.raises(KeyError, match="MassBalanceRateModule"):
        ResidualBuilder(spec).residual_vector(ResidualBuilder(spec).build_registry().initial_vector())


def test_mass_balance_invalid_parameters_fail() -> None:
    spec = system(
        [
            {
                "id": "bal",
                "type": "MassBalanceRateModule",
                "parameters": {"input_variables": ["a.x"]},
            },
        ]
    )
    with pytest.raises(ValueError, match="output_variables"):
        ResidualBuilder(spec).build_registry()


def mixer_system() -> SystemSpec:
    return system(
        [
            {"id": "m1", "type": "DummyResidualModule", "parameters": {"target": 1.0}},
            {"id": "m2", "type": "DummyResidualModule", "parameters": {"target": 3.0}},
            {
                "id": "t1",
                "type": "DummyResidualModule",
                "parameters": {
                    "target": 300.0,
                    "lower_bound": 200.0,
                    "upper_bound": 1000.0,
                    "initial_guess": 300.0,
                },
            },
            {
                "id": "t2",
                "type": "DummyResidualModule",
                "parameters": {
                    "target": 340.0,
                    "lower_bound": 200.0,
                    "upper_bound": 1000.0,
                    "initial_guess": 340.0,
                },
            },
            {"id": "mo", "type": "DummyResidualModule", "parameters": {"target": 4.0}},
            {
                "id": "to",
                "type": "DummyResidualModule",
                "parameters": {
                    "target": 330.0,
                    "lower_bound": 200.0,
                    "upper_bound": 1000.0,
                    "initial_guess": 330.0,
                },
            },
            {
                "id": "mix",
                "type": "MixerEnergyBalanceModule",
                "parameters": {
                    "inlet_m_dot_variables": ["m1.x", "m2.x"],
                    "inlet_T_variables": ["t1.x", "t2.x"],
                    "outlet_m_dot_variable": "mo.x",
                    "outlet_T_variable": "to.x",
                },
            },
        ]
    )


def test_mixer_zero_residual_for_weighted_temperature() -> None:
    records = records_for(
        mixer_system(),
        {
            "m1.x": 1.0,
            "m2.x": 3.0,
            "t1.x": 300.0,
            "t2.x": 340.0,
            "mo.x": 4.0,
            "to.x": 330.0,
        },
    )
    mixer_records = [record for record in records if record.source == "mix"]
    assert [record.value for record in mixer_records] == pytest.approx([0.0, 0.0])
    assert {record.diagnostic_key for record in mixer_records} == {
        "mixer_mass_balance_mismatch",
        "mixer_energy_balance_mismatch",
    }


def test_mixer_inconsistent_outlet_temperature_produces_residual() -> None:
    records = records_for(
        mixer_system(),
        {
            "m1.x": 1.0,
            "m2.x": 3.0,
            "t1.x": 300.0,
            "t2.x": 340.0,
            "mo.x": 4.0,
            "to.x": 300.0,
        },
    )
    energy = [
        record for record in records if record.diagnostic_key == "mixer_energy_balance_mismatch"
    ][0]
    assert energy.value == pytest.approx(-120.0)


def test_mixer_missing_variable_fails() -> None:
    spec = system(
        [
            {"id": "m1", "type": "DummyResidualModule", "parameters": {"target": 1.0}},
            {
                "id": "mix",
                "type": "MixerEnergyBalanceModule",
                "parameters": {
                    "inlet_m_dot_variables": ["m1.x"],
                    "inlet_T_variables": ["missing.x"],
                    "outlet_m_dot_variable": "m1.x",
                    "outlet_T_variable": "missing.y",
                },
            },
        ]
    )
    with pytest.raises(KeyError, match="MixerEnergyBalanceModule"):
        ResidualBuilder(spec).residual_vector(ResidualBuilder(spec).build_registry().initial_vector())


def test_mixer_invalid_parameters_fail() -> None:
    spec = system(
        [
            {
                "id": "mix",
                "type": "MixerEnergyBalanceModule",
                "parameters": {
                    "inlet_m_dot_variables": ["a.x", "b.x"],
                    "inlet_T_variables": ["ta.x"],
                    "outlet_m_dot_variable": "out.x",
                    "outlet_T_variable": "tout.x",
                },
            },
        ]
    )
    with pytest.raises(ValueError, match="same length"):
        ResidualBuilder(spec).build_registry()


def test_pump_hydraulic_power_zero_residual() -> None:
    spec = one_module("PumpHydraulicPowerModule", {"rho_kg_m3": 1000.0, "efficiency": 0.8})
    record = records_for(
        spec,
        {
            "m.p_out_Pa": 200000.0,
            "m.p_in_Pa": 100000.0,
            "m.m_dot_kg_s": 1.0,
            "m.P_shaft_W": 125.0,
        },
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "pump_hydraulic_power_mismatch"
    assert record.role == "equation"


@pytest.mark.parametrize(
    ("parameters", "match"),
    [
        ({"rho_kg_m3": 0.0, "efficiency": 0.8}, "rho_kg_m3"),
        ({"rho_kg_m3": 1000.0, "efficiency": 0.0}, "efficiency"),
        ({"rho_kg_m3": 1000.0, "efficiency": 1.5}, "efficiency"),
    ],
)
def test_pump_invalid_parameters_fail(parameters: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        ResidualBuilder(one_module("PumpHydraulicPowerModule", parameters)).build_registry()


@pytest.mark.parametrize(
    "example",
    [
        "incompressible_pressure_drop.yaml",
        "incompressible_orifice.yaml",
        "mass_balance_rate.yaml",
        "mixer_energy_balance.yaml",
        "pump_hydraulic_power.yaml",
    ],
)
def test_fluid_foundation_yaml_examples_solve(example: str) -> None:
    _, result = solve_example(example)
    assert result.optimization_success
    assert result.audit_pass


def test_conflict_mass_balance_fails_audit() -> None:
    spec, result = solve_example("conflict_mass_balance.yaml")
    report = DiagnosticReporter().generate(spec, ResidualBuilder(spec), result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "mass_balance_rate_mismatch"
