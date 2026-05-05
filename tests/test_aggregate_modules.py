from __future__ import annotations

from pathlib import Path

import math

import numpy as np
import pytest

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.modules.registry import default_module_registry
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]
FC = ROOT / "examples" / "hierarchical" / "fuel_cell_system"


AGGREGATE_TYPES = {
    "AggregatePowerBalanceModule",
    "AggregateThermalBalanceModule",
    "AggregateMassBalanceModule",
    "AggregateSpeciesBalanceModule",
    "AggregateElectricalBusBalanceModule",
    "AggregateEfficiencyModule",
}


def dummy(component_id: str, value: float) -> dict:
    return {
        "id": component_id,
        "type": "DummyResidualModule",
        "parameters": {
            "target": value,
            "lower_bound": -1.0e9,
            "upper_bound": 1.0e9,
            "initial_guess": value,
            "scale": max(abs(value), 1.0),
        },
    }


def system(components: list[dict]) -> SystemSpec:
    return SystemSpec.model_validate({"system_name": "aggregate_test", "components": components})


def aggregate_record(module_type: str, parameters: dict, values: dict[str, float]):
    components = [dummy(name.split(".", 1)[0], value) for name, value in values.items()]
    components.append({"id": "aggregate", "type": module_type, "parameters": parameters})
    spec = system(components)
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    records = builder.diagnostic_residual_records(x)
    return next(record for record in records if record.source == "aggregate")


def test_registry_includes_aggregate_modules() -> None:
    assert AGGREGATE_TYPES.issubset(set(default_module_registry().registered_types()))


@pytest.mark.parametrize(
    ("module_type", "parameters", "values", "diagnostic_key"),
    [
        (
            "AggregatePowerBalanceModule",
            {
                "source_power_variables": ["source.x"],
                "load_power_variables": ["load.x"],
                "loss_power_variables": ["loss.x"],
                "residual_scale_W": 1.0,
            },
            {"source.x": 10.0, "load.x": 7.0, "loss.x": 3.0},
            "aggregate_power_balance_mismatch",
        ),
        (
            "AggregateThermalBalanceModule",
            {
                "heat_in_variables": ["heat_in.x"],
                "heat_out_variables": ["heat_out.x"],
                "target_storage_rate_W": 2.0,
                "residual_scale_W": 1.0,
            },
            {"heat_in.x": 10.0, "heat_out.x": 8.0},
            "aggregate_thermal_balance_mismatch",
        ),
        (
            "AggregateMassBalanceModule",
            {
                "mass_in_variables": ["mass_in.x"],
                "mass_out_variables": ["mass_out.x"],
                "target_storage_rate_kg_s": 0.2,
                "residual_scale_kg_s": 1.0,
            },
            {"mass_in.x": 1.0, "mass_out.x": 0.8},
            "aggregate_mass_balance_mismatch",
        ),
        (
            "AggregateSpeciesBalanceModule",
            {
                "species_in_variables": ["species_in.x"],
                "species_out_variables": ["species_out.x"],
                "species_consumption_variables": ["consumption.x"],
                "species_production_variables": ["production.x"],
                "target_storage_rate_mol_s": 0.2,
                "residual_scale_mol_s": 1.0,
            },
            {"species_in.x": 1.0, "species_out.x": 0.9, "consumption.x": 0.1, "production.x": 0.2},
            "aggregate_species_balance_mismatch",
        ),
        (
            "AggregateElectricalBusBalanceModule",
            {
                "generation_power_variables": ["generation.x"],
                "consumption_power_variables": ["consumption.x"],
                "storage_power_variables": ["storage.x"],
                "loss_power_variables": ["loss.x"],
                "residual_scale_W": 1.0,
            },
            {"generation.x": 10.0, "consumption.x": 6.0, "storage.x": 2.0, "loss.x": 2.0},
            "aggregate_electrical_bus_balance_mismatch",
        ),
        (
            "AggregateEfficiencyModule",
            {
                "useful_output_power_variable": "useful.x",
                "input_power_variable": "input.x",
                "efficiency_variable": "efficiency.x",
                "residual_scale": 0.01,
            },
            {"useful.x": 5.0, "input.x": 10.0, "efficiency.x": 0.5},
            "aggregate_efficiency_mismatch",
        ),
    ],
)
def test_aggregate_modules_zero_residual(
    module_type: str,
    parameters: dict,
    values: dict[str, float],
    diagnostic_key: str,
) -> None:
    record = aggregate_record(module_type, parameters, values)
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == diagnostic_key
    assert record.role == "equation"
    assert math.isfinite(record.normalized_value)


def test_aggregate_power_balance_conflict_residual_is_finite() -> None:
    record = aggregate_record(
        "AggregatePowerBalanceModule",
        {
            "source_power_variables": ["source.x"],
            "load_power_variables": ["load.x"],
            "loss_power_variables": ["loss.x"],
            "residual_scale_W": 1.0,
        },
        {"source.x": 10.0, "load.x": 6.0, "loss.x": 3.0},
    )
    assert record.value == pytest.approx(1.0)
    assert np.isfinite(record.normalized_value)


def test_aggregate_references_unknown_variable_fail_clearly() -> None:
    spec = system(
        [
            dummy("source", 10.0),
            {
                "id": "aggregate",
                "type": "AggregatePowerBalanceModule",
                "parameters": {
                    "source_power_variables": ["source.x"],
                    "load_power_variables": ["missing.x"],
                },
            },
        ]
    )
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector({"source.x": 10.0})

    with pytest.raises(KeyError, match="unknown variable"):
        builder.diagnostic_residual_records(x)


def test_aggregate_efficiency_unsafe_denominator_fails_clearly() -> None:
    spec = system(
        [
            dummy("useful", 1.0),
            dummy("input", 0.0),
            dummy("efficiency", 0.5),
            {
                "id": "aggregate",
                "type": "AggregateEfficiencyModule",
                "parameters": {
                    "useful_output_power_variable": "useful.x",
                    "input_power_variable": "input.x",
                    "efficiency_variable": "efficiency.x",
                },
            },
        ]
    )
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector({"useful.x": 1.0, "input.x": 0.0, "efficiency.x": 0.5})

    with pytest.raises(ValueError, match="denominator_min_abs"):
        builder.diagnostic_residual_records(x)


def test_aggregate_modules_run_through_hierarchical_yaml_example() -> None:
    spec = load_hierarchical_audit_spec(FC / "level_0_system_balance.yaml")
    builder = ResidualBuilder(spec.system)
    result = BoundedSolver(builder, spec.system.solver).solve()
    report = DiagnosticReporter().generate(spec.system, builder, result)
    keys = {residual.diagnostic_key for residual in report.top_residuals}

    assert result.optimization_success
    assert report.audit_pass
    assert "aggregate_power_balance_mismatch" in keys
    assert "aggregate_efficiency_mismatch" in keys
