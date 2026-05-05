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
        {"system_name": module_type, "components": [{"id": "m", "type": module_type, "parameters": parameters}]}
    )


def records_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)


def test_registry_includes_component_electrochemical_modules() -> None:
    assert {
        "FuelCellStackBalanceModule",
        "FuelCellPolarizationMapModule",
        "ElectrolyzerStackBalanceModule",
        "ElectrolyzerPolarizationMapModule",
    }.issubset(set(default_module_registry().registered_types()))


def test_fuel_cell_stack_balance_zero_residual_and_invalid_parameters() -> None:
    h2 = 400.0 * 100.0 / (2.0 * FARADAY_CONSTANT)
    records = records_for(
        one_module("FuelCellStackBalanceModule", {"n_cells": 400.0}),
        {
            "m.current_A": 100.0,
            "m.V_cell_V": 0.7,
            "m.V_stack_V": 280.0,
            "m.P_stack_W": 28000.0,
            "m.n_dot_H2_consumed_mol_s": h2,
            "m.n_dot_O2_consumed_mol_s": h2 / 2.0,
            "m.n_dot_H2O_produced_mol_s": h2,
            "m.Q_heat_W": 31200.0,
        },
    )
    assert all(record.value == pytest.approx(0.0, abs=1e-9) for record in records)
    assert "fuel_cell_h2_consumption_mismatch" in {r.diagnostic_key for r in records}
    with pytest.raises(ValueError, match="n_cells"):
        ResidualBuilder(one_module("FuelCellStackBalanceModule", {"n_cells": 0.0})).build_registry()


def test_electrolyzer_stack_balance_zero_residual_and_invalid_efficiency() -> None:
    h2 = 400.0 * 100.0 / (2.0 * FARADAY_CONSTANT)
    records = records_for(
        one_module("ElectrolyzerStackBalanceModule", {"n_cells": 400.0}),
        {
            "m.current_A": 100.0,
            "m.V_cell_V": 1.8,
            "m.V_stack_V": 720.0,
            "m.P_stack_W": 72000.0,
            "m.n_dot_H2_produced_mol_s": h2,
            "m.n_dot_O2_produced_mol_s": h2 / 2.0,
            "m.n_dot_H2O_consumed_mol_s": h2,
            "m.Q_heat_W": 12800.0,
        },
    )
    assert all(record.value == pytest.approx(0.0, abs=1e-9) for record in records)
    assert "electrolyzer_h2_production_mismatch" in {r.diagnostic_key for r in records}
    with pytest.raises(ValueError, match="faradaic_efficiency"):
        ResidualBuilder(
            one_module("ElectrolyzerStackBalanceModule", {"n_cells": 400.0, "faradaic_efficiency": 1.1})
        ).build_registry()


def test_polarization_maps_interpolate_and_invalid_map() -> None:
    fc = records_for(
        one_module(
            "FuelCellPolarizationMapModule",
            {"current_density_points_A_m2": [0.0, 2000.0], "V_cell_points_V": [0.9, 0.7]},
        ),
        {"m.current_density_A_m2": 1000.0, "m.V_cell_V": 0.8},
    )[0]
    el = records_for(
        one_module(
            "ElectrolyzerPolarizationMapModule",
            {"current_density_points_A_m2": [0.0, 2000.0], "V_cell_points_V": [1.5, 1.9]},
        ),
        {"m.current_density_A_m2": 1000.0, "m.V_cell_V": 1.7},
    )[0]
    assert fc.value == pytest.approx(0.0)
    assert el.value == pytest.approx(0.0)
    assert fc.diagnostic_key == "fuel_cell_polarization_map_mismatch"
    assert el.diagnostic_key == "electrolyzer_polarization_map_mismatch"
    with pytest.raises(ValueError, match="V_cell_points_V"):
        ResidualBuilder(
            one_module(
                "FuelCellPolarizationMapModule",
                {"current_density_points_A_m2": [0.0, 1.0], "V_cell_points_V": [0.9]},
            )
        ).build_registry()


@pytest.mark.parametrize(
    "name",
    ["fuel_cell_stack_balance.yaml", "fuel_cell_polarization_map.yaml", "electrolyzer_stack_balance.yaml", "electrolyzer_polarization_map.yaml"],
)
def test_component_electrochemical_yaml_examples_solve(name: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "components" / "electrochemical" / name)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("conflict_fuel_cell_stack_balance.yaml", "fuel_cell_h2_consumption_mismatch"),
        ("conflict_electrolyzer_stack_balance.yaml", "electrolyzer_h2_production_mismatch"),
    ],
)
def test_component_electrochemical_conflicts_fail_audit(name: str, expected: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "components" / "electrochemical" / name)
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == expected
