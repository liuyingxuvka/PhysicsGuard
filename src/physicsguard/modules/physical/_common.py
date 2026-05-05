"""Shared helpers for low-fidelity physical audit modules."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.modules.base import BaseModule


def finite_float(value: Any, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def positive_float(value: Any, name: str) -> float:
    parsed = finite_float(value, name)
    if parsed <= 0:
        raise ValueError(f"{name} must be positive")
    return parsed


def nonnegative_float(value: Any, name: str) -> float:
    parsed = finite_float(value, name)
    if parsed < 0:
        raise ValueError(f"{name} must be nonnegative")
    return parsed


def required(parameters: dict[str, Any], name: str) -> Any:
    if name not in parameters:
        raise ValueError(f"{name} is required")
    return parameters[name]


def required_positive(parameters: dict[str, Any], name: str) -> float:
    return positive_float(required(parameters, name), name)


def required_nonnegative(parameters: dict[str, Any], name: str) -> float:
    return nonnegative_float(required(parameters, name), name)


def owned_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    unit: str | None,
    lower_key: str,
    upper_key: str,
    initial_key: str,
    scale_key: str,
    lower_default: float,
    upper_default: float,
    initial_default: float,
    scale_default: float,
) -> VariableRecord:
    return VariableRecord(
        name=f"{component_id}.{local_name}",
        unit=unit,
        lower_bound=finite_float(parameters.get(lower_key, lower_default), lower_key),
        upper_bound=finite_float(parameters.get(upper_key, upper_default), upper_key),
        initial_guess=finite_float(parameters.get(initial_key, initial_default), initial_key),
        scale=positive_float(parameters.get(scale_key, scale_default), scale_key),
        source_component=component_id,
        local_name=local_name,
    )


def value(
    x: np.ndarray,
    registry: VariableRegistry,
    component_id: str,
    local_name: str,
) -> float:
    return float(x[registry.get_index(f"{component_id}.{local_name}")])


def metadata(module: BaseModule, domain: str, validity: list[str]) -> dict[str, Any]:
    return {
        "component_id": module.component_id,
        "module_type": module.module_type,
        "purpose": "low_fidelity_physical_audit",
        "domain": domain,
        "validity": validity,
    }
