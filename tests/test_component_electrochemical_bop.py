from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.modules.physical.constants import FARADAY_CONSTANT
from physicsguard.modules.registry import default_module_registry
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "components" / "electrochemical_bop"


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


def test_registry_includes_electrochemical_bop_modules() -> None:
    assert {
        "FuelCellCathodeAirSupplyModule",
        "FuelCellAnodeHydrogenSupplyModule",
        "FuelCellAnodeRecirculationModule",
        "FuelCellCoolantInterfaceModule",
        "FuelCellSystemEfficiencyModule",
        "ElectrolyzerWaterFeedModule",
        "ElectrolyzerGasProductionModule",
        "ElectrolyzerCoolingInterfaceModule",
        "GasSeparatorSimpleModule",
    }.issubset(set(default_module_registry().registered_types()))


@pytest.mark.parametrize(
    "name",
    [
        "fuel_cell_cathode_air_supply.yaml",
        "fuel_cell_anode_hydrogen_supply.yaml",
        "fuel_cell_anode_recirculation.yaml",
        "fuel_cell_coolant_interface.yaml",
        "fuel_cell_system_efficiency.yaml",
        "electrolyzer_water_feed.yaml",
        "electrolyzer_gas_production.yaml",
        "electrolyzer_cooling_interface.yaml",
        "gas_separator_simple.yaml",
    ],
)
def test_electrochemical_bop_clean_examples_solve(name: str) -> None:
    result, report = solve_example(name)
    assert result.optimization_success
    assert result.audit_pass
    assert np.isfinite(result.max_abs_normalized_residual)
    assert all(item.role in {"equation", "boundary"} for item in report.top_residuals)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("conflict_fuel_cell_cathode_air_supply.yaml", "fc_cathode_air_molar_feed_mismatch"),
        ("conflict_electrolyzer_gas_production.yaml", "electrolyzer_h2_molar_production_mismatch"),
    ],
)
def test_electrochemical_bop_conflicts_fail_audit(name: str, expected: str) -> None:
    result, report = solve_example(name)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == expected


@pytest.mark.parametrize(
    ("module_type", "parameters", "message"),
    [
        ("FuelCellCathodeAirSupplyModule", {"n_cells": 0.0}, "n_cells"),
        ("FuelCellCathodeAirSupplyModule", {"n_cells": 400.0, "oxygen_mole_fraction": 0.0}, "oxygen_mole_fraction"),
        ("FuelCellAnodeHydrogenSupplyModule", {"n_cells": 400.0, "faradaic_efficiency": 1.5}, "faradaic_efficiency"),
        ("ElectrolyzerWaterFeedModule", {"n_cells": 0.0}, "n_cells"),
        ("ElectrolyzerGasProductionModule", {"n_cells": 400.0, "molar_mass_H2_kg_mol": 0.0}, "molar_mass_H2_kg_mol"),
        ("FuelCellCoolantInterfaceModule", {"cp_coolant_J_kgK": 0.0}, "cp_coolant_J_kgK"),
    ],
)
def test_electrochemical_bop_invalid_parameters_fail(module_type: str, parameters: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ResidualBuilder(one_module(module_type, parameters)).build_registry()


def test_fuel_cell_cathode_zero_residual_formula() -> None:
    spec = one_module("FuelCellCathodeAirSupplyModule", {"n_cells": 400.0})
    builder = ResidualBuilder(spec)
    registry = builder.build_registry()
    o2 = 400.0 * 100.0 / (4.0 * FARADAY_CONSTANT)
    values = {
        "m.current_A": 100.0,
        "m.n_dot_O2_consumed_mol_s": o2,
        "m.oxygen_stoichiometry": 2.0,
        "m.n_dot_air_feed_mol_s": 2.0 * o2 / 0.21,
        "m.m_dot_air_feed_kg_s": 2.0 * o2 / 0.21 * 0.0289652,
    }
    records = builder.diagnostic_residual_records(registry.dict_to_vector(values))
    assert all(record.value == pytest.approx(0.0, abs=1e-12) for record in records)
