"""Low-fidelity electrical audit modules."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule


class OhmicRelationModule(BaseModule):
    """Low-fidelity electrical ohmic relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "OhmicRelationModule", parameters)
        self.resistance_ohm = _required_nonnegative(parameters, "resistance_ohm")
        self.residual_scale_V = _positive_float(
            parameters.get("residual_scale_V", 1.0),
            "residual_scale_V",
        )
        self.records = [
            _owned_record(
                component_id,
                parameters,
                "current_A",
                "A",
                "current_lower_bound",
                "current_upper_bound",
                "current_initial_guess",
                "current_scale",
                -5000.0,
                5000.0,
                100.0,
                100.0,
            ),
            _owned_record(
                component_id,
                parameters,
                "V_drop_V",
                "V",
                "V_lower_bound",
                "V_upper_bound",
                "V_initial_guess",
                "V_scale",
                -10000.0,
                10000.0,
                1.0,
                1.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        current = _value(x, registry, self.component_id, "current_A")
        voltage_drop = _value(x, registry, self.component_id, "V_drop_V")
        return [
            ResidualRecord(
                name=f"{self.component_id}.ohmic_relation",
                value=voltage_drop - current * self.resistance_ohm,
                scale=self.residual_scale_V,
                source=self.component_id,
                role="equation",
                diagnostic_key="ohmic_relation_mismatch",
                description="Low-fidelity ohmic residual V_drop - current*resistance.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            [
                "constant resistance",
                "no temperature dependence",
                "no dynamic electrical effects",
            ],
        )


class ElectricalPowerModule(BaseModule):
    """Low-fidelity electrical power relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ElectricalPowerModule", parameters)
        self.residual_scale_W = _positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            _owned_record(
                component_id,
                parameters,
                "V_V",
                "V",
                "V_lower_bound",
                "V_upper_bound",
                "V_initial_guess",
                "V_scale",
                -10000.0,
                10000.0,
                100.0,
                100.0,
            ),
            _owned_record(
                component_id,
                parameters,
                "current_A",
                "A",
                "current_lower_bound",
                "current_upper_bound",
                "current_initial_guess",
                "current_scale",
                -5000.0,
                5000.0,
                10.0,
                10.0,
            ),
            _owned_record(
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
                1000.0,
                1000.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        voltage = _value(x, registry, self.component_id, "V_V")
        current = _value(x, registry, self.component_id, "current_A")
        power = _value(x, registry, self.component_id, "P_W")
        return [
            ResidualRecord(
                name=f"{self.component_id}.electrical_power",
                value=power - voltage * current,
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="electrical_power_mismatch",
                description="Low-fidelity electrical power residual P - V*current.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            [
                "algebraic DC power relation",
                "no AC phase effects",
                "no power electronics dynamics",
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


def _positive_float(value: Any, name: str) -> float:
    parsed = _finite_float(value, name)
    if parsed <= 0:
        raise ValueError(f"{name} must be positive")
    return parsed


def _nonnegative_float(value: Any, name: str) -> float:
    parsed = _finite_float(value, name)
    if parsed < 0:
        raise ValueError(f"{name} must be nonnegative")
    return parsed


def _required_nonnegative(parameters: dict[str, Any], name: str) -> float:
    if name not in parameters:
        raise ValueError(f"{name} is required")
    return _nonnegative_float(parameters[name], name)


def _owned_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    unit: str,
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
        lower_bound=_finite_float(parameters.get(lower_key, lower_default), lower_key),
        upper_bound=_finite_float(parameters.get(upper_key, upper_default), upper_key),
        initial_guess=_finite_float(parameters.get(initial_key, initial_default), initial_key),
        scale=_positive_float(parameters.get(scale_key, scale_default), scale_key),
        source_component=component_id,
        local_name=local_name,
    )


def _value(
    x: np.ndarray,
    registry: VariableRegistry,
    component_id: str,
    local_name: str,
) -> float:
    return float(x[registry.get_index(f"{component_id}.{local_name}")])


def _metadata(module: BaseModule, validity: list[str]) -> dict[str, Any]:
    return {
        "component_id": module.component_id,
        "module_type": module.module_type,
        "purpose": "low_fidelity_physical_audit",
        "domain": "electrical",
        "validity": validity,
    }
