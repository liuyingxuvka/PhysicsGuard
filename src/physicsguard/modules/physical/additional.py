"""Additional simple low-fidelity physical relation modules."""

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
    value,
)


class PressureRatioModule(BaseModule):
    """Simple pressure ratio relation p_out / p_in."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "PressureRatioModule", parameters)
        self.residual_scale = positive_float(
            parameters.get("residual_scale", 0.1),
            "residual_scale",
        )
        self.denominator_min_abs = positive_float(
            parameters.get("denominator_min_abs", 1e-12),
            "denominator_min_abs",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "p_in_Pa",
                "Pa",
                "p_lower_bound",
                "p_upper_bound",
                "p_in_initial_guess",
                "p_scale",
                1e3,
                1e7,
                100000.0,
                1e5,
            ),
            owned_record(
                component_id,
                parameters,
                "p_out_Pa",
                "Pa",
                "p_lower_bound",
                "p_upper_bound",
                "p_out_initial_guess",
                "p_scale",
                1e3,
                1e7,
                200000.0,
                1e5,
            ),
            owned_record(
                component_id,
                parameters,
                "pressure_ratio",
                None,
                "pressure_ratio_lower_bound",
                "pressure_ratio_upper_bound",
                "pressure_ratio_initial_guess",
                "pressure_ratio_scale",
                0.0,
                100.0,
                2.0,
                1.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_in = value(x, registry, self.component_id, "p_in_Pa")
        if abs(p_in) < self.denominator_min_abs:
            raise ValueError(f"{self.component_id}: p_in_Pa is below denominator_min_abs")
        p_out = value(x, registry, self.component_id, "p_out_Pa")
        ratio = value(x, registry, self.component_id, "pressure_ratio")
        return [
            ResidualRecord(
                name=f"{self.component_id}.pressure_ratio",
                value=ratio - p_out / p_in,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="pressure_ratio_mismatch",
                description="Low-fidelity pressure ratio residual pressure_ratio - p_out/p_in.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(self, "fluid", ["algebraic ratio", "p_in must not be near zero"])


class EfficiencyModule(BaseModule):
    """Simple efficiency relation useful_output / input."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "EfficiencyModule", parameters)
        self.residual_scale = positive_float(
            parameters.get("residual_scale", 0.01),
            "residual_scale",
        )
        self.denominator_min_abs = positive_float(
            parameters.get("denominator_min_abs", 1e-12),
            "denominator_min_abs",
        )
        efficiency_lower = finite_float(
            parameters.get("efficiency_lower_bound", 0.0),
            "efficiency_lower_bound",
        )
        efficiency_upper = finite_float(
            parameters.get("efficiency_upper_bound", 1.5),
            "efficiency_upper_bound",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "input_power_W",
                "W",
                "input_power_lower_bound",
                "input_power_upper_bound",
                "input_power_initial_guess",
                "input_power_scale",
                0.0,
                1e8,
                1000.0,
                1000.0,
            ),
            owned_record(
                component_id,
                parameters,
                "useful_output_power_W",
                "W",
                "useful_output_power_lower_bound",
                "useful_output_power_upper_bound",
                "useful_output_power_initial_guess",
                "useful_output_power_scale",
                0.0,
                1e8,
                500.0,
                1000.0,
            ),
            owned_record(
                component_id,
                parameters,
                "efficiency",
                None,
                "efficiency_lower_bound",
                "efficiency_upper_bound",
                "efficiency_initial_guess",
                "efficiency_scale",
                efficiency_lower,
                efficiency_upper,
                0.5,
                0.1,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        input_power = value(x, registry, self.component_id, "input_power_W")
        if abs(input_power) < self.denominator_min_abs:
            raise ValueError(f"{self.component_id}: input_power_W is below denominator_min_abs")
        useful_output = value(x, registry, self.component_id, "useful_output_power_W")
        efficiency = value(x, registry, self.component_id, "efficiency")
        return [
            ResidualRecord(
                name=f"{self.component_id}.efficiency",
                value=efficiency - useful_output / input_power,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="efficiency_mismatch",
                description="Low-fidelity efficiency residual efficiency - useful_output/input.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "physical",
            [
                "algebraic sanity check",
                "not a detailed loss model",
                "efficiency greater than one may be diagnostically suspicious",
            ],
        )


class TorqueSpeedPowerModule(BaseModule):
    """Rotational mechanical power relation P = torque * omega."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "TorqueSpeedPowerModule", parameters)
        self.residual_scale_W = positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "torque_Nm",
                "N*m",
                "torque_lower_bound",
                "torque_upper_bound",
                "torque_initial_guess",
                "torque_scale",
                -1e6,
                1e6,
                100.0,
                100.0,
            ),
            owned_record(
                component_id,
                parameters,
                "omega_rad_s",
                "rad/s",
                "omega_lower_bound",
                "omega_upper_bound",
                "omega_initial_guess",
                "omega_scale",
                -1e5,
                1e5,
                100.0,
                100.0,
            ),
            owned_record(
                component_id,
                parameters,
                "P_W",
                "W",
                "P_lower_bound",
                "P_upper_bound",
                "P_initial_guess",
                "P_scale",
                -1e8,
                1e8,
                10000.0,
                1000.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        torque = value(x, registry, self.component_id, "torque_Nm")
        omega = value(x, registry, self.component_id, "omega_rad_s")
        power = value(x, registry, self.component_id, "P_W")
        return [
            ResidualRecord(
                name=f"{self.component_id}.torque_speed_power",
                value=power - torque * omega,
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="torque_speed_power_mismatch",
                description="Low-fidelity rotational power residual P - torque*omega.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(self, "mechanical", ["algebraic rotational power relation", "no drivetrain dynamics"])


class CellVoltageStackVoltageModule(BaseModule):
    """Electrochemical stack voltage relation V_stack = n_cells * V_cell."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "CellVoltageStackVoltageModule", parameters)
        self.n_cells = _required_positive(parameters, "n_cells")
        self.residual_scale_V = positive_float(
            parameters.get("residual_scale_V", 1.0),
            "residual_scale_V",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "V_cell_V",
                "V",
                "V_cell_lower_bound",
                "V_cell_upper_bound",
                "V_cell_initial_guess",
                "V_cell_scale",
                0.0,
                3.0,
                0.7,
                1.0,
            ),
            owned_record(
                component_id,
                parameters,
                "V_stack_V",
                "V",
                "V_stack_lower_bound",
                "V_stack_upper_bound",
                "V_stack_initial_guess",
                "V_stack_scale",
                0.0,
                5000.0,
                self.n_cells * 0.7,
                100.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        cell_voltage = value(x, registry, self.component_id, "V_cell_V")
        stack_voltage = value(x, registry, self.component_id, "V_stack_V")
        return [
            ResidualRecord(
                name=f"{self.component_id}.cell_stack_voltage",
                value=stack_voltage - self.n_cells * cell_voltage,
                scale=self.residual_scale_V,
                source=self.component_id,
                role="equation",
                diagnostic_key="cell_stack_voltage_mismatch",
                description="Low-fidelity stack voltage residual V_stack - n_cells*V_cell.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(self, "electrochemical", ["lumped stack voltage relation", "no cell voltage model"])


class CurrentDensityModule(BaseModule):
    """Current density relation current / active_area."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "CurrentDensityModule", parameters)
        self.active_area_m2 = _required_positive(parameters, "active_area_m2")
        self.residual_scale_A_m2 = positive_float(
            parameters.get("residual_scale_A_m2", 100.0),
            "residual_scale_A_m2",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "current_A",
                "A",
                "current_lower_bound",
                "current_upper_bound",
                "current_initial_guess",
                "current_scale",
                0.0,
                5000.0,
                100.0,
                100.0,
            ),
            owned_record(
                component_id,
                parameters,
                "current_density_A_m2",
                "A/m^2",
                "current_density_lower_bound",
                "current_density_upper_bound",
                "current_density_initial_guess",
                "current_density_scale",
                0.0,
                1e6,
                1000.0,
                100.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        current = value(x, registry, self.component_id, "current_A")
        density = value(x, registry, self.component_id, "current_density_A_m2")
        return [
            ResidualRecord(
                name=f"{self.component_id}.current_density",
                value=density - current / self.active_area_m2,
                scale=self.residual_scale_A_m2,
                source=self.component_id,
                role="equation",
                diagnostic_key="current_density_mismatch",
                description="Low-fidelity current density residual current_density - current/area.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(self, "electrochemical", ["algebraic current density relation", "constant active area"])


def _required_positive(parameters: dict[str, Any], name: str) -> float:
    if name not in parameters:
        raise ValueError(f"{name} is required")
    return positive_float(parameters[name], name)


