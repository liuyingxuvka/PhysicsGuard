from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.modules.registry import default_module_registry
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]


def system(module_type: str, parameters: dict) -> SystemSpec:
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


def test_default_module_registry_includes_foundation_modules() -> None:
    registered = set(default_module_registry().registered_types())
    assert {
        "ThermalConductorModule",
        "ConvectiveHeatTransferModule",
        "ThermalCapacitanceRateModule",
        "IncompressiblePressureDropModule",
        "IncompressibleOrificeModule",
        "MassBalanceRateModule",
        "MixerEnergyBalanceModule",
        "PumpHydraulicPowerModule",
        "OhmicRelationModule",
        "ElectricalPowerModule",
        "StoichiometryModule",
        "ElectrochemicalStackPowerModule",
    }.issubset(registered)


def test_stoichiometry_zero_residual() -> None:
    record = record_for(
        system("StoichiometryModule", {"stoichiometry": 2.0}),
        {"m.n_dot_feed_mol_s": 0.2, "m.n_dot_consumed_mol_s": 0.1},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "stoichiometry_mismatch"
    assert record.role == "equation"


def test_stoichiometry_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="stoichiometry"):
        ResidualBuilder(system("StoichiometryModule", {"stoichiometry": 0.0})).build_registry()


def test_electrochemical_stack_power_zero_residual() -> None:
    record = record_for(
        system("ElectrochemicalStackPowerModule", {"n_cells": 400.0}),
        {"m.V_cell_V": 0.7, "m.current_A": 100.0, "m.P_stack_W": 28000.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "electrochemical_stack_power_mismatch"
    assert record.role == "equation"


def test_electrochemical_stack_power_invalid_n_cells_fails() -> None:
    with pytest.raises(ValueError, match="n_cells"):
        ResidualBuilder(
            system("ElectrochemicalStackPowerModule", {"n_cells": 0.0})
        ).build_registry()


@pytest.mark.parametrize("example", ["stoichiometry.yaml", "electrochemical_stack_power.yaml"])
def test_electrochemical_foundation_yaml_examples_solve(example: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "foundation" / example)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
