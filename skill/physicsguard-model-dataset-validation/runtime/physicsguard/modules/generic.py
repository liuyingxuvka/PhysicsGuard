"""Generic non-physical modules for validating the residual framework."""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.schema.variable import is_qualified_variable_name


class LinearRelationModule(BaseModule):
    """Generic framework validation module enforcing y = a*x + b."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "LinearRelationModule", parameters)
        self.a = _finite_float(parameters.get("a", 1.0), "a")
        self.b = _finite_float(parameters.get("b", 0.0), "b")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.x_unit: Optional[str] = parameters.get("x_unit")
        self.y_unit: Optional[str] = parameters.get("y_unit")
        self.x_record = self._variable_record("x", self.x_unit)
        self.y_record = self._variable_record("y", self.y_unit)

    def declare_variables(self) -> list[VariableRecord]:
        return [self.x_record, self.y_record]

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        x_value = float(x[registry.get_index(self.x_record.name)])
        y_value = float(x[registry.get_index(self.y_record.name)])
        return [
            ResidualRecord(
                name=f"{self.component_id}.linear_relation",
                value=y_value - (self.a * x_value + self.b),
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="linear_relation_mismatch",
                description="Generic non-physical residual enforcing y = a*x + b.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "module_type": self.module_type,
            "purpose": "framework_validation_only",
            "has_physical_meaning": False,
        }

    def _variable_record(self, local_name: str, unit: Optional[str]) -> VariableRecord:
        return VariableRecord(
            name=f"{self.component_id}.{local_name}",
            unit=unit,
            lower_bound=_finite_float(
                _required_parameter(self.parameters, f"{local_name}_lower_bound"),
                f"{local_name}_lower_bound",
            ),
            upper_bound=_finite_float(
                _required_parameter(self.parameters, f"{local_name}_upper_bound"),
                f"{local_name}_upper_bound",
            ),
            initial_guess=_finite_float(
                _required_parameter(self.parameters, f"{local_name}_initial_guess"),
                f"{local_name}_initial_guess",
            ),
            scale=_positive_float(
                _required_parameter(self.parameters, f"{local_name}_scale"),
                f"{local_name}_scale",
            ),
            source_component=self.component_id,
            local_name=local_name,
        )


class ConservationSumModule(BaseModule):
    """Generic residual enforcing sum(inputs) - sum(outputs) = target."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ConservationSumModule", parameters)
        self.input_variables = _qualified_variable_list(parameters, "input_variables")
        self.output_variables = _qualified_variable_list(parameters, "output_variables")
        if not self.input_variables and not self.output_variables:
            raise ValueError(
                f"{component_id}: ConservationSumModule requires at least one referenced variable"
            )
        self.target = _finite_float(parameters.get("target", 0.0), "target")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        try:
            input_sum = sum(float(x[registry.get_index(name)]) for name in self.input_variables)
            output_sum = sum(float(x[registry.get_index(name)]) for name in self.output_variables)
        except KeyError as exc:
            raise KeyError(
                f"{self.component_id}: ConservationSumModule references unknown variable: {exc}"
            ) from exc
        return [
            ResidualRecord(
                name=f"{self.component_id}.conservation_sum",
                value=input_sum - output_sum - self.target,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="conservation_sum_mismatch",
                description=(
                    "Generic non-physical residual enforcing "
                    "sum(inputs) - sum(outputs) = target."
                ),
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "module_type": self.module_type,
            "purpose": "framework_validation_only",
            "has_physical_meaning": False,
        }


class RangeCheckModule(BaseModule):
    """Generic soft range residual for an existing variable."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "RangeCheckModule", parameters)
        variable = parameters.get("variable")
        if not isinstance(variable, str) or not is_qualified_variable_name(variable):
            raise ValueError(
                f"{component_id}: RangeCheckModule variable must use component.variable format"
            )
        self.variable = variable
        self.lower_bound = _optional_finite_float(parameters.get("lower_bound"), "lower_bound")
        self.upper_bound = _optional_finite_float(parameters.get("upper_bound"), "upper_bound")
        if self.lower_bound is None and self.upper_bound is None:
            raise ValueError(
                f"{component_id}: RangeCheckModule requires lower_bound or upper_bound"
            )
        if (
            self.lower_bound is not None
            and self.upper_bound is not None
            and self.lower_bound > self.upper_bound
        ):
            raise ValueError(f"{component_id}: lower_bound must be <= upper_bound")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.role = parameters.get("role", "post_check")
        if self.role not in {"post_check", "soft_check"}:
            raise ValueError(
                f"{component_id}: RangeCheckModule role must be 'post_check' or 'soft_check'"
            )
        include_in_solver = parameters.get("include_in_solver", False)
        if not isinstance(include_in_solver, bool):
            raise ValueError(f"{component_id}: include_in_solver must be a boolean")
        if self.role == "post_check" and include_in_solver:
            raise ValueError(f"{component_id}: post_check residuals cannot enter the solver")
        self.include_in_solver = include_in_solver

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        try:
            value = float(x[registry.get_index(self.variable)])
        except KeyError as exc:
            raise KeyError(
                f"{self.component_id}: RangeCheckModule references unknown variable: {exc}"
            ) from exc
        residual = 0.0
        if self.lower_bound is not None and value < self.lower_bound:
            residual = value - self.lower_bound
        elif self.upper_bound is not None and value > self.upper_bound:
            residual = value - self.upper_bound
        return [
            ResidualRecord(
                name=f"{self.component_id}.range_check",
                value=residual,
                scale=self.residual_scale,
                source=self.component_id,
                role=self.role,
                active_in_solver=self.include_in_solver if self.role == "soft_check" else False,
                diagnostic_key="range_check_violation",
                description="Generic non-physical soft range residual.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "module_type": self.module_type,
            "purpose": "framework_validation_only",
            "has_physical_meaning": False,
        }


def _finite_float(value: Any, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def _required_parameter(parameters: dict[str, Any], name: str) -> Any:
    if name not in parameters:
        raise ValueError(f"{name} is required")
    return parameters[name]


def _optional_finite_float(value: Any, name: str) -> Optional[float]:
    if value is None:
        return None
    return _finite_float(value, name)


def _positive_float(value: Any, name: str) -> float:
    parsed = _finite_float(value, name)
    if parsed <= 0:
        raise ValueError(f"{name} must be positive")
    return parsed


def _qualified_variable_list(parameters: dict[str, Any], name: str) -> list[str]:
    value = parameters.get(name, [])
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    variables: list[str] = []
    for item in value:
        if not isinstance(item, str) or not is_qualified_variable_name(item):
            raise ValueError(f"{name} entries must use component.variable format")
        variables.append(item)
    return variables
