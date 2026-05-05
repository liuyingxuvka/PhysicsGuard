"""Generic signal algebra audit modules."""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.schema.variable import is_qualified_variable_name


class GainBiasModule(BaseModule):
    """Generic signal scale and offset relation y = gain*x + bias."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "GainBiasModule", parameters)
        self.gain = _finite_float(parameters.get("gain", 1.0), "gain")
        self.bias = _finite_float(parameters.get("bias", 0.0), "bias")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = _xy_records(component_id, parameters, "x", "y")

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        x_value = _owned_value(x, registry, self.component_id, "x")
        y_value = _owned_value(x, registry, self.component_id, "y")
        return [
            ResidualRecord(
                name=f"{self.component_id}.gain_bias",
                value=y_value - (self.gain * x_value + self.bias),
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="gain_bias_mismatch",
                description="Generic signal residual y - (gain*x + bias).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            "signal",
            ["algebraic scale/offset check", "no dynamics", "no unit conversion unless encoded in parameters"],
        )


class SumModule(BaseModule):
    """Weighted sum relation over existing variables."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "SumModule", parameters)
        self.input_variables = _required_variable_list(parameters, "input_variables")
        if not self.input_variables:
            raise ValueError(f"{component_id}: input_variables cannot be empty")
        weights = parameters.get("weights")
        if weights is None:
            self.weights = [1.0] * len(self.input_variables)
        else:
            if not isinstance(weights, list):
                raise ValueError("weights must be a list")
            if len(weights) != len(self.input_variables):
                raise ValueError("weights length must match input_variables")
            self.weights = [_finite_float(weight, "weights") for weight in weights]
        self.output_variable = _required_variable_name(parameters, "output_variable")
        self.bias = _finite_float(parameters.get("bias", 0.0), "bias")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        try:
            weighted_sum = sum(
                weight * float(x[registry.get_index(name)])
                for name, weight in zip(self.input_variables, self.weights, strict=True)
            )
            output = float(x[registry.get_index(self.output_variable)])
        except KeyError as exc:
            raise KeyError(f"{self.component_id}: SumModule references unknown variable: {exc}") from exc
        return [
            ResidualRecord(
                name=f"{self.component_id}.sum_relation",
                value=output - weighted_sum - self.bias,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="sum_relation_mismatch",
                description="Generic weighted sum residual output - sum(weights*x) - bias.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(self, "signal", ["algebraic weighted sum", "no dynamics"])


class ProductModule(BaseModule):
    """Simple product relation over existing variables."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ProductModule", parameters)
        self.x1_variable = _required_variable_name(parameters, "x1_variable")
        self.x2_variable = _required_variable_name(parameters, "x2_variable")
        self.output_variable = _required_variable_name(parameters, "output_variable")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        try:
            x1 = float(x[registry.get_index(self.x1_variable)])
            x2 = float(x[registry.get_index(self.x2_variable)])
            output = float(x[registry.get_index(self.output_variable)])
        except KeyError as exc:
            raise KeyError(f"{self.component_id}: ProductModule references unknown variable: {exc}") from exc
        return [
            ResidualRecord(
                name=f"{self.component_id}.product_relation",
                value=output - x1 * x2,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="product_relation_mismatch",
                description="Generic product residual output - x1*x2.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(self, "signal", ["algebraic product", "no dynamics"])


class RatioModule(BaseModule):
    """Simple ratio relation over existing variables."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "RatioModule", parameters)
        self.numerator_variable = _required_variable_name(parameters, "numerator_variable")
        self.denominator_variable = _required_variable_name(parameters, "denominator_variable")
        self.output_variable = _required_variable_name(parameters, "output_variable")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.denominator_min_abs = _positive_float(
            parameters.get("denominator_min_abs", 1e-12),
            "denominator_min_abs",
        )

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        try:
            numerator = float(x[registry.get_index(self.numerator_variable)])
            denominator = float(x[registry.get_index(self.denominator_variable)])
            output = float(x[registry.get_index(self.output_variable)])
        except KeyError as exc:
            raise KeyError(f"{self.component_id}: RatioModule references unknown variable: {exc}") from exc
        if abs(denominator) < self.denominator_min_abs:
            raise ValueError(
                f"{self.component_id}: denominator magnitude is below denominator_min_abs"
            )
        return [
            ResidualRecord(
                name=f"{self.component_id}.ratio_relation",
                value=output - numerator / denominator,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="ratio_relation_mismatch",
                description="Generic ratio residual output - numerator/denominator.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(self, "signal", ["algebraic ratio", "denominator near zero is invalid"])


class UnitScaleModule(BaseModule):
    """Explicit unit-scale audit relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "UnitScaleModule", parameters)
        if "factor" not in parameters:
            raise ValueError("factor is required")
        self.factor = _finite_float(parameters["factor"], "factor")
        self.offset = _finite_float(parameters.get("offset", 0.0), "offset")
        self.source_unit: Optional[str] = parameters.get("source_unit")
        self.target_unit: Optional[str] = parameters.get("target_unit")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = _xy_records(component_id, parameters, "x", "y")

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        x_value = _owned_value(x, registry, self.component_id, "x")
        y_value = _owned_value(x, registry, self.component_id, "y")
        return [
            ResidualRecord(
                name=f"{self.component_id}.unit_scale",
                value=y_value - (self.factor * x_value + self.offset),
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="unit_scale_mismatch",
                description="Explicit unit-scale residual y - (factor*x + offset).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        metadata = _metadata(
            self,
            "signal",
            ["explicit scale/offset check", "no automatic unit conversion"],
        )
        metadata["source_unit"] = self.source_unit
        metadata["target_unit"] = self.target_unit
        return metadata


class SensorScaleOffsetModule(BaseModule):
    """Sensor measurement scale and offset relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "SensorScaleOffsetModule", parameters)
        self.scale_factor = _finite_float(parameters.get("scale_factor", 1.0), "scale_factor")
        self.offset = _finite_float(parameters.get("offset", 0.0), "offset")
        self.residual_scale = _positive_float(
            parameters.get("residual_scale", 1.0),
            "residual_scale",
        )
        self.records = _xy_records(
            component_id,
            parameters,
            "true_value",
            "measured_value",
            "true",
            "measured",
        )

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        true_value = _owned_value(x, registry, self.component_id, "true_value")
        measured = _owned_value(x, registry, self.component_id, "measured_value")
        return [
            ResidualRecord(
                name=f"{self.component_id}.sensor_scale_offset",
                value=measured - (self.scale_factor * true_value + self.offset),
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="sensor_scale_offset_mismatch",
                description="Sensor scale/offset residual measured - (scale_factor*true + offset).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            "signal",
            ["algebraic sensor calibration check", "no sensor dynamics", "no noise model"],
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


def _owned_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    unit: Optional[str],
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


def _xy_records(
    component_id: str,
    parameters: dict[str, Any],
    x_name: str,
    y_name: str,
    x_prefix: str = "x",
    y_prefix: str = "y",
) -> list[VariableRecord]:
    return [
        _owned_record(
            component_id,
            parameters,
            x_name,
            None,
            f"{x_prefix}_lower_bound",
            f"{x_prefix}_upper_bound",
            f"{x_prefix}_initial_guess",
            f"{x_prefix}_scale",
            -1e9,
            1e9,
            0.0,
            1.0,
        ),
        _owned_record(
            component_id,
            parameters,
            y_name,
            None,
            f"{y_prefix}_lower_bound",
            f"{y_prefix}_upper_bound",
            f"{y_prefix}_initial_guess",
            f"{y_prefix}_scale",
            -1e9,
            1e9,
            0.0,
            1.0,
        ),
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


def _required_variable_list(parameters: dict[str, Any], name: str) -> list[str]:
    if name not in parameters:
        raise ValueError(f"{name} is required")
    value = parameters[name]
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    variables: list[str] = []
    for item in value:
        if not isinstance(item, str) or not is_qualified_variable_name(item):
            raise ValueError(f"{name} entries must use component.variable format")
        variables.append(item)
    return variables


def _metadata(module: BaseModule, domain: str, validity: list[str]) -> dict[str, Any]:
    return {
        "component_id": module.component_id,
        "module_type": module.module_type,
        "purpose": "low_fidelity_signal_audit",
        "domain": domain,
        "validity": validity,
    }
