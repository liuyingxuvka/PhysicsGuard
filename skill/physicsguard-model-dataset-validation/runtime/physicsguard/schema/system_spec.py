"""Concrete audit system schemas."""

from __future__ import annotations

import math
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.assumption_spec import AssumptionSpec
from physicsguard.schema.variable import ensure_non_empty, is_qualified_variable_name


class VariableOverrideSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    initial_guess: Optional[float] = None
    scale: Optional[float] = None

    @model_validator(mode="after")
    def _validate_override(self) -> "VariableOverrideSpec":
        for field_name in ("lower_bound", "upper_bound", "initial_guess", "scale"):
            value = getattr(self, field_name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite")
        if (
            self.lower_bound is not None
            and self.upper_bound is not None
            and self.lower_bound >= self.upper_bound
        ):
            raise ValueError("lower_bound must be less than upper_bound")
        if self.scale is not None and self.scale <= 0:
            raise ValueError("scale must be positive")
        return self


class ComponentInstanceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    variable_overrides: dict[str, VariableOverrideSpec] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _id_valid(cls, value: str) -> str:
        ensure_non_empty(value, "component id")
        if "." in value:
            raise ValueError("component id cannot contain dots")
        return value

    @field_validator("type")
    @classmethod
    def _type_valid(cls, value: str) -> str:
        return ensure_non_empty(value, "component type")


class ConnectionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_variable: str
    to_variable: str
    description: Optional[str] = None

    @field_validator("from_variable", "to_variable")
    @classmethod
    def _endpoint_qualified(cls, value: str) -> str:
        if not is_qualified_variable_name(value):
            raise ValueError("connection endpoint must use component.variable format")
        return value


class BoundarySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable: str
    value: float
    unit: Optional[str] = None
    scale: Optional[float] = None
    description: Optional[str] = None

    @field_validator("variable")
    @classmethod
    def _variable_qualified(cls, value: str) -> str:
        if not is_qualified_variable_name(value):
            raise ValueError("boundary variable must use component.variable format")
        return value

    @model_validator(mode="after")
    def _validate_boundary(self) -> "BoundarySpec":
        if not math.isfinite(self.value):
            raise ValueError("boundary value must be finite")
        if self.scale is not None and (not math.isfinite(self.scale) or self.scale <= 0):
            raise ValueError("boundary scale must be finite and positive")
        return self


class InputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float | str | bool
    unit: Optional[str] = None
    description: Optional[str] = None


class SolverSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str = "least_squares"
    max_iterations: int = 30
    tolerance: float = 1e-4
    audit_threshold: float = 1.0
    verbose: bool = False

    @model_validator(mode="after")
    def _validate_solver(self) -> "SolverSpec":
        if self.method != "least_squares":
            raise ValueError("solver method currently supports only 'least_squares'")
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        if not math.isfinite(self.tolerance) or self.tolerance <= 0:
            raise ValueError("tolerance must be finite and positive")
        if not math.isfinite(self.audit_threshold) or self.audit_threshold <= 0:
            raise ValueError("audit_threshold must be finite and positive")
        return self


class SystemSpec(BaseModel):
    """Concrete audit system assembled from component instances."""

    model_config = ConfigDict(extra="forbid")

    system_name: str
    description: Optional[str] = None
    components: list[ComponentInstanceSpec]
    connections: list[ConnectionSpec] = Field(default_factory=list)
    boundaries: list[BoundarySpec] = Field(default_factory=list)
    inputs: dict[str, InputSpec] = Field(default_factory=dict)
    assumptions: list[AssumptionSpec] = Field(default_factory=list)
    solver: SolverSpec = Field(default_factory=SolverSpec)

    @field_validator("system_name")
    @classmethod
    def _system_name_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "system_name")

    @model_validator(mode="after")
    def _validate_components(self) -> "SystemSpec":
        ids = [component.id for component in self.components]
        if len(ids) != len(set(ids)):
            raise ValueError("component ids must be unique")
        assumption_ids = [assumption.id for assumption in self.assumptions]
        if len(assumption_ids) != len(set(assumption_ids)):
            raise ValueError("assumption ids must be unique")
        return self
