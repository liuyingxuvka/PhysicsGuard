"""Coarse aggregate modules for hierarchical PhysicsGuard audits."""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.schema.variable import is_qualified_variable_name


class AggregatePowerBalanceModule(BaseModule):
    """Coarse algebraic power balance for a system or block."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "AggregatePowerBalanceModule", parameters)
        self.sources = _variable_list(parameters, "source_power_variables", required=False)
        self.loads = _variable_list(parameters, "load_power_variables", required=False)
        self.losses = _variable_list(parameters, "loss_power_variables", required=False)
        self.storage = _variable_list(parameters, "storage_power_variables", required=False)
        self.scale = _positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        residual = (
            _sum_variables(x, registry, self.sources, self.component_id)
            - _sum_variables(x, registry, self.loads, self.component_id)
            - _sum_variables(x, registry, self.losses, self.component_id)
            - _sum_variables(x, registry, self.storage, self.component_id)
        )
        return [_record(self, "aggregate_power_balance", residual, self.scale, "aggregate_power_balance_mismatch", "Coarse algebraic power balance residual.")]

    def metadata(self) -> dict[str, Any]:
        return _metadata(self, ["algebraic coarse power balance", "caller supplies sign convention", "no dynamic energy storage unless storage term is included"])


class AggregateThermalBalanceModule(BaseModule):
    """Coarse thermal balance for a block."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "AggregateThermalBalanceModule", parameters)
        self.heat_in = _variable_list(parameters, "heat_in_variables", required=False)
        self.heat_out = _variable_list(parameters, "heat_out_variables", required=False)
        self.storage_variable = _optional_variable(parameters.get("heat_storage_rate_variable"), "heat_storage_rate_variable")
        self.target_storage = _finite_float(parameters.get("target_storage_rate_W", 0.0), "target_storage_rate_W")
        self.scale = _positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        storage = _variable_value(x, registry, self.storage_variable, self.component_id) if self.storage_variable else self.target_storage
        residual = _sum_variables(x, registry, self.heat_in, self.component_id) - _sum_variables(x, registry, self.heat_out, self.component_id) - storage
        return [_record(self, "aggregate_thermal_balance", residual, self.scale, "aggregate_thermal_balance_mismatch", "Coarse lumped heat balance residual.")]

    def metadata(self) -> dict[str, Any]:
        return _metadata(self, ["lumped heat balance", "no spatial distribution", "no detailed heat transfer"])


class AggregateMassBalanceModule(BaseModule):
    """Coarse mass balance for a block."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "AggregateMassBalanceModule", parameters)
        self.mass_in = _variable_list(parameters, "mass_in_variables", required=False)
        self.mass_out = _variable_list(parameters, "mass_out_variables", required=False)
        self.storage_variable = _optional_variable(parameters.get("mass_storage_rate_variable"), "mass_storage_rate_variable")
        self.target_storage = _finite_float(parameters.get("target_storage_rate_kg_s", 0.0), "target_storage_rate_kg_s")
        self.scale = _positive_float(parameters.get("residual_scale_kg_s", 0.01), "residual_scale_kg_s")

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        storage = _variable_value(x, registry, self.storage_variable, self.component_id) if self.storage_variable else self.target_storage
        residual = _sum_variables(x, registry, self.mass_in, self.component_id) - _sum_variables(x, registry, self.mass_out, self.component_id) - storage
        return [_record(self, "aggregate_mass_balance", residual, self.scale, "aggregate_mass_balance_mismatch", "Coarse lumped mass balance residual.")]

    def metadata(self) -> dict[str, Any]:
        return _metadata(self, ["lumped mass balance", "no species distinction", "no density state"])


class AggregateSpeciesBalanceModule(BaseModule):
    """Coarse species molar balance for a block."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "AggregateSpeciesBalanceModule", parameters)
        self.species_in = _variable_list(parameters, "species_in_variables", required=False)
        self.species_out = _variable_list(parameters, "species_out_variables", required=False)
        self.consumption = _variable_list(parameters, "species_consumption_variables", required=False)
        self.production = _variable_list(parameters, "species_production_variables", required=False)
        self.storage_variable = _optional_variable(parameters.get("storage_rate_variable"), "storage_rate_variable")
        self.target_storage = _finite_float(parameters.get("target_storage_rate_mol_s", 0.0), "target_storage_rate_mol_s")
        self.scale = _positive_float(parameters.get("residual_scale_mol_s", 1e-3), "residual_scale_mol_s")
        self.species_name: Optional[str] = parameters.get("species_name")

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        storage = _variable_value(x, registry, self.storage_variable, self.component_id) if self.storage_variable else self.target_storage
        residual = (
            _sum_variables(x, registry, self.species_in, self.component_id)
            + _sum_variables(x, registry, self.production, self.component_id)
            - _sum_variables(x, registry, self.species_out, self.component_id)
            - _sum_variables(x, registry, self.consumption, self.component_id)
            - storage
        )
        return [_record(self, "aggregate_species_balance", residual, self.scale, "aggregate_species_balance_mismatch", "Coarse species molar balance residual.")]

    def metadata(self) -> dict[str, Any]:
        data = _metadata(self, ["coarse species molar balance", "no transport details", "no reaction kinetics beyond provided rates"])
        data["species_name"] = self.species_name
        return data


