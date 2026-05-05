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


def records_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)


def test_default_registry_includes_heat_exchanger_helpers() -> None:
    registered = set(default_module_registry().registered_types())
    assert {
        "HeatExchangerEffectivenessModule",
        "RadiativeHeatTransferModule",
        "AmbientHeatLossModule",
    }.issubset(registered)


def test_heat_exchanger_effectiveness_zero_residual() -> None:
    records = records_for(
        one_module(
            "HeatExchangerEffectivenessModule",
            {"cp_hot_J_kgK": 1000.0, "cp_cold_J_kgK": 1000.0, "effectiveness": 0.5},
        ),
        {
            "m.m_dot_hot_kg_s": 1.0,
            "m.T_hot_in_K": 350.0,
            "m.T_hot_out_K": 325.0,
            "m.m_dot_cold_kg_s": 2.0,
            "m.T_cold_in_K": 300.0,
            "m.T_cold_out_K": 312.5,
            "m.Q_dot_W": 25000.0,
        },
    )
    assert {record.diagnostic_key for record in records} == {
        "heat_exchanger_effectiveness_mismatch",
        "heat_exchanger_hot_side_energy_mismatch",
        "heat_exchanger_cold_side_energy_mismatch",
    }
    assert all(record.value == pytest.approx(0.0) for record in records)
    assert all(record.role == "equation" for record in records)


@pytest.mark.parametrize(
    ("parameters", "match"),
    [
        ({"effectiveness": -0.1}, "effectiveness"),
        ({"effectiveness": 1.1}, "effectiveness"),
        ({"effectiveness": 0.5, "cp_hot_J_kgK": 0.0}, "cp_hot_J_kgK"),
        ({"effectiveness": 0.5, "cp_cold_J_kgK": 0.0}, "cp_cold_J_kgK"),
    ],
)
def test_heat_exchanger_invalid_parameters_fail(parameters: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        ResidualBuilder(one_module("HeatExchangerEffectivenessModule", parameters)).build_registry()


def test_radiative_heat_transfer_zero_residual_and_invalid_parameters() -> None:
    expected = 5.670374419e-8 * (400.0**4 - 300.0**4)
    record = records_for(
        one_module("RadiativeHeatTransferModule", {"emissivity": 1.0, "area_m2": 1.0}),
        {"m.T_hot_K": 400.0, "m.T_cold_K": 300.0, "m.Q_dot_W": expected},
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "radiative_heat_transfer_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="emissivity"):
        ResidualBuilder(
            one_module("RadiativeHeatTransferModule", {"emissivity": 1.1, "area_m2": 1.0})
        ).build_registry()
    with pytest.raises(ValueError, match="area_m2"):
        ResidualBuilder(
            one_module("RadiativeHeatTransferModule", {"emissivity": 1.0, "area_m2": 0.0})
        ).build_registry()


def test_ambient_heat_loss_zero_residual_and_invalid_ua() -> None:
    record = records_for(
        one_module("AmbientHeatLossModule", {"UA_W_K": 100.0}),
        {"m.T_body_K": 330.0, "m.T_ambient_K": 300.0, "m.Q_loss_W": 3000.0},
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "ambient_heat_loss_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="UA_W_K"):
        ResidualBuilder(one_module("AmbientHeatLossModule", {"UA_W_K": -1.0})).build_registry()


@pytest.mark.parametrize(
    "example",
    [
        "heat_exchanger_effectiveness.yaml",
        "radiative_heat_transfer.yaml",
        "ambient_heat_loss.yaml",
    ],
)
def test_heat_exchanger_yaml_examples_solve(example: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "foundation" / example)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass


def test_conflict_heat_exchanger_effectiveness_fails_audit() -> None:
    spec = load_system_spec(ROOT / "examples" / "foundation" / "conflict_heat_exchanger_effectiveness.yaml")
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key in {
        "heat_exchanger_effectiveness_mismatch",
        "heat_exchanger_hot_side_energy_mismatch",
        "heat_exchanger_cold_side_energy_mismatch",
    }
