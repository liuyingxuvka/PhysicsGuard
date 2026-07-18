"""Low-fidelity control, map, and single-step signal audit modules."""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.schema.variable import is_qualified_variable_name


EQUATION_OR_CHECK_ROLES = {"equation", "soft_check", "post_check"}


class ControlErrorModule(BaseModule):
    """Basic control error relation error = setpoint - measurement."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ControlErrorModule", parameters)
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = [
            _owned_record(component_id, parameters, "setpoint", None, "setpoint", 0.0),
            _owned_record(component_id, parameters, "measurement", None, "measurement", 0.0),
            _owned_record(component_id, parameters, "error", None, "error", 0.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        setpoint = _owned_value(x, registry, self.component_id, "setpoint")
        measurement = _owned_value(x, registry, self.component_id, "measurement")
        error = _owned_value(x, registry, self.component_id, "error")
        return [
            ResidualRecord(
                name=f"{self.component_id}.control_error",
                value=error - (setpoint - measurement),
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="control_error_mismatch",
                description="Control error residual error - (setpoint - measurement).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            ["algebraic control error only", "no controller dynamics"],
        )


class PIDAlgebraicModule(BaseModule):
    """Single-step algebraic PID output consistency check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "PIDAlgebraicModule", parameters)
        self.Kp = _finite_float(parameters.get("Kp", 0.0), "Kp")
        self.Ki = _finite_float(parameters.get("Ki", 0.0), "Ki")
        self.Kd = _finite_float(parameters.get("Kd", 0.0), "Kd")
        self.bias = _finite_float(parameters.get("bias", 0.0), "bias")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = [
            _owned_record(component_id, parameters, "error", None, "error", 0.0),
            _owned_record(component_id, parameters, "integral_error", None, "integral_error", 0.0),
            _owned_record(
                component_id,
                parameters,
                "derivative_error",
                None,
                "derivative_error",
                0.0,
            ),
            _owned_record(component_id, parameters, "output", None, "output", 0.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        error = _owned_value(x, registry, self.component_id, "error")
        integral_error = _owned_value(x, registry, self.component_id, "integral_error")
        derivative_error = _owned_value(x, registry, self.component_id, "derivative_error")
        output = _owned_value(x, registry, self.component_id, "output")
        expected = self.Kp * error + self.Ki * integral_error + self.Kd * derivative_error + self.bias
        return [
            ResidualRecord(
                name=f"{self.component_id}.pid_algebraic",
                value=output - expected,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="pid_algebraic_mismatch",
                description="Algebraic PID residual output - (Kp*error + Ki*integral + Kd*derivative + bias).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            [
                "algebraic PID consistency only",
                "no anti-windup",
                "no derivative filtering",
                "no saturation",
                "no time integration unless paired with another module",
            ],
        )


class DiscreteIntegratorModule(BaseModule):
    """Single-step explicit integrator consistency check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "DiscreteIntegratorModule", parameters)
        self.dt_s = _required_positive(parameters, "dt_s")
        self.gain = _finite_float(parameters.get("gain", 1.0), "gain")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = [
            _owned_record(component_id, parameters, "state_previous", None, "state_previous", 0.0),
            _owned_record(component_id, parameters, "input", None, "input", 0.0),
            _owned_record(component_id, parameters, "state_current", None, "state_current", 0.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        previous = _owned_value(x, registry, self.component_id, "state_previous")
        input_value = _owned_value(x, registry, self.component_id, "input")
        current = _owned_value(x, registry, self.component_id, "state_current")
        expected = previous + self.gain * input_value * self.dt_s
        return [
            ResidualRecord(
                name=f"{self.component_id}.discrete_integrator",
                value=current - expected,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="discrete_integrator_mismatch",
                description="Single-step integrator residual state_current - (state_previous + gain*input*dt).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            [
                "single-step explicit integrator check",
                "no full time-series simulation",
                "assumes previous state is known",
            ],
        )


class HysteresisStateCheckModule(BaseModule):
    """Post-check for hysteresis state consistency."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "HysteresisStateCheckModule", parameters)
        self.low_threshold = _finite_float(_required(parameters, "low_threshold"), "low_threshold")
        self.high_threshold = _finite_float(_required(parameters, "high_threshold"), "high_threshold")
        if self.low_threshold >= self.high_threshold:
            raise ValueError("low_threshold must be less than high_threshold")
        self.state_on_value = _finite_float(parameters.get("state_on_value", 1.0), "state_on_value")
        self.state_off_value = _finite_float(parameters.get("state_off_value", 0.0), "state_off_value")
        self.state_tolerance = _positive_float(parameters.get("state_tolerance", 0.25), "state_tolerance")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = [
            _owned_record(component_id, parameters, "input", None, "input", 0.0),
            _owned_record(component_id, parameters, "state", None, "state", 0.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        input_value = _owned_value(x, registry, self.component_id, "input")
        state = _owned_value(x, registry, self.component_id, "state")
        on_distance = abs(state - self.state_on_value)
        off_distance = abs(state - self.state_off_value)
        residual = 0.0
        if on_distance <= self.state_tolerance and input_value < self.low_threshold:
            residual = self.low_threshold - input_value
        elif off_distance <= self.state_tolerance and input_value > self.high_threshold:
            residual = input_value - self.high_threshold
        elif min(on_distance, off_distance) > self.state_tolerance:
            residual = min(on_distance, off_distance)
        return [
            ResidualRecord(
                name=f"{self.component_id}.hysteresis_state_check",
                value=residual,
                scale=self.residual_scale,
                source=self.component_id,
                role="post_check",
                diagnostic_key="hysteresis_state_violation",
                description="Hysteresis state post-check residual.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            [
                "consistency check only",
                "no state memory",
                "no automatic switching logic",
                "does not infer previous state",
                "post_check residual does not pull solver solution",
            ],
        )


class BooleanSwitchModule(BaseModule):
    """Algebraic switch relation output = condition*true + (1-condition)*false."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "BooleanSwitchModule", parameters)
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = [
            _custom_owned_record(
                component_id,
                parameters,
                "condition",
                None,
                "condition",
                0.0,
                1.0,
                1.0,
                1.0,
            ),
            _owned_record(component_id, parameters, "true_value", None, "true_value", 1.0),
            _owned_record(component_id, parameters, "false_value", None, "false_value", 0.0),
            _owned_record(component_id, parameters, "output", None, "output", 1.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        condition = _owned_value(x, registry, self.component_id, "condition")
        true_value = _owned_value(x, registry, self.component_id, "true_value")
        false_value = _owned_value(x, registry, self.component_id, "false_value")
        output = _owned_value(x, registry, self.component_id, "output")
        expected = condition * true_value + (1.0 - condition) * false_value
        return [
            ResidualRecord(
                name=f"{self.component_id}.boolean_switch",
                value=output - expected,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="boolean_switch_mismatch",
                description="Algebraic switch residual output - (condition*true + (1-condition)*false).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            [
                "algebraic switch check",
                "condition should normally be 0 or 1",
                "does not enforce integer logic unless paired with a post_check",
            ],
        )


class ThresholdStateCheckModule(BaseModule):
    """Post-check for a threshold-derived state."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ThresholdStateCheckModule", parameters)
        self.threshold = _finite_float(_required(parameters, "threshold"), "threshold")
        self.on_value = _finite_float(parameters.get("on_value", 1.0), "on_value")
        self.off_value = _finite_float(parameters.get("off_value", 0.0), "off_value")
        self.state_tolerance = _positive_float(parameters.get("state_tolerance", 0.25), "state_tolerance")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = [
            _owned_record(component_id, parameters, "input", None, "input", 0.0),
            _owned_record(component_id, parameters, "state", None, "state", 0.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        input_value = _owned_value(x, registry, self.component_id, "input")
        state = _owned_value(x, registry, self.component_id, "state")
        expected = self.on_value if input_value >= self.threshold else self.off_value
        return [
            ResidualRecord(
                name=f"{self.component_id}.threshold_state_check",
                value=state - expected,
                scale=self.residual_scale,
                source=self.component_id,
                role="post_check",
                diagnostic_key="threshold_state_violation",
                description="Threshold state post-check residual state - expected_state.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            [
                "diagnostic check only",
                "no hysteresis",
                "no temporal memory",
                "post_check residual does not pull solver solution",
            ],
        )


class SaturationModule(BaseModule):
    """Saturation consistency relation y = min(max(u, lower), upper)."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "SaturationModule", parameters)
        if "lower" not in parameters or "upper" not in parameters:
            raise ValueError("lower and upper are required")
        self.lower = _finite_float(parameters["lower"], "lower")
        self.upper = _finite_float(parameters["upper"], "upper")
        if self.lower >= self.upper:
            raise ValueError("lower must be less than upper")
        self.role = _role(parameters.get("role_override", "equation"))
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = _xy_records(component_id, parameters, "u", "y", "u", "y")

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        u_value = _owned_value(x, registry, self.component_id, "u")
        y_value = _owned_value(x, registry, self.component_id, "y")
        saturated = min(max(u_value, self.lower), self.upper)
        return [
            ResidualRecord(
                name=f"{self.component_id}.saturation",
                value=y_value - saturated,
                scale=self.residual_scale,
                source=self.component_id,
                role=self.role,
                diagnostic_key="saturation_mismatch",
                description="Saturation residual y - min(max(u, lower), upper).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            [
                "algebraic saturation consistency check",
                "no actuator dynamics",
                "role may be equation, soft_check, or post_check",
            ],
        )


class RateLimiterModule(BaseModule):
    """Single-step rate-limit consistency check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "RateLimiterModule", parameters)
        self.dt_s = _required_positive(parameters, "dt_s")
        self.rising_rate_limit = _finite_float(
            _required(parameters, "rising_rate_limit"),
            "rising_rate_limit",
        )
        if self.rising_rate_limit < 0:
            raise ValueError("rising_rate_limit must be >= 0")
        self.falling_rate_limit = _finite_float(
            _required(parameters, "falling_rate_limit"),
            "falling_rate_limit",
        )
        if self.falling_rate_limit > 0:
            raise ValueError("falling_rate_limit must be <= 0")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = _xy_records(
            component_id,
            parameters,
            "y_previous",
            "y_current",
            "y_previous",
            "y_current",
        )

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        previous = _owned_value(x, registry, self.component_id, "y_previous")
        current = _owned_value(x, registry, self.component_id, "y_current")
        rate = (current - previous) / self.dt_s
        residual = 0.0
        if rate > self.rising_rate_limit:
            residual = rate - self.rising_rate_limit
        elif rate < self.falling_rate_limit:
            residual = rate - self.falling_rate_limit
        return [
            ResidualRecord(
                name=f"{self.component_id}.rate_limiter",
                value=residual,
                scale=self.residual_scale,
                source=self.component_id,
                role="post_check",
                diagnostic_key="rate_limit_violation",
                description="Single-step rate-limit post-check residual.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            [
                "single-step consistency check",
                "no time-series evaluation",
                "no controller state beyond previous/current values",
                "post_check residual does not pull solver solution",
            ],
        )


class FirstOrderLagModule(BaseModule):
    """Single-step first-order lag audit relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "FirstOrderLagModule", parameters)
        self.tau_s = _required_positive(parameters, "tau_s")
        self.dt_s = _required_positive(parameters, "dt_s")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = [
            _owned_record(component_id, parameters, "u_current", None, "u_current", 0.0),
            _owned_record(component_id, parameters, "y_previous", None, "y_previous", 0.0),
            _owned_record(component_id, parameters, "y_current", None, "y_current", 0.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        u_current = _owned_value(x, registry, self.component_id, "u_current")
        y_previous = _owned_value(x, registry, self.component_id, "y_previous")
        y_current = _owned_value(x, registry, self.component_id, "y_current")
        residual = ((y_current - y_previous) / self.dt_s) - (
            (u_current - y_current) / self.tau_s
        )
        return [
            ResidualRecord(
                name=f"{self.component_id}.first_order_lag",
                value=residual,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="first_order_lag_mismatch",
                description="Single-step first-order lag residual.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            [
                "single-step audit",
                "no full dynamic simulation",
                "assumes known previous state",
            ],
        )


class LookupTable1DModule(BaseModule):
    """Low-fidelity 1D lookup-table consistency check."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "LookupTable1DModule", parameters)
        self.x_points = _finite_float_list(parameters, "x_points")
        self.y_points = _finite_float_list(parameters, "y_points")
        if len(self.x_points) != len(self.y_points):
            raise ValueError("x_points and y_points must have the same length")
        if len(self.x_points) < 2:
            raise ValueError("x_points and y_points must contain at least two points")
        if any(right <= left for left, right in zip(self.x_points, self.x_points[1:])):
            raise ValueError("x_points must be strictly increasing")
        self.extrapolation = parameters.get("extrapolation", "error")
        if self.extrapolation not in {"error", "hold", "linear"}:
            raise ValueError("extrapolation must be 'error', 'hold', or 'linear'")
        self.role = _role(parameters.get("role_override", "equation"))
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = _xy_records(component_id, parameters, "x", "y", "x", "y")

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        x_value = _owned_value(x, registry, self.component_id, "x")
        y_value = _owned_value(x, registry, self.component_id, "y")
        expected = self._interpolate(x_value)
        return [
            ResidualRecord(
                name=f"{self.component_id}.lookup_table_1d",
                value=y_value - expected,
                scale=self.residual_scale,
                source=self.component_id,
                role=self.role,
                diagnostic_key="lookup_table_1d_mismatch",
                description="Low-fidelity 1D lookup table residual y - table(x).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        metadata = _metadata(
            self,
            [
                "piecewise linear lookup consistency check",
                "no smoothing",
                "no multidimensional interpolation",
            ],
        )
        metadata["extrapolation"] = self.extrapolation
        return metadata

    def _interpolate(self, value: float) -> float:
        x_values = self.x_points
        y_values = self.y_points
        if x_values[0] <= value <= x_values[-1]:
            return float(np.interp(value, x_values, y_values))
        if self.extrapolation == "error":
            raise ValueError(f"{self.component_id}: lookup x is outside table range")
        if self.extrapolation == "hold":
            return y_values[0] if value < x_values[0] else y_values[-1]
        if value < x_values[0]:
            x0, x1 = x_values[0], x_values[1]
            y0, y1 = y_values[0], y_values[1]
        else:
            x0, x1 = x_values[-2], x_values[-1]
            y0, y1 = y_values[-2], y_values[-1]
        slope = (y1 - y0) / (x1 - x0)
        return y0 + slope * (value - x0)


class MapBoundsCheckModule(BaseModule):
    """Post-check that a variable lies within a map axis range."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "MapBoundsCheckModule", parameters)
        self.variable = _required_variable_name(parameters, "variable")
        self.lower = _finite_float(_required(parameters, "lower"), "lower")
        self.upper = _finite_float(_required(parameters, "upper"), "upper")
        if self.lower >= self.upper:
            raise ValueError("lower must be less than upper")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        try:
            value = float(x[registry.get_index(self.variable)])
        except KeyError as exc:
            raise KeyError(
                f"{self.component_id}: MapBoundsCheckModule references unknown variable: {exc}"
            ) from exc
        residual = 0.0
        if value > self.upper:
            residual = value - self.upper
        elif value < self.lower:
            residual = value - self.lower
        return [
            ResidualRecord(
                name=f"{self.component_id}.map_bounds_check",
                value=residual,
                scale=self.residual_scale,
                source=self.component_id,
                role="post_check",
                diagnostic_key="map_bounds_violation",
                description="Map-axis bounds post-check residual.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            [
                "map-axis range check",
                "post_check residual does not pull solver solution",
                "no map interpolation",
            ],
        )


def _finite_float(value: Any, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def _finite_float_list(parameters: dict[str, Any], name: str) -> list[float]:
    value = parameters.get(name)
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return [_finite_float(item, name) for item in value]


def _positive_float(value: Any, name: str) -> float:
    parsed = _finite_float(value, name)
    if parsed <= 0:
        raise ValueError(f"{name} must be positive")
    return parsed


def _required(parameters: dict[str, Any], name: str) -> Any:
    if name not in parameters:
        raise ValueError(f"{name} is required")
    return parameters[name]


def _required_positive(parameters: dict[str, Any], name: str) -> float:
    return _positive_float(_required(parameters, name), name)


def _role(value: Any) -> str:
    if value not in EQUATION_OR_CHECK_ROLES:
        raise ValueError("role_override must be 'equation', 'soft_check', or 'post_check'")
    return str(value)


def _owned_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    unit: Optional[str],
    prefix: str,
    initial_default: float,
) -> VariableRecord:
    return VariableRecord(
        name=f"{component_id}.{local_name}",
        unit=unit,
        lower_bound=_finite_float(parameters.get(f"{prefix}_lower_bound", -1e9), f"{prefix}_lower_bound"),
        upper_bound=_finite_float(parameters.get(f"{prefix}_upper_bound", 1e9), f"{prefix}_upper_bound"),
        initial_guess=_finite_float(
            parameters.get(f"{prefix}_initial_guess", initial_default),
            f"{prefix}_initial_guess",
        ),
        scale=_positive_float(parameters.get(f"{prefix}_scale", 1.0), f"{prefix}_scale"),
        source_component=component_id,
        local_name=local_name,
    )


def _custom_owned_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    unit: Optional[str],
    prefix: str,
    lower_default: float,
    upper_default: float,
    initial_default: float,
    scale_default: float,
) -> VariableRecord:
    return VariableRecord(
        name=f"{component_id}.{local_name}",
        unit=unit,
        lower_bound=_finite_float(parameters.get(f"{prefix}_lower_bound", lower_default), f"{prefix}_lower_bound"),
        upper_bound=_finite_float(parameters.get(f"{prefix}_upper_bound", upper_default), f"{prefix}_upper_bound"),
        initial_guess=_finite_float(
            parameters.get(f"{prefix}_initial_guess", initial_default),
            f"{prefix}_initial_guess",
        ),
        scale=_positive_float(parameters.get(f"{prefix}_scale", scale_default), f"{prefix}_scale"),
        source_component=component_id,
        local_name=local_name,
    )


def _xy_records(
    component_id: str,
    parameters: dict[str, Any],
    x_name: str,
    y_name: str,
    x_prefix: str,
    y_prefix: str,
) -> list[VariableRecord]:
    return [
        _owned_record(component_id, parameters, x_name, None, x_prefix, 0.0),
        _owned_record(component_id, parameters, y_name, None, y_prefix, 0.0),
    ]


def _owned_value(
    x: np.ndarray,
    registry: VariableRegistry,
    component_id: str,
    local_name: str,
) -> float:
    return float(x[registry.get_index(f"{component_id}.{local_name}")])


def _required_variable_name(parameters: dict[str, Any], name: str) -> str:
    value = parameters.get(name)
    if not isinstance(value, str) or not is_qualified_variable_name(value):
        raise ValueError(f"{name} must use component.variable format")
    return value


def _metadata(module: BaseModule, validity: list[str]) -> dict[str, Any]:
    return {
        "component_id": module.component_id,
        "module_type": module.module_type,
        "purpose": "low_fidelity_control_audit",
        "domain": "control",
        "validity": validity,
    }
