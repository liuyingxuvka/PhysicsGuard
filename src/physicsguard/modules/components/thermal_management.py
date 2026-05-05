"""Component-level low-fidelity thermal-management audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.components._common import (
    bounded_record,
    component_metadata,
    fraction_record,
    mass_flow_record,
    nonnegative_float,
    positive_float,
    power_record,
    residual_record,
    required_positive,
    role,
    temperature_record,
    validate_fraction_value,
    value,
    volume_record,
)


class ColdPlateSimpleModule(BaseModule):
    """Low-fidelity cold-plate heat removal audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ColdPlateSimpleModule", parameters)
        self.cp = positive_float(parameters.get("cp_coolant_J_kgK", 4180.0), "cp_coolant_J_kgK")
        self.UA = nonnegative_float(parameters.get("UA_W_K"), "UA_W_K") if "UA_W_K" in parameters else required_positive(parameters, "UA_W_K")
        self.scale = positive_float(parameters.get("residual_scale_heat_W", 1000.0), "residual_scale_heat_W")
        self.records = [
            mass_flow_record(component_id, parameters, "m_dot_coolant_kg_s", "m_dot_coolant", 0.1),
            temperature_record(component_id, parameters, "T_coolant_in_K", "T_coolant_in", 300.0),
            temperature_record(component_id, parameters, "T_coolant_out_K", "T_coolant_out", 310.0),
            temperature_record(component_id, parameters, "T_surface_K", "T_surface", 320.0),
            power_record(component_id, parameters, "Q_removed_W", "Q_removed", 4180.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m = value(x, registry, self.component_id, "m_dot_coolant_kg_s")
        tin = value(x, registry, self.component_id, "T_coolant_in_K")
        tout = value(x, registry, self.component_id, "T_coolant_out_K")
        ts = value(x, registry, self.component_id, "T_surface_K")
        q = value(x, registry, self.component_id, "Q_removed_W")
        return [
            residual_record(self, "cold_plate_coolant_heat_balance", q - m * self.cp * (tout - tin), self.scale, "cold_plate_coolant_heat_balance_mismatch", "Cold-plate coolant heat balance residual."),
            residual_record(self, "cold_plate_ua_heat_transfer", q - self.UA * (ts - tin), self.scale, "cold_plate_ua_heat_transfer_mismatch", "Cold-plate UA heat transfer residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "thermal_management", ["lumped cold plate", "no spatial gradients", "no two-phase flow", "no pressure drop", "no wall thermal mass"])


class ThermalMassStepModule(BaseModule):
    """Single-step thermal mass temperature audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ThermalMassStepModule", parameters)
        self.C = required_positive(parameters, "C_J_K")
        self.dt = required_positive(parameters, "dt_s")
        self.scale = positive_float(parameters.get("residual_scale_K", 1.0), "residual_scale_K")
        self.records = [
            temperature_record(component_id, parameters, "T_previous_K", "T_previous", 300.0),
            temperature_record(component_id, parameters, "T_current_K", "T_current", 301.0),
            power_record(component_id, parameters, "Q_in_W", "Q_in", 1000.0),
            power_record(component_id, parameters, "Q_out_W", "Q_out", 0.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        prev = value(x, registry, self.component_id, "T_previous_K")
        cur = value(x, registry, self.component_id, "T_current_K")
        qin = value(x, registry, self.component_id, "Q_in_W")
        qout = value(x, registry, self.component_id, "Q_out_W")
        return [residual_record(self, "thermal_mass_temperature_step", cur - prev - (qin - qout) * self.dt / self.C, self.scale, "thermal_mass_temperature_step_mismatch", "Thermal mass single-step temperature residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "thermal_management", ["lumped temperature", "single-step audit", "no spatial gradients", "no phase change"])


class ThermostatValveModule(BaseModule):
    """Static thermostat opening consistency check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ThermostatValveModule", parameters)
        self.begin = positive_float(parameters.get("T_begin_open_K"), "T_begin_open_K") if "T_begin_open_K" in parameters else required_positive(parameters, "T_begin_open_K")
        self.full = positive_float(parameters.get("T_full_open_K"), "T_full_open_K") if "T_full_open_K" in parameters else required_positive(parameters, "T_full_open_K")
        if self.begin >= self.full:
            raise ValueError("T_begin_open_K must be less than T_full_open_K")
        self.scale = positive_float(parameters.get("residual_scale", 0.01), "residual_scale")
        self.role = role(parameters.get("role_override"))
        self.records = [
            temperature_record(component_id, parameters, "T_control_K", "T_control", self.begin),
            fraction_record(component_id, parameters, "opening", "opening", 0.5),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        temp = value(x, registry, self.component_id, "T_control_K")
        opening = value(x, registry, self.component_id, "opening")
        expected = 0.0 if temp <= self.begin else 1.0 if temp >= self.full else (temp - self.begin) / (self.full - self.begin)
        return [residual_record(self, "thermostat_valve_opening", opening - expected, self.scale, "thermostat_valve_opening_mismatch", "Thermostat static opening residual.", self.role)]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "thermal_management", ["static thermostat relation", "no wax motor dynamics", "no hysteresis unless modeled separately"])


class ThreeWayValveMixingModule(BaseModule):
    """Low-fidelity three-way valve mixing relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ThreeWayValveMixingModule", parameters)
        self.mass_scale = positive_float(parameters.get("mass_residual_scale_kg_s", 0.01), "mass_residual_scale_kg_s")
        self.energy_scale = positive_float(parameters.get("energy_residual_scale_kgK_s", 1.0), "energy_residual_scale_kgK_s")
        self.records = [
            mass_flow_record(component_id, parameters, "m_dot_in_1_kg_s", "m_dot_in_1", 0.4),
            temperature_record(component_id, parameters, "T_in_1_K", "T_in_1", 300.0),
            mass_flow_record(component_id, parameters, "m_dot_in_2_kg_s", "m_dot_in_2", 0.6),
            temperature_record(component_id, parameters, "T_in_2_K", "T_in_2", 320.0),
            mass_flow_record(component_id, parameters, "m_dot_out_kg_s", "m_dot_out", 1.0),
            temperature_record(component_id, parameters, "T_out_K", "T_out", 312.0),
            fraction_record(component_id, parameters, "split_fraction", "split_fraction", 0.4),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m1 = value(x, registry, self.component_id, "m_dot_in_1_kg_s")
        t1 = value(x, registry, self.component_id, "T_in_1_K")
        m2 = value(x, registry, self.component_id, "m_dot_in_2_kg_s")
        t2 = value(x, registry, self.component_id, "T_in_2_K")
        mo = value(x, registry, self.component_id, "m_dot_out_kg_s")
        to = value(x, registry, self.component_id, "T_out_K")
        split = value(x, registry, self.component_id, "split_fraction")
        return [
            residual_record(self, "three_way_valve_branch_1_flow", m1 - split * mo, self.mass_scale, "three_way_valve_branch_1_flow_mismatch", "Three-way valve branch 1 flow residual."),
            residual_record(self, "three_way_valve_branch_2_flow", m2 - (1.0 - split) * mo, self.mass_scale, "three_way_valve_branch_2_flow_mismatch", "Three-way valve branch 2 flow residual."),
            residual_record(self, "three_way_valve_mixing_temperature", mo * to - (m1 * t1 + m2 * t2), self.energy_scale, "three_way_valve_mixing_temperature_mismatch", "Three-way valve mixing temperature residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "thermal_management", ["same fluid", "same cp", "no heat loss", "no pressure drop"])


class ChillerSimpleModule(BaseModule):
    """Low-fidelity chiller COP and power audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ChillerSimpleModule", parameters)
        self.scale = positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")
        self.records = [
            power_record(component_id, parameters, "Q_cooling_W", "Q_cooling", 5000.0),
            power_record(component_id, parameters, "P_electric_W", "P_electric", 1000.0),
            bounded_record(component_id, parameters, "COP", None, "COP", 0.0, 10.0, 5.0, 1.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        q = value(x, registry, self.component_id, "Q_cooling_W")
        p = value(x, registry, self.component_id, "P_electric_W")
        cop = value(x, registry, self.component_id, "COP")
        return [residual_record(self, "chiller_cop_power", q - cop * p, self.scale, "chiller_cop_power_mismatch", "Chiller COP power residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "thermal_management", ["algebraic COP relation", "no refrigerant cycle model", "no compressor map", "no transient thermal dynamics"])


class ExpansionTankSimpleModule(BaseModule):
    """Low-fidelity expansion tank fill-fraction audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ExpansionTankSimpleModule", parameters)
        self.scale = positive_float(parameters.get("residual_scale_m3", 0.001), "residual_scale_m3")
        self.records = [
            volume_record(component_id, parameters, "volume_liquid_m3", "volume_liquid", 0.5),
            volume_record(component_id, parameters, "volume_total_m3", "volume_total", 1.0),
            fraction_record(component_id, parameters, "fill_fraction", "fill_fraction", 0.5),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        liquid = value(x, registry, self.component_id, "volume_liquid_m3")
        total = value(x, registry, self.component_id, "volume_total_m3")
        fill = value(x, registry, self.component_id, "fill_fraction")
        return [residual_record(self, "expansion_tank_fill_fraction", liquid - fill * total, self.scale, "expansion_tank_fill_fraction_mismatch", "Expansion tank fill fraction residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "thermal_management", ["simple volume relation", "no pressure bladder model", "no compressibility", "no thermal expansion calculation"])
