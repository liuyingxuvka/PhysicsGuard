"""Component-level low-fidelity compressor and pump audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.components._common import (
    bilinear_interp,
    bounded_record,
    component_metadata,
    efficiency_record,
    finite_grid,
    mass_flow_record,
    omega_record,
    positive_float,
    power_record,
    pressure_record,
    strictly_increasing_axis,
    temperature_record,
    value,
    xy_record,
)


class CompressorSimpleModule(BaseModule):
    """Low-fidelity ideal-gas compressor component audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "CompressorSimpleModule", parameters)
        self.cp_J_kgK = positive_float(parameters.get("cp_J_kgK", 1005.0), "cp_J_kgK")
        self.gamma = positive_float(parameters.get("gamma", 1.4), "gamma")
        if self.gamma <= 1.0:
            raise ValueError("gamma must be > 1")
        self.denominator_min_abs = positive_float(
            parameters.get("denominator_min_abs", 1e-12),
            "denominator_min_abs",
        )
        self.residual_scale_power_W = positive_float(
            parameters.get("residual_scale_power_W", 1000.0),
            "residual_scale_power_W",
        )
        self.residual_scale_temperature_K = positive_float(
            parameters.get("residual_scale_temperature_K", 10.0),
            "residual_scale_temperature_K",
        )
        self.residual_scale_pressure_ratio = positive_float(
            parameters.get("residual_scale_pressure_ratio", 0.05),
            "residual_scale_pressure_ratio",
        )
        self.records = _compressor_records(component_id, parameters)

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        vals = _compressor_values(x, registry, self.component_id)
        pressure_ratio = _safe_pressure_ratio(vals["p_in_Pa"], vals["p_out_Pa"], self.denominator_min_abs, self.component_id)
        t_out_expected, power_expected = _compressor_temperature_power(
            vals["T_in_K"],
            vals["m_dot_kg_s"],
            vals["efficiency"],
            pressure_ratio,
            self.cp_J_kgK,
            self.gamma,
            self.component_id,
        )
        return [
            ResidualRecord(
                name=f"{self.component_id}.compressor_pressure_ratio",
                value=vals["pressure_ratio"] - pressure_ratio,
                scale=self.residual_scale_pressure_ratio,
                source=self.component_id,
                role="equation",
                diagnostic_key="compressor_pressure_ratio_mismatch",
                description="Compressor pressure-ratio residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.compressor_temperature_rise",
                value=vals["T_out_K"] - t_out_expected,
                scale=self.residual_scale_temperature_K,
                source=self.component_id,
                role="equation",
                diagnostic_key="compressor_temperature_rise_mismatch",
                description="Compressor ideal-gas outlet temperature residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.compressor_power",
                value=vals["P_shaft_W"] - power_expected,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="compressor_power_mismatch",
                description="Compressor shaft power residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "fluid_machine",
            [
                "ideal gas",
                "isentropic-efficiency approximation",
                "no compressor map",
                "no surge",
                "no choking",
                "no heat loss",
                "no motor model",
            ],
        )


class CompressorMapSimpleModule(BaseModule):
    """Map-based compressor consistency and ideal-gas power sanity check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "CompressorMapSimpleModule", parameters)
        self.speed_points = strictly_increasing_axis(parameters, "speed_points")
        self.flow_points = strictly_increasing_axis(parameters, "flow_points")
        self.pressure_ratio_values = finite_grid(
            parameters,
            "pressure_ratio_values",
            rows=len(self.flow_points),
            cols=len(self.speed_points),
        )
        self.efficiency_values = finite_grid(
            parameters,
            "efficiency_values",
            rows=len(self.flow_points),
            cols=len(self.speed_points),
        )
        self.extrapolation = parameters.get("extrapolation", "error")
        if self.extrapolation not in {"error", "hold"}:
            raise ValueError("extrapolation must be 'error' or 'hold'")
        self.cp_J_kgK = positive_float(parameters.get("cp_J_kgK", 1005.0), "cp_J_kgK")
        self.gamma = positive_float(parameters.get("gamma", 1.4), "gamma")
        if self.gamma <= 1.0:
            raise ValueError("gamma must be > 1")
        self.denominator_min_abs = positive_float(
            parameters.get("denominator_min_abs", 1e-12),
            "denominator_min_abs",
        )
        self.residual_scale_map = positive_float(parameters.get("residual_scale_map", 0.01), "residual_scale_map")
        self.residual_scale_power_W = positive_float(
            parameters.get("residual_scale_power_W", 1000.0),
            "residual_scale_power_W",
        )
        self.residual_scale_temperature_K = positive_float(
            parameters.get("residual_scale_temperature_K", 10.0),
            "residual_scale_temperature_K",
        )
        self.residual_scale_pressure_ratio = positive_float(
            parameters.get("residual_scale_pressure_ratio", 0.05),
            "residual_scale_pressure_ratio",
        )
        self.records = [
            xy_record(component_id, parameters, "corrected_speed", "corrected_speed"),
            xy_record(component_id, parameters, "corrected_mass_flow", "corrected_mass_flow"),
            *_compressor_records(component_id, parameters),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        corrected_speed = value(x, registry, self.component_id, "corrected_speed")
        corrected_flow = value(x, registry, self.component_id, "corrected_mass_flow")
        vals = _compressor_values(x, registry, self.component_id)
        mapped_pr = bilinear_interp(
            corrected_speed,
            corrected_flow,
            self.speed_points,
            self.flow_points,
            self.pressure_ratio_values,
            self.extrapolation,
            self.component_id,
        )
        mapped_eff = bilinear_interp(
            corrected_speed,
            corrected_flow,
            self.speed_points,
            self.flow_points,
            self.efficiency_values,
            self.extrapolation,
            self.component_id,
        )
        pressure_ratio = _safe_pressure_ratio(vals["p_in_Pa"], vals["p_out_Pa"], self.denominator_min_abs, self.component_id)
        t_out_expected, power_expected = _compressor_temperature_power(
            vals["T_in_K"],
            vals["m_dot_kg_s"],
            vals["efficiency"],
            pressure_ratio,
            self.cp_J_kgK,
            self.gamma,
            self.component_id,
        )
        return [
            ResidualRecord(
                name=f"{self.component_id}.compressor_pressure_ratio_map",
                value=vals["pressure_ratio"] - mapped_pr,
                scale=self.residual_scale_pressure_ratio,
                source=self.component_id,
                role="equation",
                diagnostic_key="compressor_pressure_ratio_map_mismatch",
                description="Compressor pressure-ratio map residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.compressor_efficiency_map",
                value=vals["efficiency"] - mapped_eff,
                scale=self.residual_scale_map,
                source=self.component_id,
                role="equation",
                diagnostic_key="compressor_efficiency_map_mismatch",
                description="Compressor efficiency map residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.compressor_pressure_ratio",
                value=vals["pressure_ratio"] - pressure_ratio,
                scale=self.residual_scale_pressure_ratio,
                source=self.component_id,
                role="equation",
                diagnostic_key="compressor_pressure_ratio_mismatch",
                description="Compressor pressure-ratio residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.compressor_temperature_rise",
                value=vals["T_out_K"] - t_out_expected,
                scale=self.residual_scale_temperature_K,
                source=self.component_id,
                role="equation",
                diagnostic_key="compressor_temperature_rise_mismatch",
                description="Compressor outlet temperature residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.compressor_power",
                value=vals["P_shaft_W"] - power_expected,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="compressor_power_mismatch",
                description="Compressor shaft power residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        metadata = component_metadata(
            self,
            "fluid_machine",
            [
                "map consistency and ideal-gas power sanity check only",
                "no surge/choke modeling",
                "no full compressor solver",
                "corrected variables are assumed provided by caller",
            ],
        )
        metadata["extrapolation"] = self.extrapolation
        return metadata


class PumpSimpleModule(BaseModule):
    """Low-fidelity incompressible pump power audit component."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "PumpSimpleModule", parameters)
        self.rho_kg_m3 = positive_float(parameters.get("rho_kg_m3", 997.0), "rho_kg_m3")
        self.residual_scale_power_W = positive_float(
            parameters.get("residual_scale_power_W", 1000.0),
            "residual_scale_power_W",
        )
        self.records = [
            pressure_record(component_id, parameters, "p_in_Pa", "p_in", 100000.0),
            pressure_record(component_id, parameters, "p_out_Pa", "p_out", 200000.0),
            mass_flow_record(component_id, parameters, "m_dot_kg_s", "m_dot", 1.0),
            power_record(component_id, parameters, "P_shaft_W", "P_shaft", 1000.0),
            efficiency_record(component_id, parameters),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_in = value(x, registry, self.component_id, "p_in_Pa")
        p_out = value(x, registry, self.component_id, "p_out_Pa")
        m_dot = value(x, registry, self.component_id, "m_dot_kg_s")
        power = value(x, registry, self.component_id, "P_shaft_W")
        efficiency = _safe_efficiency(value(x, registry, self.component_id, "efficiency"), self.component_id)
        expected = ((p_out - p_in) * m_dot / self.rho_kg_m3) / efficiency
        return [
            ResidualRecord(
                name=f"{self.component_id}.pump_power",
                value=power - expected,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="pump_power_mismatch",
                description="Pump hydraulic shaft power residual.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "fluid_machine",
            [
                "incompressible pump power check",
                "no pump map",
                "no speed relation",
                "no cavitation",
                "no motor model",
            ],
        )


class PumpMapSimpleModule(BaseModule):
    """Map-based pump component consistency and hydraulic power check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "PumpMapSimpleModule", parameters)
        self.speed_points = strictly_increasing_axis(parameters, "speed_points")
        self.flow_points = strictly_increasing_axis(parameters, "flow_points")
        self.delta_p_values = finite_grid(
            parameters,
            "delta_p_values",
            rows=len(self.flow_points),
            cols=len(self.speed_points),
        )
        self.efficiency_values = finite_grid(
            parameters,
            "efficiency_values",
            rows=len(self.flow_points),
            cols=len(self.speed_points),
        )
        self.extrapolation = parameters.get("extrapolation", "error")
        if self.extrapolation not in {"error", "hold"}:
            raise ValueError("extrapolation must be 'error' or 'hold'")
        self.rho_kg_m3 = positive_float(parameters.get("rho_kg_m3", 997.0), "rho_kg_m3")
        self.residual_scale_pressure_Pa = positive_float(
            parameters.get("residual_scale_pressure_Pa", 1000.0),
            "residual_scale_pressure_Pa",
        )
        self.residual_scale_efficiency = positive_float(
            parameters.get("residual_scale_efficiency", 0.01),
            "residual_scale_efficiency",
        )
        self.residual_scale_power_W = positive_float(
            parameters.get("residual_scale_power_W", 1000.0),
            "residual_scale_power_W",
        )
        self.records = [
            omega_record(component_id, parameters, "speed_rad_s", "speed"),
            mass_flow_record(component_id, parameters, "m_dot_kg_s", "m_dot", 1.0),
            bounded_record(component_id, parameters, "delta_p_Pa", "Pa", "delta_p", -1e8, 1e8, 100000.0, 1e5),
            efficiency_record(component_id, parameters),
            power_record(component_id, parameters, "P_shaft_W", "P_shaft", 1000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        speed = value(x, registry, self.component_id, "speed_rad_s")
        m_dot = value(x, registry, self.component_id, "m_dot_kg_s")
        delta_p = value(x, registry, self.component_id, "delta_p_Pa")
        efficiency = value(x, registry, self.component_id, "efficiency")
        power = value(x, registry, self.component_id, "P_shaft_W")
        mapped_delta_p = bilinear_interp(
            speed,
            m_dot,
            self.speed_points,
            self.flow_points,
            self.delta_p_values,
            self.extrapolation,
            self.component_id,
        )
        mapped_efficiency = bilinear_interp(
            speed,
            m_dot,
            self.speed_points,
            self.flow_points,
            self.efficiency_values,
            self.extrapolation,
            self.component_id,
        )
        safe_efficiency = _safe_efficiency(efficiency, self.component_id)
        expected_power = (delta_p * m_dot / self.rho_kg_m3) / safe_efficiency
        return [
            ResidualRecord(
                name=f"{self.component_id}.pump_delta_p_map",
                value=delta_p - mapped_delta_p,
                scale=self.residual_scale_pressure_Pa,
                source=self.component_id,
                role="equation",
                diagnostic_key="pump_delta_p_map_mismatch",
                description="Pump pressure map residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.pump_efficiency_map",
                value=efficiency - mapped_efficiency,
                scale=self.residual_scale_efficiency,
                source=self.component_id,
                role="equation",
                diagnostic_key="pump_efficiency_map_mismatch",
                description="Pump efficiency map residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.pump_power",
                value=power - expected_power,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="pump_power_mismatch",
                description="Pump hydraulic shaft power residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        metadata = component_metadata(
            self,
            "fluid_machine",
            [
                "map consistency and hydraulic power check only",
                "no cavitation",
                "no detailed pump dynamics",
            ],
        )
        metadata["extrapolation"] = self.extrapolation
        return metadata


def _compressor_records(component_id: str, parameters: dict[str, Any]) -> list[VariableRecord]:
    return [
        pressure_record(component_id, parameters, "p_in_Pa", "p_in", 100000.0),
        pressure_record(component_id, parameters, "p_out_Pa", "p_out", 200000.0),
        temperature_record(component_id, parameters, "T_in_K", "T_in", 300.0),
        temperature_record(component_id, parameters, "T_out_K", "T_out", 370.0),
        mass_flow_record(component_id, parameters, "m_dot_kg_s", "m_dot", 0.1),
        power_record(component_id, parameters, "P_shaft_W", "P_shaft", 1000.0),
        bounded_record(component_id, parameters, "pressure_ratio", None, "pressure_ratio", 0.0, 100.0, 2.0, 0.1),
        efficiency_record(component_id, parameters),
    ]


def _compressor_values(x: np.ndarray, registry: VariableRegistry, component_id: str) -> dict[str, float]:
    return {
        "p_in_Pa": value(x, registry, component_id, "p_in_Pa"),
        "p_out_Pa": value(x, registry, component_id, "p_out_Pa"),
        "T_in_K": value(x, registry, component_id, "T_in_K"),
        "T_out_K": value(x, registry, component_id, "T_out_K"),
        "m_dot_kg_s": value(x, registry, component_id, "m_dot_kg_s"),
        "P_shaft_W": value(x, registry, component_id, "P_shaft_W"),
        "pressure_ratio": value(x, registry, component_id, "pressure_ratio"),
        "efficiency": value(x, registry, component_id, "efficiency"),
    }


def _safe_pressure_ratio(p_in: float, p_out: float, minimum: float, component_id: str) -> float:
    if abs(p_in) < minimum:
        raise ValueError(f"{component_id}: p_in_Pa is below denominator_min_abs")
    pressure_ratio = p_out / p_in
    if pressure_ratio <= 0:
        raise ValueError(f"{component_id}: pressure_ratio must be positive")
    return pressure_ratio


def _safe_efficiency(efficiency: float, component_id: str) -> float:
    if efficiency <= 0.0:
        raise ValueError(f"{component_id}: efficiency must be positive")
    return efficiency


def _compressor_temperature_power(
    t_in: float,
    m_dot: float,
    efficiency: float,
    pressure_ratio: float,
    cp: float,
    gamma: float,
    component_id: str,
) -> tuple[float, float]:
    safe_efficiency = _safe_efficiency(efficiency, component_id)
    exponent = (gamma - 1.0) / gamma
    rise_factor = pressure_ratio**exponent - 1.0
    t_out = t_in * (1.0 + rise_factor / safe_efficiency)
    power = m_dot * cp * t_in * rise_factor / safe_efficiency
    return t_out, power
