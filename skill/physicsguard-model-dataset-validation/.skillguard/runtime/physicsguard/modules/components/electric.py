"""Component-level low-fidelity electric drive audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.components._common import (
    bilinear_interp,
    component_metadata,
    current_record,
    efficiency_record,
    finite_grid,
    positive_float,
    power_record,
    strictly_increasing_axis,
    torque_record,
    value,
    voltage_record,
    omega_record,
)


class ElectricMotorSimpleModule(BaseModule):
    """Low-fidelity electric motor algebraic power balance."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ElectricMotorSimpleModule", parameters)
        self.residual_scale_power_W = positive_float(
            parameters.get("residual_scale_power_W", 1000.0),
            "residual_scale_power_W",
        )
        self.residual_scale_efficiency = positive_float(
            parameters.get("residual_scale_efficiency", 0.01),
            "residual_scale_efficiency",
        )
        self.records = [
            voltage_record(component_id, parameters, "voltage_V", "voltage", 400.0),
            current_record(component_id, parameters, "current_A", "current", 10.0),
            power_record(component_id, parameters, "electrical_power_W", "electrical_power", 4000.0),
            torque_record(component_id, parameters),
            omega_record(component_id, parameters),
            power_record(component_id, parameters, "mechanical_power_W", "mechanical_power", 3000.0),
            efficiency_record(component_id, parameters),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        voltage = value(x, registry, self.component_id, "voltage_V")
        current = value(x, registry, self.component_id, "current_A")
        electrical_power = value(x, registry, self.component_id, "electrical_power_W")
        torque = value(x, registry, self.component_id, "torque_Nm")
        omega = value(x, registry, self.component_id, "omega_rad_s")
        mechanical_power = value(x, registry, self.component_id, "mechanical_power_W")
        efficiency = value(x, registry, self.component_id, "efficiency")
        return [
            ResidualRecord(
                name=f"{self.component_id}.motor_electrical_power",
                value=electrical_power - voltage * current,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="motor_electrical_power_mismatch",
                description="Motor electrical power residual P_elec - V*I.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.motor_mechanical_power",
                value=mechanical_power - torque * omega,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="motor_mechanical_power_mismatch",
                description="Motor mechanical power residual P_mech - torque*omega.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.motor_efficiency_power",
                value=mechanical_power - efficiency * electrical_power,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="motor_efficiency_power_mismatch",
                description="Motor efficiency power residual P_mech - eta*P_elec.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "electric_drive",
            [
                "algebraic power balance only",
                "no torque-speed map",
                "no inverter dynamics",
                "no thermal derating",
                "no transient motor dynamics",
            ],
        )


class ElectricMotorMapModule(BaseModule):
    """Map-based motor efficiency consistency and power balance."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ElectricMotorMapModule", parameters)
        self.torque_points = strictly_increasing_axis(parameters, "torque_points")
        self.omega_points = strictly_increasing_axis(parameters, "omega_points")
        self.efficiency_values = finite_grid(
            parameters,
            "efficiency_values",
            rows=len(self.omega_points),
            cols=len(self.torque_points),
        )
        self.extrapolation = parameters.get("extrapolation", "error")
        if self.extrapolation not in {"error", "hold"}:
            raise ValueError("extrapolation must be 'error' or 'hold'")
        self.residual_scale_efficiency = positive_float(
            parameters.get("residual_scale_efficiency", 0.01),
            "residual_scale_efficiency",
        )
        self.residual_scale_power_W = positive_float(
            parameters.get("residual_scale_power_W", 1000.0),
            "residual_scale_power_W",
        )
        self.records = [
            torque_record(component_id, parameters),
            omega_record(component_id, parameters),
            efficiency_record(component_id, parameters),
            power_record(component_id, parameters, "electrical_power_W", "electrical_power", 4000.0),
            power_record(component_id, parameters, "mechanical_power_W", "mechanical_power", 3000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        torque = value(x, registry, self.component_id, "torque_Nm")
        omega = value(x, registry, self.component_id, "omega_rad_s")
        efficiency = value(x, registry, self.component_id, "efficiency")
        electrical_power = value(x, registry, self.component_id, "electrical_power_W")
        mechanical_power = value(x, registry, self.component_id, "mechanical_power_W")
        expected_efficiency = bilinear_interp(
            torque,
            omega,
            self.torque_points,
            self.omega_points,
            self.efficiency_values,
            self.extrapolation,
            self.component_id,
        )
        return [
            ResidualRecord(
                name=f"{self.component_id}.motor_efficiency_map",
                value=efficiency - expected_efficiency,
                scale=self.residual_scale_efficiency,
                source=self.component_id,
                role="equation",
                diagnostic_key="motor_efficiency_map_mismatch",
                description="Motor efficiency map residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.motor_mechanical_power",
                value=mechanical_power - torque * omega,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="motor_mechanical_power_mismatch",
                description="Motor mechanical power residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.motor_efficiency_power",
                value=mechanical_power - efficiency * electrical_power,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="motor_efficiency_power_mismatch",
                description="Motor efficiency power residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        metadata = component_metadata(
            self,
            "electric_drive",
            [
                "map consistency and power balance only",
                "no inverter model",
                "no thermal derating",
                "no torque-speed envelope unless map bounds are used",
            ],
        )
        metadata["extrapolation"] = self.extrapolation
        return metadata


class DCDCConverterSimpleModule(BaseModule):
    """Low-fidelity DC/DC converter power consistency check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "DCDCConverterSimpleModule", parameters)
        self.residual_scale_power_W = positive_float(
            parameters.get("residual_scale_power_W", 1000.0),
            "residual_scale_power_W",
        )
        self.records = [
            voltage_record(component_id, parameters, "V_in_V", "V_in", 400.0),
            current_record(component_id, parameters, "I_in_A", "I_in", 10.0),
            power_record(component_id, parameters, "P_in_W", "P_in", 4000.0),
            voltage_record(component_id, parameters, "V_out_V", "V_out", 200.0),
            current_record(component_id, parameters, "I_out_A", "I_out", 18.0),
            power_record(component_id, parameters, "P_out_W", "P_out", 3600.0),
            efficiency_record(component_id, parameters),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        v_in = value(x, registry, self.component_id, "V_in_V")
        i_in = value(x, registry, self.component_id, "I_in_A")
        p_in = value(x, registry, self.component_id, "P_in_W")
        v_out = value(x, registry, self.component_id, "V_out_V")
        i_out = value(x, registry, self.component_id, "I_out_A")
        p_out = value(x, registry, self.component_id, "P_out_W")
        efficiency = value(x, registry, self.component_id, "efficiency")
        return [
            ResidualRecord(
                name=f"{self.component_id}.dcdc_input_power",
                value=p_in - v_in * i_in,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="dcdc_input_power_mismatch",
                description="DC/DC input power residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.dcdc_output_power",
                value=p_out - v_out * i_out,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="dcdc_output_power_mismatch",
                description="DC/DC output power residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.dcdc_efficiency_power",
                value=p_out - efficiency * p_in,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="dcdc_efficiency_power_mismatch",
                description="DC/DC efficiency power residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "electric",
            [
                "algebraic DC power relation",
                "no switching model",
                "no ripple",
                "no thermal derating",
                "no control dynamics",
            ],
        )


class InverterSimpleModule(BaseModule):
    """Low-fidelity inverter power consistency check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "InverterSimpleModule", parameters)
        self.residual_scale_power_W = positive_float(
            parameters.get("residual_scale_power_W", 1000.0),
            "residual_scale_power_W",
        )
        self.records = [
            power_record(component_id, parameters, "P_dc_W", "P_dc", 4000.0),
            power_record(component_id, parameters, "P_ac_W", "P_ac", 3600.0),
            efficiency_record(component_id, parameters),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_dc = value(x, registry, self.component_id, "P_dc_W")
        p_ac = value(x, registry, self.component_id, "P_ac_W")
        efficiency = value(x, registry, self.component_id, "efficiency")
        return [
            ResidualRecord(
                name=f"{self.component_id}.inverter_efficiency_power",
                value=p_ac - efficiency * p_dc,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="inverter_efficiency_power_mismatch",
                description="Inverter efficiency power residual P_ac - eta*P_dc.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "electric",
            [
                "algebraic power check only",
                "no phase modeling",
                "no PWM",
                "no switching losses",
                "no thermal derating",
            ],
        )
