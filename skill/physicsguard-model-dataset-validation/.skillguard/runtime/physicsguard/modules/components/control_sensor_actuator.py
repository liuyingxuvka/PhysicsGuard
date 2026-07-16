"""Component-level control, calibration, sensor, and actuator audit modules."""

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
    finite_list,
    finite_string_list,
    one_d_interp,
    positive_float,
    residual_record,
    role,
    same_length,
    scalar_record,
    strictly_increasing_axis,
    value,
    xy_record,
)


class GainScheduledPIDModule(BaseModule):
    """Low-fidelity gain-scheduled algebraic PID audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "GainScheduledPIDModule", parameters)
        self.schedule_points = strictly_increasing_axis(parameters, "schedule_points")
        self.kp_points = finite_list(parameters, "Kp_points")
        self.ki_points = finite_list(parameters, "Ki_points")
        self.kd_points = finite_list(parameters, "Kd_points")
        same_length(self.kp_points, len(self.schedule_points), "Kp_points")
        same_length(self.ki_points, len(self.schedule_points), "Ki_points")
        same_length(self.kd_points, len(self.schedule_points), "Kd_points")
        self.bias = finite_float(parameters.get("bias", 0.0), "bias")
        self.extrapolation = parameters.get("extrapolation", "error")
        if self.extrapolation not in {"error", "hold"}:
            raise ValueError("extrapolation must be 'error' or 'hold'")
        self.error_scale = positive_float(parameters.get("residual_scale_error", 1.0), "residual_scale_error")
        self.output_scale = positive_float(parameters.get("residual_scale_output", 1.0), "residual_scale_output")
        self.records = [
            xy_record(component_id, parameters, "schedule_variable", "schedule_variable"),
            xy_record(component_id, parameters, "setpoint", "setpoint"),
            xy_record(component_id, parameters, "measurement", "measurement"),
            xy_record(component_id, parameters, "error", "error"),
            xy_record(component_id, parameters, "integral_error", "integral_error"),
            xy_record(component_id, parameters, "derivative_error", "derivative_error"),
            xy_record(component_id, parameters, "output", "output"),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        sched = value(x, registry, self.component_id, "schedule_variable")
        setpoint = value(x, registry, self.component_id, "setpoint")
        measurement = value(x, registry, self.component_id, "measurement")
        err = value(x, registry, self.component_id, "error")
        integral = value(x, registry, self.component_id, "integral_error")
        derivative = value(x, registry, self.component_id, "derivative_error")
        output = value(x, registry, self.component_id, "output")
        kp = one_d_interp(sched, self.schedule_points, self.kp_points, self.extrapolation, self.component_id)
        ki = one_d_interp(sched, self.schedule_points, self.ki_points, self.extrapolation, self.component_id)
        kd = one_d_interp(sched, self.schedule_points, self.kd_points, self.extrapolation, self.component_id)
        return [
            residual_record(self, "gain_scheduled_pid_error", err - (setpoint - measurement), self.error_scale, "gain_scheduled_pid_error_mismatch", "Gain-scheduled PID error residual."),
            residual_record(self, "gain_scheduled_pid_output", output - (kp * err + ki * integral + kd * derivative + self.bias), self.output_scale, "gain_scheduled_pid_output_mismatch", "Gain-scheduled PID output residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        metadata = component_metadata(self, "control_sensor_actuator", ["algebraic gain-scheduled PID check", "no integrator state update", "no anti-windup", "no derivative filtering", "no saturation unless paired separately"])
        metadata["extrapolation"] = self.extrapolation
        return metadata


class AntiWindupClampModule(BaseModule):
    """Post-check for integrator clamp and output saturation consistency."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "AntiWindupClampModule", parameters)
        self.integral_lower = finite_float(parameters.get("integral_lower"), "integral_lower")
        self.integral_upper = finite_float(parameters.get("integral_upper"), "integral_upper")
        self.output_lower = finite_float(parameters.get("output_lower"), "output_lower")
        self.output_upper = finite_float(parameters.get("output_upper"), "output_upper")
        if self.integral_lower >= self.integral_upper:
            raise ValueError("integral_lower must be less than integral_upper")
        if self.output_lower >= self.output_upper:
            raise ValueError("output_lower must be less than output_upper")
        self.scale = positive_float(parameters.get("residual_scale", 1.0), "residual_scale")
        self.records = [
            xy_record(component_id, parameters, "integral_state", "integral_state"),
            xy_record(component_id, parameters, "output_unsaturated", "output_unsaturated"),
            xy_record(component_id, parameters, "output_saturated", "output_saturated"),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        integral = value(x, registry, self.component_id, "integral_state")
        saturated = value(x, registry, self.component_id, "output_saturated")
        integral_res = integral - self.integral_upper if integral > self.integral_upper else integral - self.integral_lower if integral < self.integral_lower else 0.0
        output_res = saturated - self.output_upper if saturated > self.output_upper else saturated - self.output_lower if saturated < self.output_lower else 0.0
        return [
            residual_record(self, "anti_windup_integral_clamp", integral_res, self.scale, "anti_windup_integral_clamp_violation", "Anti-windup integral clamp post-check.", "post_check"),
            residual_record(self, "anti_windup_output_saturation", output_res, self.scale, "anti_windup_output_saturation_violation", "Anti-windup output saturation post-check.", "post_check"),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "control_sensor_actuator", ["diagnostic only", "no controller state correction", "no anti-windup back-calculation"])


class MapAxisBoundsCheckModule(BaseModule):
    """Post-check multiple map-axis ranges."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "MapAxisBoundsCheckModule", parameters)
        self.variables = finite_string_list(parameters, "variables")
        self.lower_bounds = finite_list(parameters, "lower_bounds")
        self.upper_bounds = finite_list(parameters, "upper_bounds")
        same_length(self.lower_bounds, len(self.variables), "lower_bounds")
        same_length(self.upper_bounds, len(self.variables), "upper_bounds")
        for lower, upper in zip(self.lower_bounds, self.upper_bounds):
            if lower >= upper:
                raise ValueError("each lower bound must be less than upper bound")
        self.scale = positive_float(parameters.get("residual_scale", 1.0), "residual_scale")

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        records: list[ResidualRecord] = []
        for variable, lower, upper in zip(self.variables, self.lower_bounds, self.upper_bounds):
            observed = float(x[registry.get_index(variable)])
            residual = observed - upper if observed > upper else observed - lower if observed < lower else 0.0
            records.append(residual_record(self, f"map_axis_bounds:{variable}", residual, self.scale, "map_axis_bounds_violation", "Map axis bounds post-check.", "post_check"))
        return records

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "control_sensor_actuator", ["diagnostic envelope only", "no interpolation"])


class MapMonotonicityCheckModule(BaseModule):
    """Static post-check residual for monotonic map data."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "MapMonotonicityCheckModule", parameters)
        self.values = finite_list(parameters, "values")
        self.expected = parameters.get("expected")
        if self.expected not in {"increasing", "decreasing", "nondecreasing", "nonincreasing"}:
            raise ValueError("expected must be increasing, decreasing, nondecreasing, or nonincreasing")
        self.scale = positive_float(parameters.get("residual_scale", 1.0), "residual_scale")

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        violation = 0.0
        for left, right in zip(self.values, self.values[1:]):
            if self.expected == "increasing":
                violation += max(left - right, 0.0) + (1.0 if right == left else 0.0)
            elif self.expected == "decreasing":
                violation += max(right - left, 0.0) + (1.0 if right == left else 0.0)
            elif self.expected == "nondecreasing":
                violation += max(left - right, 0.0)
            else:
                violation += max(right - left, 0.0)
        return [residual_record(self, "map_monotonicity", violation, self.scale, "map_monotonicity_violation", "Map monotonicity post-check.", "post_check")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "control_sensor_actuator", ["calibration/map sanity check only", "no physical interpretation by itself"])


class SensorLowPassFilterStepModule(BaseModule):
    """Single-step sensor low-pass filter audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "SensorLowPassFilterStepModule", parameters)
        self.tau = positive_float(parameters.get("tau_s"), "tau_s")
        self.dt = positive_float(parameters.get("dt_s"), "dt_s")
        self.scale = positive_float(parameters.get("residual_scale", 1.0), "residual_scale")
        self.records = [
            xy_record(component_id, parameters, "true_value_current", "true_value_current"),
            xy_record(component_id, parameters, "measured_previous", "measured_previous"),
            xy_record(component_id, parameters, "measured_current", "measured_current"),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        true_val = value(x, registry, self.component_id, "true_value_current")
        prev = value(x, registry, self.component_id, "measured_previous")
        cur = value(x, registry, self.component_id, "measured_current")
        expected = prev + (self.dt / self.tau) * (true_val - prev)
        return [residual_record(self, "sensor_low_pass_filter_step", cur - expected, self.scale, "sensor_low_pass_filter_step_mismatch", "Sensor low-pass filter step residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "control_sensor_actuator", ["single-step filter check", "no noise model", "no sensor fault model"])


class ActuatorDeadZoneModule(BaseModule):
    """Static actuator dead-zone relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ActuatorDeadZoneModule", parameters)
        self.dead_zone = finite_float(parameters.get("dead_zone"), "dead_zone")
        if self.dead_zone < 0:
            raise ValueError("dead_zone must be nonnegative")
        self.gain = finite_float(parameters.get("gain", 1.0), "gain")
        self.scale = positive_float(parameters.get("residual_scale", 1.0), "residual_scale")
        self.role = role(parameters.get("role_override"))
        self.records = [
            xy_record(component_id, parameters, "command", "command"),
            xy_record(component_id, parameters, "output", "output"),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        command = value(x, registry, self.component_id, "command")
        output = value(x, registry, self.component_id, "output")
        if abs(command) <= self.dead_zone:
            expected = 0.0
        else:
            sign = 1.0 if command > 0 else -1.0
            expected = self.gain * (command - sign * self.dead_zone)
        return [residual_record(self, "actuator_dead_zone", output - expected, self.scale, "actuator_dead_zone_mismatch", "Actuator dead-zone residual.", self.role)]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "control_sensor_actuator", ["static dead-zone check", "no actuator dynamics"])


class ActuatorPositionFeedbackModule(BaseModule):
    """Actuator command, position, and feedback consistency audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ActuatorPositionFeedbackModule", parameters)
        self.command_gain = finite_float(parameters.get("command_to_position_gain", 1.0), "command_to_position_gain")
        self.feedback_gain = finite_float(parameters.get("feedback_gain", 1.0), "feedback_gain")
        self.feedback_offset = finite_float(parameters.get("feedback_offset", 0.0), "feedback_offset")
        self.position_scale = positive_float(parameters.get("residual_scale_position", 0.01), "residual_scale_position")
        self.feedback_scale = positive_float(parameters.get("residual_scale_feedback", 0.01), "residual_scale_feedback")
        self.records = [
            xy_record(component_id, parameters, "command", "command"),
            xy_record(component_id, parameters, "actual_position", "actual_position"),
            xy_record(component_id, parameters, "feedback_position", "feedback_position"),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        command = value(x, registry, self.component_id, "command")
        actual = value(x, registry, self.component_id, "actual_position")
        feedback = value(x, registry, self.component_id, "feedback_position")
        return [
            residual_record(self, "actuator_command_position", actual - self.command_gain * command, self.position_scale, "actuator_command_position_mismatch", "Actuator command-to-position residual."),
            residual_record(self, "actuator_feedback_position", feedback - (self.feedback_gain * actual + self.feedback_offset), self.feedback_scale, "actuator_feedback_position_mismatch", "Actuator feedback-position residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "control_sensor_actuator", ["algebraic actuator consistency", "no dynamics", "no force/torque model", "no saturation unless paired separately"])


class SignalDelayStepModule(BaseModule):
    """Single-step signal delay audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "SignalDelayStepModule", parameters)
        self.scale = positive_float(parameters.get("residual_scale", 1.0), "residual_scale")
        self.records = [
            xy_record(component_id, parameters, "input_previous", "input_previous"),
            xy_record(component_id, parameters, "output_current", "output_current"),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        inp = value(x, registry, self.component_id, "input_previous")
        out = value(x, registry, self.component_id, "output_current")
        return [residual_record(self, "signal_delay_step", out - inp, self.scale, "signal_delay_step_mismatch", "Signal one-step delay residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "control_sensor_actuator", ["one-step delay check", "no time-series buffer", "no variable sample time"])


class SampleAndHoldModule(BaseModule):
    """Single-step sample-and-hold audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "SampleAndHoldModule", parameters)
        self.scale = positive_float(parameters.get("residual_scale", 1.0), "residual_scale")
        self.role = role(parameters.get("role_override"))
        self.records = [
            xy_record(component_id, parameters, "input_current", "input_current"),
            xy_record(component_id, parameters, "output_previous", "output_previous"),
            xy_record(component_id, parameters, "output_current", "output_current"),
            bounded_record(component_id, parameters, "hold_flag", None, "hold_flag", 0.0, 1.0, 0.0, 1.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        inp = value(x, registry, self.component_id, "input_current")
        prev = value(x, registry, self.component_id, "output_previous")
        cur = value(x, registry, self.component_id, "output_current")
        hold = value(x, registry, self.component_id, "hold_flag")
        expected = prev if hold >= 0.5 else inp
        return [residual_record(self, "sample_and_hold", cur - expected, self.scale, "sample_and_hold_mismatch", "Sample-and-hold single-step residual.", self.role)]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "control_sensor_actuator", ["single-step check", "hold_flag treated as numeric boolean", "no full time-series sampling logic"])


class UnitConversionAuditModule(BaseModule):
    """Explicit semantic unit-conversion audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "UnitConversionAuditModule", parameters)
        self.factor = finite_float(parameters.get("factor"), "factor")
        self.offset = finite_float(parameters.get("offset", 0.0), "offset")
        self.source_unit = parameters.get("source_unit")
        self.target_unit = parameters.get("target_unit")
        self.scale = positive_float(parameters.get("residual_scale", 1.0), "residual_scale")
        self.records = [
            xy_record(component_id, parameters, "source_value", "source_value"),
            xy_record(component_id, parameters, "target_value", "target_value"),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        source = value(x, registry, self.component_id, "source_value")
        target = value(x, registry, self.component_id, "target_value")
        return [residual_record(self, "unit_conversion_audit", target - (self.factor * source + self.offset), self.scale, "unit_conversion_audit_mismatch", "Explicit unit-conversion audit residual.")]

    def metadata(self) -> dict[str, Any]:
        data = component_metadata(self, "control_sensor_actuator", ["explicit user-provided conversion only", "no automatic unit system", "no hidden conversion table"])
        data["source_unit"] = self.source_unit
        data["target_unit"] = self.target_unit
        return data
