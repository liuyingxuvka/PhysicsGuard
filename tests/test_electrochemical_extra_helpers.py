from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.modules.physical.constants import FARADAY_CONSTANT
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


def test_default_registry_includes_electrochemical_extra_helpers() -> None:
    registered = set(default_module_registry().registered_types())
    assert {
        "ChemicalPowerLHVModule",
        "StackChemicalEfficiencyModule",
        "AirOxygenMolarFlowModule",
        "WaterProductionFaradayModule",
    }.issubset(registered)


def test_chemical_power_lhv_zero_residual_and_invalid_lhv() -> None:
    record = records_for(
        one_module("ChemicalPowerLHVModule", {"LHV_J_kg": 120e6}),
        {"m.m_dot_fuel_kg_s": 0.001, "m.P_chemical_W": 120000.0},
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "chemical_power_lhv_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="LHV_J_kg"):
        ResidualBuilder(one_module("ChemicalPowerLHVModule", {"LHV_J_kg": 0.0})).build_registry()


def test_stack_chemical_efficiency_zero_residual_and_denominator_safety() -> None:
    record = records_for(
        one_module("StackChemicalEfficiencyModule", {}),
        {"m.P_stack_W": 500.0, "m.P_chemical_W": 1000.0, "m.efficiency": 0.5},
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "stack_chemical_efficiency_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="P_chemical_W"):
        records_for(
            one_module(
                "StackChemicalEfficiencyModule",
                {"P_chemical_lower_bound": -1.0, "P_chemical_initial_guess": 0.0},
            ),
            {"m.P_stack_W": 0.0, "m.P_chemical_W": 0.0, "m.efficiency": 0.0},
        )


def test_stack_chemical_efficiency_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="denominator_min_abs"):
        ResidualBuilder(
            one_module("StackChemicalEfficiencyModule", {"denominator_min_abs": 0.0})
        ).build_registry()


def test_air_oxygen_molar_flow_zero_residual_and_invalid_parameters() -> None:
    n_air = 0.1 / 0.21
    records = records_for(
        one_module(
            "AirOxygenMolarFlowModule",
            {"oxygen_mole_fraction": 0.21, "molar_mass_air_kg_mol": 0.0289652},
        ),
        {
            "m.n_dot_O2_mol_s": 0.1,
            "m.n_dot_air_mol_s": n_air,
            "m.m_dot_air_kg_s": n_air * 0.0289652,
        },
    )
    assert {record.diagnostic_key for record in records} == {
        "air_oxygen_molar_flow_mismatch",
        "air_mass_flow_from_molar_flow_mismatch",
    }
    assert all(record.value == pytest.approx(0.0) for record in records)
    assert all(record.role == "equation" for record in records)

    with pytest.raises(ValueError, match="oxygen_mole_fraction"):
        ResidualBuilder(
            one_module("AirOxygenMolarFlowModule", {"oxygen_mole_fraction": 0.0})
        ).build_registry()
    with pytest.raises(ValueError, match="molar_mass_air_kg_mol"):
        ResidualBuilder(
            one_module("AirOxygenMolarFlowModule", {"molar_mass_air_kg_mol": 0.0})
        ).build_registry()


def test_water_production_faraday_zero_residual_and_invalid_parameters() -> None:
    expected = 400.0 * 100.0 / (2.0 * FARADAY_CONSTANT)
    record = records_for(
        one_module("WaterProductionFaradayModule", {"n_cells": 400.0}),
        {"m.current_A": 100.0, "m.n_dot_H2O_mol_s": expected},
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "water_production_faraday_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="n_cells"):
        ResidualBuilder(one_module("WaterProductionFaradayModule", {"n_cells": 0.0})).build_registry()
    with pytest.raises(ValueError, match="faradaic_efficiency"):
        ResidualBuilder(
            one_module(
                "WaterProductionFaradayModule",
                {"n_cells": 400.0, "faradaic_efficiency": 1.1},
            )
        ).build_registry()


@pytest.mark.parametrize(
    "example",
    [
        "chemical_power_lhv.yaml",
        "stack_chemical_efficiency.yaml",
        "air_oxygen_molar_flow.yaml",
        "water_production_faraday.yaml",
    ],
)
def test_electrochemical_extra_yaml_examples_solve(example: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "foundation" / example)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass


def test_conflict_air_oxygen_molar_flow_fails_audit() -> None:
    spec = load_system_spec(ROOT / "examples" / "foundation" / "conflict_air_oxygen_molar_flow.yaml")
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "air_oxygen_molar_flow_mismatch"
