"""Component-level low-fidelity electrochemical audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.components._common import (
    bounded_record,
    component_metadata,
    finite_list,
    molar_flow_record,
    one_d_interp,
    positive_current_record,
    positive_float,
    power_record,
    required_positive,
    strictly_increasing_axis,
    value,
    voltage_record,
)
from physicsguard.modules.physical.constants import FARADAY_CONSTANT


class FuelCellStackBalanceModule(BaseModule):
    """Low-fidelity PEM fuel-cell stack balance audit component."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "FuelCellStackBalanceModule", parameters)
        self.n_cells = required_positive(parameters, "n_cells")
        self.E_thermoneutral_V = positive_float(
            parameters.get("E_thermoneutral_V", 1.48),
            "E_thermoneutral_V",
        )
        self.faradaic_efficiency = positive_float(
            parameters.get("faradaic_efficiency", 1.0),
            "faradaic_efficiency",
        )
        if self.faradaic_efficiency > 1.0:
            raise ValueError("faradaic_efficiency must be <= 1")
        self.residual_scale_mol_s = positive_float(
            parameters.get("residual_scale_mol_s", 1e-3),
            "residual_scale_mol_s",
        )
        self.residual_scale_power_W = positive_float(
            parameters.get("residual_scale_power_W", 1000.0),
            "residual_scale_power_W",
        )
        self.residual_scale_voltage_V = positive_float(
            parameters.get("residual_scale_voltage_V", 1.0),
            "residual_scale_voltage_V",
        )
        self.records = _stack_common_records(component_id, parameters, self.n_cells) + [
            molar_flow_record(component_id, parameters, "n_dot_H2_consumed_mol_s", "n_dot_H2_consumed", 1e-3),
            molar_flow_record(component_id, parameters, "n_dot_O2_consumed_mol_s", "n_dot_O2_consumed", 1e-3),
            molar_flow_record(component_id, parameters, "n_dot_H2O_produced_mol_s", "n_dot_H2O_produced", 1e-3),
            power_record(component_id, parameters, "Q_heat_W", "Q_heat", 1000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        current, v_cell, v_stack, p_stack = _stack_common_values(x, registry, self.component_id)
        h2 = value(x, registry, self.component_id, "n_dot_H2_consumed_mol_s")
        o2 = value(x, registry, self.component_id, "n_dot_O2_consumed_mol_s")
        water = value(x, registry, self.component_id, "n_dot_H2O_produced_mol_s")
        heat = value(x, registry, self.component_id, "Q_heat_W")
        h2_expected = self.faradaic_efficiency * self.n_cells * current / (2.0 * FARADAY_CONSTANT)
        o2_expected = self.faradaic_efficiency * self.n_cells * current / (4.0 * FARADAY_CONSTANT)
        heat_expected = self.n_cells * current * (self.E_thermoneutral_V - v_cell)
        return [
            _residual(self, "fuel_cell_stack_voltage", v_stack - self.n_cells * v_cell, self.residual_scale_voltage_V, "fuel_cell_stack_voltage_mismatch"),
            _residual(self, "fuel_cell_stack_power", p_stack - self.n_cells * current * v_cell, self.residual_scale_power_W, "fuel_cell_stack_power_mismatch"),
            _residual(self, "fuel_cell_h2_consumption", h2 - h2_expected, self.residual_scale_mol_s, "fuel_cell_h2_consumption_mismatch"),
            _residual(self, "fuel_cell_o2_consumption", o2 - o2_expected, self.residual_scale_mol_s, "fuel_cell_o2_consumption_mismatch"),
            _residual(self, "fuel_cell_water_production", water - h2_expected, self.residual_scale_mol_s, "fuel_cell_water_production_mismatch"),
            _residual(self, "fuel_cell_heat_generation", heat - heat_expected, self.residual_scale_power_W, "fuel_cell_heat_generation_mismatch"),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "electrochemical_component",
            [
                "lumped Faraday and power/heat balance only",
                "no polarization model",
                "no membrane water model",
                "no pressure/humidity effects",
                "no mass transport limitation",
                "no degradation",
                "no auxiliary power",
            ],
        )


class FuelCellPolarizationMapModule(BaseModule):
    """Map-based fuel-cell cell-voltage consistency check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "FuelCellPolarizationMapModule", parameters)
        self.current_density_points = strictly_increasing_axis(parameters, "current_density_points_A_m2")
        self.V_cell_points = finite_list(parameters, "V_cell_points_V")
        if len(self.current_density_points) != len(self.V_cell_points):
            raise ValueError("V_cell_points_V length must match current_density_points_A_m2")
        self.extrapolation = parameters.get("extrapolation", "error")
        if self.extrapolation not in {"error", "hold"}:
            raise ValueError("extrapolation must be 'error' or 'hold'")
        self.residual_scale_V = positive_float(parameters.get("residual_scale_V", 0.02), "residual_scale_V")
        self.records = _polarization_records(component_id, parameters)

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        current_density = value(x, registry, self.component_id, "current_density_A_m2")
        v_cell = value(x, registry, self.component_id, "V_cell_V")
        expected = one_d_interp(
            current_density,
            self.current_density_points,
            self.V_cell_points,
            self.extrapolation,
            self.component_id,
        )
        return [_residual(self, "fuel_cell_polarization_map", v_cell - expected, self.residual_scale_V, "fuel_cell_polarization_map_mismatch")]

    def metadata(self) -> dict[str, Any]:
        metadata = component_metadata(
            self,
            "electrochemical_component",
            [
                "map consistency only",
                "no electrochemical physics",
                "no pressure/temperature/humidity correction unless map already includes it",
            ],
        )
        metadata["extrapolation"] = self.extrapolation
        return metadata


class ElectrolyzerStackBalanceModule(BaseModule):
    """Low-fidelity electrolyzer stack balance audit component."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ElectrolyzerStackBalanceModule", parameters)
        self.n_cells = required_positive(parameters, "n_cells")
        self.E_thermoneutral_V = positive_float(
            parameters.get("E_thermoneutral_V", 1.48),
            "E_thermoneutral_V",
        )
        self.faradaic_efficiency = positive_float(
            parameters.get("faradaic_efficiency", 1.0),
            "faradaic_efficiency",
        )
        if self.faradaic_efficiency > 1.0:
            raise ValueError("faradaic_efficiency must be <= 1")
        self.residual_scale_mol_s = positive_float(
            parameters.get("residual_scale_mol_s", 1e-3),
            "residual_scale_mol_s",
        )
        self.residual_scale_power_W = positive_float(
            parameters.get("residual_scale_power_W", 1000.0),
            "residual_scale_power_W",
        )
        self.residual_scale_voltage_V = positive_float(
            parameters.get("residual_scale_voltage_V", 1.0),
            "residual_scale_voltage_V",
        )
        self.records = _stack_common_records(component_id, parameters, self.n_cells) + [
            molar_flow_record(component_id, parameters, "n_dot_H2_produced_mol_s", "n_dot_H2_produced", 1e-3),
            molar_flow_record(component_id, parameters, "n_dot_O2_produced_mol_s", "n_dot_O2_produced", 1e-3),
            molar_flow_record(component_id, parameters, "n_dot_H2O_consumed_mol_s", "n_dot_H2O_consumed", 1e-3),
            power_record(component_id, parameters, "Q_heat_W", "Q_heat", 1000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        current, v_cell, v_stack, p_stack = _stack_common_values(x, registry, self.component_id)
        h2 = value(x, registry, self.component_id, "n_dot_H2_produced_mol_s")
        o2 = value(x, registry, self.component_id, "n_dot_O2_produced_mol_s")
        water = value(x, registry, self.component_id, "n_dot_H2O_consumed_mol_s")
        heat = value(x, registry, self.component_id, "Q_heat_W")
        h2_expected = self.faradaic_efficiency * self.n_cells * current / (2.0 * FARADAY_CONSTANT)
        o2_expected = self.faradaic_efficiency * self.n_cells * current / (4.0 * FARADAY_CONSTANT)
        heat_expected = self.n_cells * current * (v_cell - self.E_thermoneutral_V)
        return [
            _residual(self, "electrolyzer_stack_voltage", v_stack - self.n_cells * v_cell, self.residual_scale_voltage_V, "electrolyzer_stack_voltage_mismatch"),
            _residual(self, "electrolyzer_stack_power", p_stack - self.n_cells * current * v_cell, self.residual_scale_power_W, "electrolyzer_stack_power_mismatch"),
            _residual(self, "electrolyzer_h2_production", h2 - h2_expected, self.residual_scale_mol_s, "electrolyzer_h2_production_mismatch"),
            _residual(self, "electrolyzer_o2_production", o2 - o2_expected, self.residual_scale_mol_s, "electrolyzer_o2_production_mismatch"),
            _residual(self, "electrolyzer_water_consumption", water - h2_expected, self.residual_scale_mol_s, "electrolyzer_water_consumption_mismatch"),
            _residual(self, "electrolyzer_heat_generation", heat - heat_expected, self.residual_scale_power_W, "electrolyzer_heat_generation_mismatch"),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "electrochemical_component",
            [
                "lumped Faraday and power/heat balance only",
                "no polarization model",
                "no two-phase transport",
                "no water management",
                "no thermal dynamics",
                "no auxiliary power",
            ],
        )


class ElectrolyzerPolarizationMapModule(BaseModule):
    """Map-based electrolyzer cell-voltage consistency check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ElectrolyzerPolarizationMapModule", parameters)
        self.current_density_points = strictly_increasing_axis(parameters, "current_density_points_A_m2")
        self.V_cell_points = finite_list(parameters, "V_cell_points_V")
        if len(self.current_density_points) != len(self.V_cell_points):
            raise ValueError("V_cell_points_V length must match current_density_points_A_m2")
        self.extrapolation = parameters.get("extrapolation", "error")
        if self.extrapolation not in {"error", "hold"}:
            raise ValueError("extrapolation must be 'error' or 'hold'")
        self.residual_scale_V = positive_float(parameters.get("residual_scale_V", 0.02), "residual_scale_V")
        self.records = _polarization_records(component_id, parameters)

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        current_density = value(x, registry, self.component_id, "current_density_A_m2")
        v_cell = value(x, registry, self.component_id, "V_cell_V")
        expected = one_d_interp(
            current_density,
            self.current_density_points,
            self.V_cell_points,
            self.extrapolation,
            self.component_id,
        )
        return [_residual(self, "electrolyzer_polarization_map", v_cell - expected, self.residual_scale_V, "electrolyzer_polarization_map_mismatch")]

    def metadata(self) -> dict[str, Any]:
        metadata = component_metadata(
            self,
            "electrochemical_component",
            [
                "map consistency only",
                "no electrochemical physics",
                "no temperature/pressure correction unless map already includes it",
            ],
        )
        metadata["extrapolation"] = self.extrapolation
        return metadata


def _stack_common_records(
    component_id: str,
    parameters: dict[str, Any],
    n_cells: float,
) -> list[VariableRecord]:
    return [
        positive_current_record(component_id, parameters, "current_A", "current", 100.0),
        bounded_record(component_id, parameters, "V_cell_V", "V", "V_cell", 0.0, 3.0, 0.7, 1.0),
        bounded_record(component_id, parameters, "V_stack_V", "V", "V_stack", 0.0, 1e5, n_cells * 0.7, 100.0),
        power_record(component_id, parameters, "P_stack_W", "P_stack", n_cells * 70.0),
    ]


def _stack_common_values(
    x: np.ndarray,
    registry: VariableRegistry,
    component_id: str,
) -> tuple[float, float, float, float]:
    return (
        value(x, registry, component_id, "current_A"),
        value(x, registry, component_id, "V_cell_V"),
        value(x, registry, component_id, "V_stack_V"),
        value(x, registry, component_id, "P_stack_W"),
    )


def _polarization_records(component_id: str, parameters: dict[str, Any]) -> list[VariableRecord]:
    return [
        bounded_record(
            component_id,
            parameters,
            "current_density_A_m2",
            "A/m^2",
            "current_density",
            0.0,
            1e6,
            1000.0,
            100.0,
        ),
        bounded_record(component_id, parameters, "V_cell_V", "V", "V_cell", 0.0, 3.0, 0.7, 0.1),
    ]


def _residual(
    module: BaseModule,
    name: str,
    value_obj: float,
    scale: float,
    diagnostic_key: str,
) -> ResidualRecord:
    return ResidualRecord(
        name=f"{module.component_id}.{name}",
        value=value_obj,
        scale=scale,
        source=module.component_id,
        role="equation",
        diagnostic_key=diagnostic_key,
        description=f"{module.module_type} residual {diagnostic_key}.",
    )