class AggregateElectricalBusBalanceModule(BaseModule):
    """Coarse electrical bus algebraic power balance."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "AggregateElectricalBusBalanceModule", parameters)
        self.generation = _variable_list(parameters, "generation_power_variables", required=False)
        self.consumption = _variable_list(parameters, "consumption_power_variables", required=False)
        self.storage = _variable_list(parameters, "storage_power_variables", required=False)
        self.losses = _variable_list(parameters, "loss_power_variables", required=False)
        self.scale = _positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        residual = (
            _sum_variables(x, registry, self.generation, self.component_id)
            - _sum_variables(x, registry, self.consumption, self.component_id)
            - _sum_variables(x, registry, self.storage, self.component_id)
            - _sum_variables(x, registry, self.losses, self.component_id)
        )
        return [_record(self, "aggregate_electrical_bus_balance", residual, self.scale, "aggregate_electrical_bus_balance_mismatch", "Coarse electrical bus balance residual.")]

    def metadata(self) -> dict[str, Any]:
        return _metadata(self, ["algebraic electrical power balance", "caller supplies sign convention", "no bus capacitance unless represented as storage"])


class AggregateEfficiencyModule(BaseModule):
    """Coarse algebraic efficiency relation over existing variables."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "AggregateEfficiencyModule", parameters)
        self.useful_output = _required_variable(parameters, "useful_output_power_variable")
        self.input_power = _required_variable(parameters, "input_power_variable")
        self.efficiency = _required_variable(parameters, "efficiency_variable")
        self.denominator_min_abs = _positive_float(parameters.get("denominator_min_abs", 1e-9), "denominator_min_abs")
        self.scale = _positive_float(parameters.get("residual_scale", 0.01), "residual_scale")

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        useful = _variable_value(x, registry, self.useful_output, self.component_id)
        input_power = _variable_value(x, registry, self.input_power, self.component_id)
        if abs(input_power) < self.denominator_min_abs:
            raise ValueError(f"{self.component_id}: input_power magnitude is below denominator_min_abs")
        efficiency = _variable_value(x, registry, self.efficiency, self.component_id)
        residual = efficiency - useful / input_power
        return [_record(self, "aggregate_efficiency", residual, self.scale, "aggregate_efficiency_mismatch", "Coarse algebraic efficiency residual.")]

    def metadata(self) -> dict[str, Any]:
        return _metadata(self, ["algebraic efficiency sanity check", "no detailed loss model"])


def _record(
    module: BaseModule,
    name: str,
    value: float,
    scale: float,
    diagnostic_key: str,
    description: str,
) -> ResidualRecord:
    return ResidualRecord(
        name=f"{module.component_id}.{name}",
        value=float(value),
        scale=scale,
        source=module.component_id,
        role="equation",
        diagnostic_key=diagnostic_key,
        description=description,
    )


def _variable_list(parameters: dict[str, Any], name: str, *, required: bool) -> list[str]:
    if name not in parameters:
        if required:
            raise ValueError(f"{name} is required")
        return []
    value = parameters[name]
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    variables: list[str] = []
    for item in value:
        if not isinstance(item, str) or not is_qualified_variable_name(item):
            raise ValueError(f"{name} entries must use component.variable format")
        variables.append(item)
    return variables


def _required_variable(parameters: dict[str, Any], name: str) -> str:
    if name not in parameters:
        raise ValueError(f"{name} is required")
    return _optional_variable(parameters[name], name) or ""


def _optional_variable(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not is_qualified_variable_name(value):
        raise ValueError(f"{name} must use component.variable format")
    return value


def _variable_value(
    x: np.ndarray,
    registry: VariableRegistry,
    variable: str,
    component_id: str,
) -> float:
    try:
        return float(x[registry.get_index(variable)])
    except KeyError as exc:
        raise KeyError(f"{component_id}: aggregate module references unknown variable: {exc}") from exc


def _sum_variables(
    x: np.ndarray,
    registry: VariableRegistry,
    variables: list[str],
    component_id: str,
) -> float:
    return sum(_variable_value(x, registry, variable, component_id) for variable in variables)


def _finite_float(value: Any, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def _positive_float(value: Any, name: str) -> float:
    parsed = _finite_float(value, name)
    if parsed <= 0:
        raise ValueError(f"{name} must be positive")
    return parsed


def _metadata(module: BaseModule, validity: list[str]) -> dict[str, Any]:
    return {
        "component_id": module.component_id,
        "module_type": module.module_type,
        "purpose": "coarse_hierarchical_low_fidelity_audit",
        "domain": "aggregate",
        "assumptions": list(validity),
        "limitations": list(validity),
        "si_units": True,
        "validity_range": list(validity),
    }


__all__ = [
    "AggregateElectricalBusBalanceModule",
    "AggregateEfficiencyModule",
    "AggregateMassBalanceModule",
    "AggregatePowerBalanceModule",
    "AggregateSpeciesBalanceModule",
    "AggregateThermalBalanceModule",
]
