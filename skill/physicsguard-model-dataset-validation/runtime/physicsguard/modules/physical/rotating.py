"""Low-fidelity compressible gas and rotating-machine audit helpers."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.physical._common import (
    finite_float,
    metadata,
    owned_record,
    positive_float,
    required,
    required_positive,
    value,
)


class CompressibleIsentropicCompressorPowerModule(BaseModule):
    """Ideal-gas compressor shaft power sanity check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "CompressibleIsentropicCompressorPowerModule", parameters)
        self.cp_J_kgK = positive_float(parameters.get("cp_J_kgK", 1005.0), "cp_J_kgK")
        self.gamma = positive_float(parameters.get("gamma", 1.4), "gamma")
        if self.gamma <= 1.0:
            raise ValueError("gamma must be > 1")
        self.efficiency = positive_float(parameters.get("efficiency", 0.7), "efficiency")
        if self.efficiency > 1.0:
            raise ValueError("efficiency must be <= 1")
        self.denominator_min_abs = positive_float(
            parameters.get("denominator_min_abs", 1e-12),
            "denominator_min_abs",
        )
        self.residual_scale_W = positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            _pressure_record(component_id, parameters, "p_in_Pa", "p_in", 100000.0),
            _pressure_record(component_id, parameters, "p_out_Pa", "p_out", 200000.0),
            _temperature_record(component_id, parameters, "T_in_K", "T_in", 300.0),
            _mass_flow_record(component_id, parameters),
            _power_record(component_id, parameters, "P_shaft_W", "P_shaft", 1000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_in = value(x, registry, self.component_id, "p_in_Pa")
        if abs(p_in) < self.denominator_min_abs:
            raise ValueError(f"{self.component_id}: p_in_Pa is below denominator_min_abs")
        p_out = value(x, registry, self.component_id, "p_out_Pa")
        pressure_ratio = p_out / p_in
        if pressure_ratio <= 0:
            raise ValueError(f"{self.component_id}: pressure_ratio must be positive")
        t_in = value(x, registry, self.component_id, "T_in_K")
        m_dot = value(x, registry, self.component_id, "m_dot_kg_s")
        p_shaft = value(x, registry, self.component_id, "P_shaft_W")
        exponent = (self.gamma - 1.0) / self.gamma
        calculated = (
            m_dot
            * self.cp_J_kgK
            * t_in
            * (pressure_ratio**exponent - 1.0)
            / self.efficiency
        )
        return [
            ResidualRecord(
                name=f"{self.component_id}.compressible_isentropic_compressor_power",
                value=p_shaft - calculated,
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="compressible_isentropic_compressor_power_mismatch",
                description="Ideal-gas compressor shaft power residual.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "rotating_machine",
            [
                "ideal gas",
                "isentropic-efficiency approximation",
                "no compressor map",
                "no choking",
                "no surge",
                "no motor model",
                "no heat loss",
            ],
        )


class IsentropicGasTemperatureRiseModule(BaseModule):
    """Ideal-gas compressor outlet temperature sanity check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "IsentropicGasTemperatureRiseModule", parameters)
        self.gamma = positive_float(parameters.get("gamma", 1.4), "gamma")
        if self.gamma <= 1.0:
            raise ValueError("gamma must be > 1")
        self.efficiency = positive_float(parameters.get("efficiency", 0.7), "efficiency")
        if self.efficiency > 1.0:
            raise ValueError("efficiency must be <= 1")
        self.denominator_min_abs = positive_float(
            parameters.get("denominator_min_abs", 1e-12),
            "denominator_min_abs",
        )
        self.residual_scale_K = positive_float(
            parameters.get("residual_scale_K", 10.0),
            "residual_scale_K",
        )
        self.records = [
            _pressure_record(component_id, parameters, "p_in_Pa", "p_in", 100000.0),
            _pressure_record(component_id, parameters, "p_out_Pa", "p_out", 200000.0),
            _temperature_record(component_id, parameters, "T_in_K", "T_in", 300.0),
            _temperature_record(component_id, parameters, "T_out_K", "T_out", 370.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_in = value(x, registry, self.component_id, "p_in_Pa")
        if abs(p_in) < self.denominator_min_abs:
            raise ValueError(f"{self.component_id}: p_in_Pa is below denominator_min_abs")
        p_out = value(x, registry, self.component_id, "p_out_Pa")
        pressure_ratio = p_out / p_in
        if pressure_ratio <= 0:
            raise ValueError(f"{self.component_id}: pressure_ratio must be positive")
        t_in = value(x, registry, self.component_id, "T_in_K")
        t_out = value(x, registry, self.component_id, "T_out_K")
        exponent = (self.gamma - 1.0) / self.gamma
        calculated = t_in * (1.0 + (pressure_ratio**exponent - 1.0) / self.efficiency)
        return [
            ResidualRecord(
                name=f"{self.component_id}.isentropic_gas_temperature_rise",
                value=t_out - calculated,
                scale=self.residual_scale_K,
                source=self.component_id,
                role="equation",
                diagnostic_key="isentropic_gas_temperature_rise_mismatch",
                description="Ideal-gas compressor outlet temperature residual.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "rotating_machine",
            [
                "ideal gas",
                "compressor temperature sanity check",
                "no intercooling",
                "no real-gas correction",
                "no compressor map",
            ],
        )


class RotatingMachineAffinityModule(BaseModule):
    """Low-fidelity affinity-law sanity check for pump/fan-like machines."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "RotatingMachineAffinityModule", parameters)
        self.nominal_speed_rad_s = required_positive(parameters, "nominal_speed_rad_s")
        self.nominal_m_dot_kg_s = finite_float(required(parameters, "nominal_m_dot_kg_s"), "nominal_m_dot_kg_s")
        self.nominal_delta_p_Pa = finite_float(required(parameters, "nominal_delta_p_Pa"), "nominal_delta_p_Pa")
        self.nominal_P_shaft_W = finite_float(required(parameters, "nominal_P_shaft_W"), "nominal_P_shaft_W")
        self.flow_residual_scale_kg_s = positive_float(
            parameters.get("flow_residual_scale_kg_s", 0.01),
            "flow_residual_scale_kg_s",
        )
        self.pressure_residual_scale_Pa = positive_float(
            parameters.get("pressure_residual_scale_Pa", 1000.0),
            "pressure_residual_scale_Pa",
        )
        self.power_residual_scale_W = positive_float(
            parameters.get("power_residual_scale_W", 1000.0),
            "power_residual_scale_W",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "speed_rad_s",
                "rad/s",
                "speed_lower_bound",
                "speed_upper_bound",
                "speed_initial_guess",
                "speed_scale",
                0.0,
                1e5,
                self.nominal_speed_rad_s,
                self.nominal_speed_rad_s,
            ),
            _mass_flow_record(component_id, parameters),
            owned_record(
                component_id,
                parameters,
                "delta_p_Pa",
                "Pa",
                "delta_p_lower_bound",
                "delta_p_upper_bound",
                "delta_p_initial_guess",
                "delta_p_scale",
                -1e7,
                1e7,
                self.nominal_delta_p_Pa,
                1e5,
            ),
            _power_record(component_id, parameters, "P_shaft_W", "P_shaft", self.nominal_P_shaft_W),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        speed = value(x, registry, self.component_id, "speed_rad_s")
        speed_ratio = speed / self.nominal_speed_rad_s
        m_dot = value(x, registry, self.component_id, "m_dot_kg_s")
        delta_p = value(x, registry, self.component_id, "delta_p_Pa")
        power = value(x, registry, self.component_id, "P_shaft_W")
        return [
            ResidualRecord(
                name=f"{self.component_id}.affinity_flow",
                value=m_dot - self.nominal_m_dot_kg_s * speed_ratio,
                scale=self.flow_residual_scale_kg_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="rotating_machine_affinity_flow_mismatch",
                description="Affinity-law flow residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.affinity_pressure",
                value=delta_p - self.nominal_delta_p_Pa * speed_ratio**2,
                scale=self.pressure_residual_scale_Pa,
                source=self.component_id,
                role="equation",
                diagnostic_key="rotating_machine_affinity_pressure_mismatch",
                description="Affinity-law pressure residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.affinity_power",
                value=power - self.nominal_P_shaft_W * speed_ratio**3,
                scale=self.power_residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="rotating_machine_affinity_power_mismatch",
                description="Affinity-law power residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "rotating_machine",
            [
                "affinity-law sanity check only",
                "same machine and similar operating conditions",
                "no pump/compressor/fan map",
                "no efficiency curve",
                "no surge/cavitation/choking",
            ],
        )


def _pressure_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    prefix: str,
    initial_default: float,
) -> VariableRecord:
    return owned_record(
        component_id,
        parameters,
        local_name,
        "Pa",
        f"{prefix}_lower_bound",
        f"{prefix}_upper_bound",
        f"{prefix}_initial_guess",
        f"{prefix}_scale",
        1e3,
        1e7,
        initial_default,
        1e5,
    )


def _temperature_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    prefix: str,
    initial_default: float,
) -> VariableRecord:
    return owned_record(
        component_id,
        parameters,
        local_name,
        "K",
        f"{prefix}_lower_bound",
        f"{prefix}_upper_bound",
        f"{prefix}_initial_guess",
        f"{prefix}_scale",
        100.0,
        1000.0,
        initial_default,
        100.0,
    )


def _mass_flow_record(component_id: str, parameters: dict[str, Any]) -> VariableRecord:
    return owned_record(
        component_id,
        parameters,
        "m_dot_kg_s",
        "kg/s",
        "m_dot_lower_bound",
        "m_dot_upper_bound",
        "m_dot_initial_guess",
        "m_dot_scale",
        0.0,
        100.0,
        1.0,
        1.0,
    )


def _power_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    prefix: str,
    initial_default: float,
) -> VariableRecord:
    return owned_record(
        component_id,
        parameters,
        local_name,
        "W",
        f"{prefix}_lower_bound",
        f"{prefix}_upper_bound",
        f"{prefix}_initial_guess",
        f"{prefix}_scale",
        -1e8,
        1e8,
        initial_default,
        1000.0,
    )
