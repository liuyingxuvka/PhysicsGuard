"""Component-level low-fidelity internal combustion engine audit modules."""

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
    finite_grid,
    mass_flow_record,
    omega_record,
    positive_float,
    power_record,
    strictly_increasing_axis,
    torque_record,
    value,
)


class EngineSimpleEfficiencyModule(BaseModule):
    """Low-fidelity engine power and fuel efficiency audit component."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "EngineSimpleEfficiencyModule", parameters)
        self.residual_scale_power_W = positive_float(
            parameters.get("residual_scale_power_W", 1000.0),
            "residual_scale_power_W",
        )
        self.records = [
            mass_flow_record(component_id, parameters, "fuel_m_dot_kg_s", "fuel_m_dot", 0.01),
            bounded_record(component_id, parameters, "LHV_J_kg", "J/kg", "LHV", 1.0, 1e9, 42e6, 1e6),
            power_record(component_id, parameters, "brake_power_W", "brake_power", 10000.0),
            bounded_record(
                component_id,
                parameters,
                "thermal_efficiency",
                None,
                "thermal_efficiency",
                1e-9,
                1.5,
                0.3,
                0.1,
            ),
            torque_record(component_id, parameters),
            omega_record(component_id, parameters),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        fuel_m_dot = value(x, registry, self.component_id, "fuel_m_dot_kg_s")
        lhv = value(x, registry, self.component_id, "LHV_J_kg")
        brake_power = value(x, registry, self.component_id, "brake_power_W")
        efficiency = value(x, registry, self.component_id, "thermal_efficiency")
        torque = value(x, registry, self.component_id, "torque_Nm")
        omega = value(x, registry, self.component_id, "omega_rad_s")
        return [
            ResidualRecord(
                name=f"{self.component_id}.engine_torque_speed_power",
                value=brake_power - torque * omega,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="engine_torque_speed_power_mismatch",
                description="Engine torque-speed brake power residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.engine_fuel_efficiency",
                value=brake_power - efficiency * fuel_m_dot * lhv,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="engine_fuel_efficiency_mismatch",
                description="Engine fuel-energy efficiency residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "engine",
            [
                "algebraic engine sanity check",
                "no combustion model",
                "no emissions model",
                "no turbocharger",
                "no transient engine dynamics",
                "no engine map unless paired with map module",
            ],
        )


class EngineBSFCMapModule(BaseModule):
    """Map-based engine fuel consumption audit component."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "EngineBSFCMapModule", parameters)
        self.speed_points = strictly_increasing_axis(parameters, "speed_points_rad_s")
        self.torque_points = strictly_increasing_axis(parameters, "torque_points_Nm")
        self.bsfc_values = finite_grid(
            parameters,
            "bsfc_values_kg_J",
            rows=len(self.torque_points),
            cols=len(self.speed_points),
        )
        self.extrapolation = parameters.get("extrapolation", "error")
        if self.extrapolation not in {"error", "hold"}:
            raise ValueError("extrapolation must be 'error' or 'hold'")
        self.residual_scale_power_W = positive_float(
            parameters.get("residual_scale_power_W", 1000.0),
            "residual_scale_power_W",
        )
        self.residual_scale_fuel_kg_s = positive_float(
            parameters.get("residual_scale_fuel_kg_s", 1e-4),
            "residual_scale_fuel_kg_s",
        )
        self.records = [
            omega_record(component_id, parameters, "speed_rad_s", "speed"),
            torque_record(component_id, parameters),
            power_record(component_id, parameters, "brake_power_W", "brake_power", 10000.0),
            mass_flow_record(component_id, parameters, "fuel_m_dot_kg_s", "fuel_m_dot", 0.001),
            bounded_record(component_id, parameters, "bsfc_kg_J", "kg/J", "bsfc", 0.0, 1.0, 1e-8, 1e-8),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        speed = value(x, registry, self.component_id, "speed_rad_s")
        torque = value(x, registry, self.component_id, "torque_Nm")
        brake_power = value(x, registry, self.component_id, "brake_power_W")
        fuel_flow = value(x, registry, self.component_id, "fuel_m_dot_kg_s")
        bsfc = value(x, registry, self.component_id, "bsfc_kg_J")
        mapped_bsfc = bilinear_interp(
            speed,
            torque,
            self.speed_points,
            self.torque_points,
            self.bsfc_values,
            self.extrapolation,
            self.component_id,
        )
        return [
            ResidualRecord(
                name=f"{self.component_id}.engine_bsfc_power",
                value=brake_power - torque * speed,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="engine_bsfc_power_mismatch",
                description="Engine BSFC brake power residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.engine_bsfc_fuel_flow",
                value=fuel_flow - mapped_bsfc * brake_power,
                scale=self.residual_scale_fuel_kg_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="engine_bsfc_fuel_flow_mismatch",
                description="Engine BSFC fuel flow residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.engine_bsfc_map",
                value=bsfc - mapped_bsfc,
                scale=1e-8,
                source=self.component_id,
                role="equation",
                diagnostic_key="engine_bsfc_map_mismatch",
                description="Engine BSFC map consistency residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        metadata = component_metadata(
            self,
            "engine",
            [
                "map consistency only",
                "no combustion model",
                "no emissions model",
                "no turbocharger",
                "no transient dynamics",
                "bsfc units must be kg/J internally",
            ],
        )
        metadata["extrapolation"] = self.extrapolation
        return metadata
