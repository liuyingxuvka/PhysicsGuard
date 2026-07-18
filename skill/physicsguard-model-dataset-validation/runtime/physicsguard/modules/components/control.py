"""Component-level low-fidelity control audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.components._common import (
    bounded_record,
    component_metadata,
    finite_float,
    positive_float,
    required,
    required_positive,
    value,
)


class PIDControllerStepModule(BaseModule):
    """Single-step PID controller consistency check with optional saturation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "PIDControllerStepModule", parameters)
        self.Kp = finite_float(parameters.get("Kp", 0.0), "Kp")
        self.Ki = finite_float(parameters.get("Ki", 0.0), "Ki")
        self.Kd = finite_float(parameters.get("Kd", 0.0), "Kd")
        self.bias = finite_float(parameters.get("bias", 0.0), "bias")
        self.dt_s = required_positive(parameters, "dt_s")
        self.output_lower = _optional_float(parameters.get("output_lower"), "output_lower")
        self.output_upper = _optional_float(parameters.get("output_upper"), "output_upper")
        if self.output_lower is not None and self.output_upper is not None and self.output_lower >= self.output_upper:
            raise ValueError("output_lower must be less than output_upper")
        self.residual_scale_error = positive_float(
            parameters.get("residual_scale_error", 1.0),
            "residual_scale_error",
        )
        self.residual_scale_integral = positive_float(
            parameters.get("residual_scale_integral", 1.0),
            "residual_scale_integral",
        )
        self.residual_scale_derivative = positive_float(
            parameters.get("residual_scale_derivative", 1.0),
            "residual_scale_derivative",
        )
        self.residual_scale_output = positive_float(
            parameters.get("residual_scale_output", 1.0),
            "residual_scale_output",
        )
        self.records = [
            _signal_record(component_id, parameters, "setpoint", "setpoint"),
            _signal_record(component_id, parameters, "measurement", "measurement"),
            _signal_record(component_id, parameters, "error", "error"),
            _signal_record(component_id, parameters, "error_previous", "error_previous"),
            _signal_record(component_id, parameters, "integral_previous", "integral_previous"),
            _signal_record(component_id, parameters, "integral_current", "integral_current"),
            _signal_record(component_id, parameters, "derivative_error", "derivative_error"),
            _signal_record(component_id, parameters, "output_unsaturated", "output_unsaturated"),
            _signal_record(component_id, parameters, "output", "output"),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        setpoint = value(x, registry, self.component_id, "setpoint")
        measurement = value(x, registry, self.component_id, "measurement")
        error = value(x, registry, self.component_id, "error")
        error_previous = value(x, registry, self.component_id, "error_previous")
        integral_previous = value(x, registry, self.component_id, "integral_previous")
        integral_current = value(x, registry, self.component_id, "integral_current")
        derivative_error = value(x, registry, self.component_id, "derivative_error")
        output_unsat = value(x, registry, self.component_id, "output_unsaturated")
        output = value(x, registry, self.component_id, "output")
        expected_output = (
            self.Kp * error
            + self.Ki * integral_current
            + self.Kd * derivative_error
            + self.bias
        )
        saturated = expected_output
        if self.output_lower is not None:
            saturated = max(saturated, self.output_lower)
        if self.output_upper is not None:
            saturated = min(saturated, self.output_upper)
        return [
            ResidualRecord(
                name=f"{self.component_id}.pid_error",
                value=error - (setpoint - measurement),
                scale=self.residual_scale_error,
                source=self.component_id,
                role="equation",
                diagnostic_key="pid_error_mismatch",
                description="PID step error residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.pid_integral_step",
                value=integral_current - (integral_previous + error * self.dt_s),
                scale=self.residual_scale_integral,
                source=self.component_id,
                role="equation",
                diagnostic_key="pid_integral_step_mismatch",
                description="PID single-step integral residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.pid_derivative",
                value=derivative_error - ((error - error_previous) / self.dt_s),
                scale=self.residual_scale_derivative,
                source=self.component_id,
                role="equation",
                diagnostic_key="pid_derivative_mismatch",
                description="PID single-step derivative residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.pid_unsaturated_output",
                value=output_unsat - expected_output,
                scale=self.residual_scale_output,
                source=self.component_id,
                role="equation",
                diagnostic_key="pid_unsaturated_output_mismatch",
                description="PID unsaturated output residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.pid_saturated_output",
                value=output - saturated,
                scale=self.residual_scale_output,
                source=self.component_id,
                role="equation",
                diagnostic_key="pid_saturated_output_mismatch",
                description="PID saturated output residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "control",
            [
                "single-step audit only",
                "no advanced anti-windup",
                "no derivative filtering",
                "no time-series memory beyond supplied previous values",
                "saturation is algebraic",
            ],
        )


class ActuatorFirstOrderSaturationModule(BaseModule):
    """Single-step command-to-actual first-order actuator check with saturation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ActuatorFirstOrderSaturationModule", parameters)
        self.tau_s = required_positive(parameters, "tau_s")
        self.dt_s = required_positive(parameters, "dt_s")
        self.lower = finite_float(required(parameters, "lower"), "lower")
        self.upper = finite_float(required(parameters, "upper"), "upper")
        if self.lower >= self.upper:
            raise ValueError("lower must be less than upper")
        self.residual_scale = positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = [
            _signal_record(component_id, parameters, "command", "command"),
            _signal_record(component_id, parameters, "actual_previous", "actual_previous"),
            _signal_record(component_id, parameters, "actual_current", "actual_current"),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        command = value(x, registry, self.component_id, "command")
        previous = value(x, registry, self.component_id, "actual_previous")
        current = value(x, registry, self.component_id, "actual_current")
        target = min(max(command, self.lower), self.upper)
        expected = previous + (self.dt_s / self.tau_s) * (target - previous)
        return [
            ResidualRecord(
                name=f"{self.component_id}.actuator_first_order_saturation",
                value=current - expected,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="actuator_first_order_saturation_mismatch",
                description="Actuator first-order saturation residual.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "control",
            [
                "single-step first-order actuator check",
                "no detailed actuator physics",
                "no rate-dependent nonlinearities",
            ],
        )


def _optional_float(value_obj: Any, name: str) -> float | None:
    if value_obj is None:
        return None
    return finite_float(value_obj, name)


def _signal_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    prefix: str,
) -> VariableRecord:
    return bounded_record(
        component_id,
        parameters,
        local_name,
        None,
        prefix,
        -1e9,
        1e9,
        0.0,
        1.0,
    )
