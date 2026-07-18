"""Shared helpers for component-level audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.physical._common import (
    finite_float,
    metadata,
    nonnegative_float,
    owned_record,
    positive_float,
    required,
    required_nonnegative,
    required_positive,
    value,
)

RESIDUAL_ROLES = {"equation", "soft_check", "post_check"}


def role(value: Any) -> str:
    if value is None:
        return "equation"
    if value not in RESIDUAL_ROLES:
        raise ValueError("role_override must be 'equation', 'soft_check', or 'post_check'")
    return str(value)


def finite_list(parameters: dict[str, Any], name: str) -> list[float]:
    value_obj = parameters.get(name)
    if not isinstance(value_obj, list):
        raise ValueError(f"{name} must be a list")
    return [finite_float(item, name) for item in value_obj]


def strictly_increasing_axis(parameters: dict[str, Any], name: str) -> list[float]:
    axis = finite_list(parameters, name)
    if len(axis) < 2:
        raise ValueError(f"{name} must contain at least two points")
    if any(right <= left for left, right in zip(axis, axis[1:])):
        raise ValueError(f"{name} must be strictly increasing")
    return axis


def finite_grid(parameters: dict[str, Any], name: str, rows: int, cols: int) -> list[list[float]]:
    value_obj = parameters.get(name)
    if not isinstance(value_obj, list) or len(value_obj) != rows:
        raise ValueError(f"{name} must have shape len(y_points) x len(x_points)")
    grid: list[list[float]] = []
    for row in value_obj:
        if not isinstance(row, list) or len(row) != cols:
            raise ValueError(f"{name} must have shape len(y_points) x len(x_points)")
        grid.append([finite_float(item, name) for item in row])
    return grid


def one_d_interp(
    x: float,
    x_points: list[float],
    y_points: list[float],
    extrapolation: str,
    component_id: str,
) -> float:
    if len(x_points) != len(y_points):
        raise ValueError("map axes and values length mismatch")
    if x_points[0] <= x <= x_points[-1]:
        return float(np.interp(x, x_points, y_points))
    if extrapolation == "error":
        raise ValueError(f"{component_id}: map input is outside table range")
    if extrapolation == "hold":
        return y_points[0] if x < x_points[0] else y_points[-1]
    raise ValueError("extrapolation must be 'error' or 'hold'")


def bilinear_interp(
    x: float,
    y: float,
    x_points: list[float],
    y_points: list[float],
    z_values: list[list[float]],
    extrapolation: str,
    component_id: str,
) -> float:
    if extrapolation not in {"error", "hold"}:
        raise ValueError("extrapolation must be 'error' or 'hold'")
    if x < x_points[0] or x > x_points[-1] or y < y_points[0] or y > y_points[-1]:
        if extrapolation == "error":
            raise ValueError(f"{component_id}: lookup input is outside table range")
        x = min(max(x, x_points[0]), x_points[-1])
        y = min(max(y, y_points[0]), y_points[-1])

    x_index = int(np.searchsorted(x_points, x, side="right") - 1)
    y_index = int(np.searchsorted(y_points, y, side="right") - 1)
    x_index = min(max(x_index, 0), len(x_points) - 2)
    y_index = min(max(y_index, 0), len(y_points) - 2)

    x0, x1 = x_points[x_index], x_points[x_index + 1]
    y0, y1 = y_points[y_index], y_points[y_index + 1]
    z00 = z_values[y_index][x_index]
    z10 = z_values[y_index][x_index + 1]
    z01 = z_values[y_index + 1][x_index]
    z11 = z_values[y_index + 1][x_index + 1]

    tx = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
    ty = 0.0 if y1 == y0 else (y - y0) / (y1 - y0)
    return float(
        (1.0 - tx) * (1.0 - ty) * z00
        + tx * (1.0 - ty) * z10
        + (1.0 - tx) * ty * z01
        + tx * ty * z11
    )


def xy_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str) -> VariableRecord:
    return owned_record(
        component_id,
        parameters,
        local_name,
        None,
        f"{prefix}_lower_bound",
        f"{prefix}_upper_bound",
        f"{prefix}_initial_guess",
        f"{prefix}_scale",
        -1e9,
        1e9,
        0.0,
        1.0,
    )


def bounded_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    unit: str | None,
    prefix: str,
    lower: float,
    upper: float,
    initial: float,
    scale: float,
) -> VariableRecord:
    return owned_record(
        component_id,
        parameters,
        local_name,
        unit,
        f"{prefix}_lower_bound",
        f"{prefix}_upper_bound",
        f"{prefix}_initial_guess",
        f"{prefix}_scale",
        lower,
        upper,
        initial,
        scale,
    )


def efficiency_record(component_id: str, parameters: dict[str, Any]) -> VariableRecord:
    return bounded_record(
        component_id,
        parameters,
        "efficiency",
        None,
        "efficiency",
        1e-9,
        1.5,
        0.8,
        0.1,
    )


def voltage_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "V", prefix, -1e5, 1e5, initial, 100.0)


def current_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "A", prefix, -1e5, 1e5, initial, 100.0)


def positive_current_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "A", prefix, 0.0, 1e5, initial, 100.0)


def power_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "W", prefix, -1e9, 1e9, initial, 1000.0)


def positive_power_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "W", prefix, 0.0, 1e9, initial, 1000.0)


def torque_record(component_id: str, parameters: dict[str, Any], local_name: str = "torque_Nm", prefix: str = "torque") -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "N*m", prefix, -1e7, 1e7, 100.0, 100.0)


def omega_record(component_id: str, parameters: dict[str, Any], local_name: str = "omega_rad_s", prefix: str = "omega") -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "rad/s", prefix, -1e5, 1e5, 100.0, 100.0)


def pressure_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "Pa", prefix, 1e3, 1e8, initial, 1e5)


def temperature_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "K", prefix, 100.0, 1500.0, initial, 100.0)


def mass_flow_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "kg/s", prefix, 0.0, 1e4, initial, 1.0)


def molar_flow_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "mol/s", prefix, 0.0, 1e6, initial, 1e-3)


def component_metadata(module: BaseModule, domain: str, validity: list[str]) -> dict[str, Any]:
    data = metadata(module, domain, validity)
    data["purpose"] = "component_level_low_fidelity_audit"
    data.setdefault("assumptions", list(validity))
    data.setdefault("limitations", list(validity))
    data.setdefault("si_units", True)
    data.setdefault("residual_equations", [])
    data.setdefault("validity_range", list(validity))
    data.setdefault("diagnostic_keys", [])
    return data


def finite_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def finite_string_list(parameters: dict[str, Any], name: str) -> list[str]:
    values = parameters.get(name)
    if not isinstance(values, list) or not values:
        raise ValueError(f"{name} must be a non-empty list")
    return [finite_string(item, name) for item in values]


def same_length(values: list[Any], expected: int, name: str) -> None:
    if len(values) != expected:
        raise ValueError(f"{name} length must match expected length {expected}")


def fraction_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    prefix: str,
    initial: float = 0.5,
) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, None, prefix, 0.0, 1.0, initial, 0.1)


def scalar_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    prefix: str,
    initial: float = 0.0,
    scale: float = 1.0,
    unit: str | None = None,
) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, unit, prefix, -1e9, 1e9, initial, scale)


def positive_scalar_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    prefix: str,
    initial: float = 1.0,
    scale: float = 1.0,
    unit: str | None = None,
) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, unit, prefix, 0.0, 1e9, initial, scale)


def mass_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "kg", prefix, 0.0, 1e9, initial, 1.0)


def volume_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "m^3", prefix, 0.0, 1e9, initial, 1.0)


def density_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "kg/m^3", prefix, 1e-9, 1e6, initial, 100.0)


def force_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "N", prefix, -1e9, 1e9, initial, 100.0)


def speed_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "m/s", prefix, -1e4, 1e4, initial, 1.0)


def residual_record(
    module: BaseModule,
    name: str,
    residual_value: float,
    scale: float,
    diagnostic_key: str,
    description: str,
    role_value: str = "equation",
) -> ResidualRecord:
    return ResidualRecord(
        name=f"{module.component_id}.{name}",
        value=float(residual_value),
        scale=scale,
        source=module.component_id,
        role=role_value,
        diagnostic_key=diagnostic_key,
        description=description,
    )


def validate_efficiency(value_obj: Any, name: str) -> float:
    parsed = positive_float(value_obj, name)
    if parsed > 1.0:
        raise ValueError(f"{name} must be <= 1")
    return parsed


def validate_fraction_value(value_obj: Any, name: str, *, allow_zero: bool = True) -> float:
    parsed = finite_float(value_obj, name)
    lower_ok = parsed >= 0.0 if allow_zero else parsed > 0.0
    if not lower_ok or parsed > 1.0:
        bound = "0 <= value <= 1" if allow_zero else "0 < value <= 1"
        raise ValueError(f"{name} must satisfy {bound}")
    return parsed


def check_denominator(value_obj: float, min_abs: float, name: str) -> None:
    if abs(value_obj) < min_abs:
        raise ValueError(f"{name} magnitude must be at least {min_abs}")


__all__ = [
    "bilinear_interp",
    "bounded_record",
    "check_denominator",
    "component_metadata",
    "current_record",
    "efficiency_record",
    "finite_float",
    "finite_grid",
    "finite_list",
    "finite_string",
    "finite_string_list",
    "force_record",
    "fraction_record",
    "mass_flow_record",
    "mass_record",
    "molar_flow_record",
    "nonnegative_float",
    "omega_record",
    "one_d_interp",
    "positive_scalar_record",
    "positive_current_record",
    "positive_float",
    "positive_power_record",
    "power_record",
    "pressure_record",
    "required",
    "required_nonnegative",
    "required_positive",
    "role",
    "residual_record",
    "same_length",
    "scalar_record",
    "speed_record",
    "strictly_increasing_axis",
    "temperature_record",
    "torque_record",
    "validate_efficiency",
    "validate_fraction_value",
    "value",
    "volume_record",
    "voltage_record",
    "xy_record",
]
