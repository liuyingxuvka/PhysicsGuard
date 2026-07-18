"""Generic component-level map audit modules."""

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
    positive_float,
    role,
    strictly_increasing_axis,
    value,
    xy_record,
)


class LookupTable2DModule(BaseModule):
    """Low-fidelity 2D lookup-table consistency check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "LookupTable2DModule", parameters)
        self.x_points = strictly_increasing_axis(parameters, "x_points")
        self.y_points = strictly_increasing_axis(parameters, "y_points")
        self.z_values = finite_grid(
            parameters,
            "z_values",
            rows=len(self.y_points),
            cols=len(self.x_points),
        )
        self.extrapolation = parameters.get("extrapolation", "error")
        if self.extrapolation not in {"error", "hold"}:
            raise ValueError("extrapolation must be 'error' or 'hold'")
        self.role = role(parameters.get("role_override"))
        self.residual_scale = positive_float(parameters.get("residual_scale", 1.0), "residual_scale")
        self.records = [
            xy_record(component_id, parameters, "x", "x"),
            xy_record(component_id, parameters, "y", "y"),
            xy_record(component_id, parameters, "z", "z"),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        x_value = value(x, registry, self.component_id, "x")
        y_value = value(x, registry, self.component_id, "y")
        z_value = value(x, registry, self.component_id, "z")
        expected = bilinear_interp(
            x_value,
            y_value,
            self.x_points,
            self.y_points,
            self.z_values,
            self.extrapolation,
            self.component_id,
        )
        return [
            ResidualRecord(
                name=f"{self.component_id}.lookup_table_2d",
                value=z_value - expected,
                scale=self.residual_scale,
                source=self.component_id,
                role=self.role,
                diagnostic_key="lookup_table_2d_mismatch",
                description="2D lookup residual z - bilinear_interp(x, y).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        metadata = component_metadata(
            self,
            "map",
            [
                "consistency check only",
                "no map smoothing",
                "no physical interpretation by itself",
                "map units are caller responsibility",
            ],
        )
        metadata["extrapolation"] = self.extrapolation
        return metadata


class EfficiencyMap2DModule(BaseModule):
    """Semantic 2D efficiency-map consistency check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "EfficiencyMap2DModule", parameters)
        self.x_points = strictly_increasing_axis(parameters, "x_points")
        self.y_points = strictly_increasing_axis(parameters, "y_points")
        self.efficiency_values = finite_grid(
            parameters,
            "efficiency_values",
            rows=len(self.y_points),
            cols=len(self.x_points),
        )
        self.extrapolation = parameters.get("extrapolation", "error")
        if self.extrapolation not in {"error", "hold"}:
            raise ValueError("extrapolation must be 'error' or 'hold'")
        self.residual_scale = positive_float(parameters.get("residual_scale", 0.01), "residual_scale")
        self.records = [
            xy_record(component_id, parameters, "x", "x"),
            xy_record(component_id, parameters, "y", "y"),
            bounded_record(
                component_id,
                parameters,
                "efficiency",
                None,
                "efficiency",
                0.0,
                1.5,
                0.8,
                0.1,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        x_value = value(x, registry, self.component_id, "x")
        y_value = value(x, registry, self.component_id, "y")
        efficiency = value(x, registry, self.component_id, "efficiency")
        expected = bilinear_interp(
            x_value,
            y_value,
            self.x_points,
            self.y_points,
            self.efficiency_values,
            self.extrapolation,
            self.component_id,
        )
        return [
            ResidualRecord(
                name=f"{self.component_id}.efficiency_map_2d",
                value=efficiency - expected,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="efficiency_map_2d_mismatch",
                description="2D efficiency-map residual efficiency - map(x, y).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        metadata = component_metadata(
            self,
            "map",
            [
                "map consistency only",
                "no physical model",
                "efficiency greater than one may be diagnostically suspicious",
            ],
        )
        metadata["extrapolation"] = self.extrapolation
        return metadata
