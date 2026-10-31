"""Observed variable value schemas."""

from __future__ import annotations

import json
import math
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationInfo, field_validator, model_validator

from physicsguard.schema.parameter_coverage import MappingConfidence
from physicsguard.schema.variable import is_qualified_variable_name


class SourceModelSpec(BaseModel):
    """Optional external-model context, with no effect on audit conclusions."""

    model_config = ConfigDict(extra="forbid", strict=True)

    model_name: Optional[str] = None
    tool: Optional[str] = None
    tool_version: Optional[str] = None
    model_version: Optional[str] = None
    scenario: Optional[str] = None
    export_time: Optional[str] = None


class ObservedValueSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Optional[float] = None
    raw_value: Optional[float] = None
    raw_unit: Optional[str] = None
    # Accepted input evidence survives counterfactual model_copy without recomputation.
    _raw_conversion: Optional[str] = PrivateAttr(default=None)
    unit: Optional[str] = None
    source: Optional[str] = None
    description: Optional[str] = None
    external_signal: Optional[str] = None
    mapping_confidence: Optional[MappingConfidence] = None
    mapping_status: Optional[str] = None
    review_required: bool = False
    conversion_factor: Optional[float] = None
    conversion_offset: Optional[float] = None
    conversion_note: Optional[str] = None
    mapped_at: Optional[str] = None
    stale_when: list[str] = Field(default_factory=list)

    @field_validator("value", "raw_value")
    @classmethod
    def _value_finite(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not math.isfinite(value):
            raise ValueError("observed value must be finite")
        return value

    @field_validator("raw_unit")
    @classmethod
    def _raw_unit_valid(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("raw_unit cannot be blank")
        return value

    @model_validator(mode="after")
    def _raw_value_valid(self, info: ValidationInfo) -> "ObservedValueSpec":
        if (self.raw_value is None) != (self.raw_unit is None):
            raise ValueError("raw_value and raw_unit must be supplied together")
        if self.value is None and self.raw_value is None:
            raise ValueError("value is required without raw_value and raw_unit")
        if self.raw_value is not None and self._raw_conversion is None and not (info.context or {}).get("raw_snapshot_ingestion"):
            raise ValueError("raw_snapshot_requires_load: read raw snapshots through load_observed_values before use")
        return self

    @field_validator("external_signal", "mapping_status", "conversion_note", "mapped_at")
    @classmethod
    def _optional_text_valid(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("mapping text fields cannot be blank")
        return value

    @field_validator("conversion_factor", "conversion_offset")
    @classmethod
    def _conversion_valid(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not math.isfinite(value):
            raise ValueError("conversion fields must be finite")
        return value

    @field_validator("stale_when")
    @classmethod
    def _stale_when_valid(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in values:
            if not item.strip():
                raise ValueError("stale_when entries cannot be blank")
            normalized.append(item.strip())
        return normalized


class ObservedValuesSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_name: Optional[str] = None
    source_model: Optional[SourceModelSpec] = None
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
