"""Declarative module metadata schemas."""

from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_finite, ensure_non_empty


class PortSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    variables: list[str]
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "port name")

    @field_validator("variables")
    @classmethod
    def _variables_not_empty_names(cls, value: list[str]) -> list[str]:
        for variable in value:
            ensure_non_empty(variable, "port variable")
        return value


class ParameterSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    unit: Optional[str] = None
    required: bool = True
    default: Optional[float | str | bool] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "parameter name")

    @model_validator(mode="after")
    def _validate_bounds(self) -> "ParameterSpec":
        if self.lower_bound is not None:
            ensure_finite(self.lower_bound, "parameter lower_bound")
        if self.upper_bound is not None:
            ensure_finite(self.upper_bound, "parameter upper_bound")
        if (
            self.lower_bound is not None
            and self.upper_bound is not None
            and self.lower_bound >= self.upper_bound
        ):
            raise ValueError("parameter lower_bound must be less than upper_bound")
        return self


class VariableSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    unit: Optional[str] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    initial_guess: Optional[float] = None
    scale: Optional[float] = None
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "variable name")

    @model_validator(mode="after")
    def _validate_variable(self) -> "VariableSpec":
        if self.lower_bound is not None:
            ensure_finite(self.lower_bound, "variable lower_bound")
        if self.upper_bound is not None:
            ensure_finite(self.upper_bound, "variable upper_bound")
        if self.initial_guess is not None:
            ensure_finite(self.initial_guess, "variable initial_guess")
        if (
            self.lower_bound is not None
            and self.upper_bound is not None
            and self.lower_bound >= self.upper_bound
        ):
            raise ValueError("variable lower_bound must be less than upper_bound")
        if self.scale is not None:
            ensure_finite(self.scale, "variable scale")
            if self.scale <= 0:
                raise ValueError("variable scale must be positive")
        has_inferable_scale = self.lower_bound is not None and self.upper_bound is not None
        if self.scale is None and not has_inferable_scale:
            raise ValueError(
                "variable must provide a positive scale or both lower_bound and upper_bound"
            )
        return self


class ResidualSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: Optional[str] = None
    scale: Optional[float] = None
    diagnostic_key: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "residual name")

    @field_validator("scale")
    @classmethod
    def _scale_positive(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return value
        if not math.isfinite(value) or value <= 0:
            raise ValueError("residual scale must be finite and positive")
        return value


class DiagnosticHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    likely_causes: list[str] = Field(default_factory=list)
    suggested_checks: list[str] = Field(default_factory=list)
    severity: Optional[str] = None


class ModuleSpec(BaseModel):
    """Metadata-only declaration of a component type."""

    model_config = ConfigDict(extra="forbid")

    module_type: str
    domain: str
    description: Optional[str] = None
    ports: dict[str, PortSpec]
    parameters: dict[str, ParameterSpec]
    variables: dict[str, VariableSpec]
    residuals: list[ResidualSpec]
    validity: list[str] = Field(default_factory=list)
    diagnostics: dict[str, DiagnosticHint] = Field(default_factory=dict)

    @field_validator("module_type")
    @classmethod
    def _module_type_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "module_type")

    @field_validator("domain")
    @classmethod
    def _domain_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "domain")

    @model_validator(mode="after")
    def _validate_references(self) -> "ModuleSpec":
        known_variables = set(self.variables)
        for port_name, port in self.ports.items():
            ensure_non_empty(port_name, "port key")
            for variable in port.variables:
                if variable not in known_variables:
                    raise ValueError(
                        f"port '{port_name}' references unknown variable '{variable}'"
                    )
        for variable_key, variable in self.variables.items():
            ensure_non_empty(variable_key, "variable key")
            if variable.name != variable_key:
                raise ValueError(
                    f"variable key '{variable_key}' must match variable name '{variable.name}'"
                )
        for parameter_key, parameter in self.parameters.items():
            ensure_non_empty(parameter_key, "parameter key")
            if parameter.name != parameter_key:
                raise ValueError(
                    f"parameter key '{parameter_key}' must match parameter name '{parameter.name}'"
                )
        for residual in self.residuals:
            ensure_non_empty(residual.name, "residual name")
        return self
