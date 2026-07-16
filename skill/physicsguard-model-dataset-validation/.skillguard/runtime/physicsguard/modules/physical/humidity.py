"""Low-fidelity humidity and simple gas mixture audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.physical._common import (
    metadata,
    owned_record,
    positive_float,
    value,
)


class RelativeHumidityFromPartialPressureModule(BaseModule):
    """Relate relative humidity to vapor and saturation partial pressures."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "RelativeHumidityFromPartialPressureModule", parameters)
        self.residual_scale = positive_float(
            parameters.get("residual_scale", 0.01),
            "residual_scale",
        )
        self.denominator_min_abs = positive_float(
            parameters.get("denominator_min_abs", 1e-6),
            "denominator_min_abs",
        )
        self.records = [
            _pressure_record(component_id, parameters, "p_vapor_Pa", "p_vapor", 1000.0),
            _pressure_record(
                component_id,
                parameters,
                "p_saturation_Pa",
                "p_saturation",
                2000.0,
            ),
            owned_record(
                component_id,
                parameters,
                "relative_humidity",
                None,
                "relative_humidity_lower_bound",
                "relative_humidity_upper_bound",
                "relative_humidity_initial_guess",
                "relative_humidity_scale",
                0.0,
                2.0,
                0.5,
                1.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_vapor = value(x, registry, self.component_id, "p_vapor_Pa")
        p_sat = value(x, registry, self.component_id, "p_saturation_Pa")
        if abs(p_sat) < self.denominator_min_abs:
            raise ValueError(f"{self.component_id}: p_saturation_Pa is below denominator_min_abs")
        rh = value(x, registry, self.component_id, "relative_humidity")
        return [
            ResidualRecord(
                name=f"{self.component_id}.relative_humidity",
                value=rh - p_vapor / p_sat,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="relative_humidity_mismatch",
                description="Relative humidity residual relative_humidity - p_vapor/p_saturation.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "humidity",
            [
                "assumes p_saturation is supplied externally",
                "no saturation-pressure correlation",
                "no condensation model",
                "no psychrometric solver",
            ],
        )


class HumidityRatioFromPartialPressureModule(BaseModule):
    """Low-fidelity humidity ratio relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "HumidityRatioFromPartialPressureModule", parameters)
        self.residual_scale = positive_float(
            parameters.get("residual_scale", 0.001),
            "residual_scale",
        )
        self.denominator_min_abs = positive_float(
            parameters.get("denominator_min_abs", 1e-6),
            "denominator_min_abs",
        )
        self.records = [
            _pressure_record(component_id, parameters, "p_total_Pa", "p_total", 101325.0),
            _pressure_record(component_id, parameters, "p_vapor_Pa", "p_vapor", 2000.0),
            owned_record(
                component_id,
                parameters,
                "humidity_ratio_kg_kg",
                "kg/kg",
                "humidity_ratio_lower_bound",
                "humidity_ratio_upper_bound",
                "humidity_ratio_initial_guess",
                "humidity_ratio_scale",
                0.0,
                10.0,
                0.01,
                0.01,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_total = value(x, registry, self.component_id, "p_total_Pa")
        p_vapor = value(x, registry, self.component_id, "p_vapor_Pa")
        denominator = p_total - p_vapor
        if denominator <= self.denominator_min_abs:
            raise ValueError(f"{self.component_id}: p_total_Pa - p_vapor_Pa is not safely positive")
        humidity_ratio = value(x, registry, self.component_id, "humidity_ratio_kg_kg")
        expected = 0.62198 * p_vapor / denominator
        return [
            ResidualRecord(
                name=f"{self.component_id}.humidity_ratio",
                value=humidity_ratio - expected,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="humidity_ratio_mismatch",
                description="Humidity ratio residual humidity_ratio - 0.62198*p_vapor/(p_total - p_vapor).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "humidity",
            [
                "ideal gas psychrometric approximation",
                "no condensation",
                "no saturation pressure calculation",
                "no humid-air property package",
            ],
        )


class WaterVaporMoleFractionModule(BaseModule):
    """Relate water vapor mole fraction to vapor and total pressure."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "WaterVaporMoleFractionModule", parameters)
        self.residual_scale = positive_float(
            parameters.get("residual_scale", 0.01),
            "residual_scale",
        )
        self.denominator_min_abs = positive_float(
            parameters.get("denominator_min_abs", 1e-6),
            "denominator_min_abs",
        )
        self.records = [
            _pressure_record(component_id, parameters, "p_total_Pa", "p_total", 101325.0),
            _pressure_record(component_id, parameters, "p_vapor_Pa", "p_vapor", 2000.0),
            owned_record(
                component_id,
                parameters,
                "x_vapor",
                None,
                "x_vapor_lower_bound",
                "x_vapor_upper_bound",
                "x_vapor_initial_guess",
                "x_vapor_scale",
                0.0,
                1.0,
                0.02,
                0.01,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_total = value(x, registry, self.component_id, "p_total_Pa")
        if abs(p_total) < self.denominator_min_abs:
            raise ValueError(f"{self.component_id}: p_total_Pa is below denominator_min_abs")
        p_vapor = value(x, registry, self.component_id, "p_vapor_Pa")
        x_vapor = value(x, registry, self.component_id, "x_vapor")
        return [
            ResidualRecord(
                name=f"{self.component_id}.water_vapor_mole_fraction",
                value=x_vapor - p_vapor / p_total,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="water_vapor_mole_fraction_mismatch",
                description="Water vapor mole fraction residual x_vapor - p_vapor/p_total.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "humidity",
            ["ideal gas mixture relation", "no condensation", "no saturation check"],
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
        0.0,
        1e7,
        initial_default,
        1e5,
    )
