"""Low-fidelity tank and inventory audit helper modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.physical._common import metadata, owned_record, positive_float, required_positive, value


class TankLevelVolumeModule(BaseModule):
    """Relate tank level to volume for a constant cross-section area."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "TankLevelVolumeModule", parameters)
        self.area_m2 = required_positive(parameters, "area_m2")
        self.residual_scale_m3 = positive_float(
            parameters.get("residual_scale_m3", 0.001),
            "residual_scale_m3",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "level_m",
                "m",
                "level_lower_bound",
                "level_upper_bound",
                "level_initial_guess",
                "level_scale",
                0.0,
                100.0,
                1.0,
                1.0,
            ),
            owned_record(
                component_id,
                parameters,
                "volume_m3",
                "m^3",
                "volume_lower_bound",
                "volume_upper_bound",
                "volume_initial_guess",
                "volume_scale",
                0.0,
                1e6,
                1.0,
                1.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        level = value(x, registry, self.component_id, "level_m")
        volume = value(x, registry, self.component_id, "volume_m3")
        return [
            ResidualRecord(
                name=f"{self.component_id}.tank_level_volume",
                value=volume - self.area_m2 * level,
                scale=self.residual_scale_m3,
                source=self.component_id,
                role="equation",
                diagnostic_key="tank_level_volume_mismatch",
                description="Tank level/volume residual volume - area*level.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "tank",
            ["constant cross-sectional area", "no sloshing", "no geometry details"],
        )


class TankVolumeRateModule(BaseModule):
    """Single-step tank volume balance."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "TankVolumeRateModule", parameters)
        self.dt_s = required_positive(parameters, "dt_s")
        self.residual_scale_m3 = positive_float(
            parameters.get("residual_scale_m3", 0.001),
            "residual_scale_m3",
        )
        self.records = [
            _volume_record(component_id, parameters, "volume_previous_m3", "volume_previous", 1.0),
            _volume_flow_record(component_id, parameters, "V_dot_in_m3_s", "V_dot_in", 0.1),
            _volume_flow_record(component_id, parameters, "V_dot_out_m3_s", "V_dot_out", 0.0),
            _volume_record(component_id, parameters, "volume_current_m3", "volume_current", 1.1),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        previous = value(x, registry, self.component_id, "volume_previous_m3")
        v_in = value(x, registry, self.component_id, "V_dot_in_m3_s")
        v_out = value(x, registry, self.component_id, "V_dot_out_m3_s")
        current = value(x, registry, self.component_id, "volume_current_m3")
        expected = previous + (v_in - v_out) * self.dt_s
        return [
            ResidualRecord(
                name=f"{self.component_id}.tank_volume_rate",
                value=current - expected,
                scale=self.residual_scale_m3,
                source=self.component_id,
                role="equation",
                diagnostic_key="tank_volume_rate_mismatch",
                description="Single-step tank volume residual volume_current - (volume_previous + (V_dot_in - V_dot_out)*dt).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "tank",
            [
                "single-step volume balance",
                "no compressibility",
                "no density change",
                "no time integration beyond one step",
            ],
        )


def _volume_record(
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
        "m^3",
        f"{prefix}_lower_bound",
        f"{prefix}_upper_bound",
        f"{prefix}_initial_guess",
        f"{prefix}_scale",
        0.0,
        1e6,
        initial_default,
        1.0,
    )


def _volume_flow_record(
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
        "m^3/s",
        f"{prefix}_lower_bound",
        f"{prefix}_upper_bound",
        f"{prefix}_initial_guess",
        f"{prefix}_scale",
        -100.0,
        100.0,
        initial_default,
        1.0,
    )
