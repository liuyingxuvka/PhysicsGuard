"""Observed variable value schemas."""

from __future__ import annotations

import json
import math
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import is_qualified_variable_name


class ObservedValueSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float
    unit: Optional[str] = None
    source: Optional[str] = None
    description: Optional[str] = None

    @field_validator("value")
    @classmethod
    def _value_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("observed value must be finite")
        return value


class ObservedValuesSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_name: Optional[str] = None
    description: Optional[str] = None
    variables: dict[str, ObservedValueSpec]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_observation(self) -> "ObservedValuesSpec":
        if not self.variables:
            raise ValueError("observed variables cannot be empty")
        for name in self.variables:
            if not is_qualified_variable_name(name):
                raise ValueError(
                    f"observed variable '{name}' must use component.variable format"
                )
        try:
            json.dumps(self.metadata)
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must be JSON-serializable") from exc
        return self
