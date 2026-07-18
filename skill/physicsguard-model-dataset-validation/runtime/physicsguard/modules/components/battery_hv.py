"""Component-level battery and high-voltage power-system audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.components._common import (
    bounded_record,
    check_denominator,
    component_metadata,
    current_record,
    finite_string_list,
    finite_list,
    fraction_record,
    one_d_interp,
    positive_float,
    power_record,
    residual_record,
    required_nonnegative,
    required_positive,
    same_length,
    strictly_increasing_axis,
    value,
    voltage_record,
)


def _soc_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, None, prefix, 0.0, 1.0, initial, 0.01)


class BatterySOCStepModule(BaseModule):
    """Single-step battery SOC audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "BatterySOCStepModule", parameters)
        self.capacity = required_positive(parameters, "capacity_C")
        self.dt = required_positive(parameters, "dt_s")
        self.eta = positive_float(parameters.get("coulombic_efficiency", 1.0), "coulombic_efficiency")
        if self.eta > 1.0:
            raise ValueError("coulombic_efficiency must be <= 1")
        self.sign = parameters.get("sign_convention", "discharge_positive")
        if self.sign not in {"discharge_positive", "charge_positive"}:
            raise ValueError("sign_convention must be 'discharge_positive' or 'charge_positive'")
        self.scale = positive_float(parameters.get("residual_scale_SOC", 0.001), "residual_scale_SOC")
        self.records = [
            _soc_record(component_id, parameters, "SOC_previous", "SOC_previous", 0.8),
            _soc_record(component_id, parameters, "SOC_current", "SOC_current", 0.79),
            current_record(component_id, parameters, "current_A", "current", 10.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        prev = value(x, registry, self.component_id, "SOC_previous")
        cur = value(x, registry, self.component_id, "SOC_current")
        current = value(x, registry, self.component_id, "current_A")
        delta = self.eta * current * self.dt / self.capacity
        expected = prev - delta if self.sign == "discharge_positive" else prev + delta
        return [residual_record(self, "battery_soc_step", cur - expected, self.scale, "battery_soc_step_mismatch", "Battery SOC single-step residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "battery_hv", ["single-step SOC audit", "no OCV dynamics", "no temperature effects", "no degradation", "no balancing"])


class BatteryOCVMapModule(BaseModule):
    """Battery OCV map consistency audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "BatteryOCVMapModule", parameters)
        self.soc_points = strictly_increasing_axis(parameters, "SOC_points")
        self.ocv_points = finite_list(parameters, "OCV_points_V")
        same_length(self.ocv_points, len(self.soc_points), "OCV_points_V")
        self.extrapolation = parameters.get("extrapolation", "error")
        if self.extrapolation not in {"error", "hold"}:
            raise ValueError("extrapolation must be 'error' or 'hold'")
        self.scale = positive_float(parameters.get("residual_scale_V", 0.01), "residual_scale_V")
        self.records = [
            _soc_record(component_id, parameters, "SOC", "SOC", 0.5),
            voltage_record(component_id, parameters, "OCV_V", "OCV", 350.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        soc = value(x, registry, self.component_id, "SOC")
        ocv = value(x, registry, self.component_id, "OCV_V")
        expected = one_d_interp(soc, self.soc_points, self.ocv_points, self.extrapolation, self.component_id)
        return [residual_record(self, "battery_ocv_map", ocv - expected, self.scale, "battery_ocv_map_mismatch", "Battery OCV map residual.")]

    def metadata(self) -> dict[str, Any]:
        metadata = component_metadata(self, "battery_hv", ["map consistency only", "no hysteresis", "no temperature correction unless map includes it", "no electrochemical dynamics"])
        metadata["extrapolation"] = self.extrapolation
        return metadata


class BatteryInternalResistanceModule(BaseModule):
    """Simple battery internal resistance voltage and heat audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "BatteryInternalResistanceModule", parameters)
        self.v_scale = positive_float(parameters.get("residual_scale_V", 0.01), "residual_scale_V")
        self.heat_scale = positive_float(parameters.get("residual_scale_heat_W", 100.0), "residual_scale_heat_W")
        self.sign = parameters.get("sign_convention", "discharge_positive")
        if self.sign not in {"discharge_positive", "charge_positive"}:
            raise ValueError("sign_convention must be 'discharge_positive' or 'charge_positive'")
        self.records = [
            voltage_record(component_id, parameters, "OCV_V", "OCV", 350.0),
            current_record(component_id, parameters, "current_A", "current", 10.0),
            voltage_record(component_id, parameters, "terminal_voltage_V", "terminal_voltage", 349.0),
            bounded_record(component_id, parameters, "R_ohm", "ohm", "R", 0.0, 1e6, 0.1, 0.01),
            power_record(component_id, parameters, "heat_generation_W", "heat_generation", 10.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        ocv = value(x, registry, self.component_id, "OCV_V")
        current = value(x, registry, self.component_id, "current_A")
        term = value(x, registry, self.component_id, "terminal_voltage_V")
        resistance = value(x, registry, self.component_id, "R_ohm")
        heat = value(x, registry, self.component_id, "heat_generation_W")
        expected_v = ocv - current * resistance if self.sign == "discharge_positive" else ocv + current * resistance
        return [
            residual_record(self, "battery_terminal_voltage", term - expected_v, self.v_scale, "battery_terminal_voltage_mismatch", "Battery terminal voltage residual."),
            residual_record(self, "battery_internal_resistance_heat", heat - current**2 * resistance, self.heat_scale, "battery_internal_resistance_heat_mismatch", "Battery I^2R heat residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "battery_hv", ["simple equivalent resistance", "no RC dynamics", "no OCV hysteresis", "no temperature dependence unless R is supplied externally"])


class BatteryPackPowerModule(BaseModule):
    """Battery pack DC power consistency audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "BatteryPackPowerModule", parameters)
        self.sign = parameters.get("sign_convention", "discharge_positive")
        if self.sign not in {"discharge_positive", "charge_positive"}:
            raise ValueError("sign_convention must be 'discharge_positive' or 'charge_positive'")
        self.scale = positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")
        self.records = [
            voltage_record(component_id, parameters, "terminal_voltage_V", "terminal_voltage", 350.0),
            current_record(component_id, parameters, "current_A", "current", 10.0),
            power_record(component_id, parameters, "power_W", "power", 3500.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        voltage = value(x, registry, self.component_id, "terminal_voltage_V")
        current = value(x, registry, self.component_id, "current_A")
        power = value(x, registry, self.component_id, "power_W")
        return [residual_record(self, "battery_pack_power", power - voltage * current, self.scale, "battery_pack_power_mismatch", "Battery pack DC power residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "battery_hv", ["algebraic DC power", "no inverter/converter", "no thermal limits"])


class BatteryPowerLimitCheckModule(BaseModule):
    """Post-check battery power, SOC, and temperature envelopes."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "BatteryPowerLimitCheckModule", parameters)
        self.max_discharge = required_nonnegative(parameters, "max_discharge_power_W")
        self.max_charge = required_nonnegative(parameters, "max_charge_power_W")
        self.soc_min = float(parameters.get("SOC_min", 0.0))
        self.soc_max = float(parameters.get("SOC_max", 1.0))
        if self.soc_min >= self.soc_max:
            raise ValueError("SOC_min must be less than SOC_max")
        self.t_min = float(parameters.get("T_min_K", 250.0))
        self.t_max = float(parameters.get("T_max_K", 350.0))
        if self.t_min >= self.t_max:
            raise ValueError("T_min_K must be less than T_max_K")
        self.scale = positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")
        self.records = [
            power_record(component_id, parameters, "power_W", "power", 1000.0),
            _soc_record(component_id, parameters, "SOC", "SOC", 0.5),
            bounded_record(component_id, parameters, "temperature_K", "K", "temperature", 100.0, 1500.0, 300.0, 10.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        power = value(x, registry, self.component_id, "power_W")
        soc = value(x, registry, self.component_id, "SOC")
        temp = value(x, registry, self.component_id, "temperature_K")
        discharge = max(power - self.max_discharge, 0.0)
        charge = max(-self.max_charge - power, 0.0)
        soc_res = soc - self.soc_max if soc > self.soc_max else soc - self.soc_min if soc < self.soc_min else 0.0
        temp_res = temp - self.t_max if temp > self.t_max else temp - self.t_min if temp < self.t_min else 0.0
        return [
            residual_record(self, "battery_discharge_power_limit", discharge, self.scale, "battery_discharge_power_limit_violation", "Battery discharge power limit post-check.", "post_check"),
            residual_record(self, "battery_charge_power_limit", charge, self.scale, "battery_charge_power_limit_violation", "Battery charge power limit post-check.", "post_check"),
            residual_record(self, "battery_soc_limit", soc_res, 0.01, "battery_soc_limit_violation", "Battery SOC limit post-check.", "post_check"),
            residual_record(self, "battery_temperature_limit", temp_res, 1.0, "battery_temperature_limit_violation", "Battery temperature limit post-check.", "post_check"),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "battery_hv", ["diagnostic envelope only", "no detailed BMS logic", "no dynamic derating map"])


class HVBusPowerBalanceModule(BaseModule):
    """Referenced-variable high-voltage bus algebraic power balance."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "HVBusPowerBalanceModule", parameters)
        self.sources = finite_string_list(parameters, "source_power_variables")
        self.loads = finite_string_list(parameters, "load_power_variables")
        self.storage = parameters.get("storage_power_variables", [])
        if not isinstance(self.storage, list):
            raise ValueError("storage_power_variables must be a list")
        self.storage = [str(item) for item in self.storage]
        self.scale = positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        def total(names: list[str]) -> float:
            return sum(float(x[registry.get_index(name)]) for name in names)

        residual = total(self.sources) - total(self.loads) - total(self.storage)
        return [residual_record(self, "hv_bus_power_balance", residual, self.scale, "hv_bus_power_balance_mismatch", "HV bus algebraic power balance residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "battery_hv", ["algebraic power balance", "caller supplies sign convention", "no bus capacitance dynamics unless storage term is included"])


class ChargerSimpleModule(BaseModule):
    """Low-fidelity charger efficiency power audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ChargerSimpleModule", parameters)
        self.scale = positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")
        self.records = [
            power_record(component_id, parameters, "P_grid_W", "P_grid", 10000.0),
            power_record(component_id, parameters, "P_battery_W", "P_battery", 9000.0),
            bounded_record(component_id, parameters, "efficiency", None, "efficiency", 0.0, 1.5, 0.9, 0.1),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        grid = value(x, registry, self.component_id, "P_grid_W")
        battery = value(x, registry, self.component_id, "P_battery_W")
        eff = value(x, registry, self.component_id, "efficiency")
        return [residual_record(self, "charger_efficiency_power", battery - eff * grid, self.scale, "charger_efficiency_power_mismatch", "Charger efficiency power residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "battery_hv", ["algebraic charger efficiency", "no AC phase model", "no thermal derating", "no charge-control logic"])
