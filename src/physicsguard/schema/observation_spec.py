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


class PhysicalPropertySpec(BaseModel):
    """A declared physical property (for example a density) that links two quantities in a conversion."""

    model_config = ConfigDict(extra="forbid")

    value: float
    unit: str
    source: Optional[str] = None

    @field_validator("value")
    @classmethod
    def _value_positive(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError("a declared property needs a finite positive value")
        return value

    @field_validator("unit")
    @classmethod
    def _unit_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("a declared property needs a unit")
        return value

    @model_validator(mode="after")
    def _physically_possible(self) -> "PhysicalPropertySpec":
        from physicsguard.core.units import implausible_property

        problem = implausible_property(self.value, self.unit)
        if problem is not None:
            raise ValueError(f"implausible_property: {problem}")
        return self


class ObservedValueSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Optional[float] = None
    raw_value: Optional[float] = None
    raw_unit: Optional[str] = None
    # Accepted input evidence survives counterfactual model_copy without recomputation.
    _raw_conversion: Optional[str] = PrivateAttr(default=None)
    # Set by convert_observed_rows: True when the tool converted the raw value itself (unit
    # table, or unit table plus a declared property) or checked the value against a reading in
    # external_signal, False when a conversion was applied or recorded that the tool could not
    # check, None when nothing was converted. _conversion_check says why in one sentence, and
    # _signal_disagrees marks a value that contradicts the reading in its external_signal.
    _conversion_checked: Optional[bool] = PrivateAttr(default=None)
    _conversion_check: Optional[str] = PrivateAttr(default=None)
    _signal_disagrees: bool = PrivateAttr(default=False)
    conversion_property: Optional[str] = None
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
        if self.conversion_property is not None and self.raw_value is None:
            raise ValueError("conversion_property needs raw_value and raw_unit: the tool converts the raw value with it")
        if self.raw_value is not None and self._raw_conversion is None and not (info.context or {}).get("raw_snapshot_ingestion"):
            raise ValueError("raw_snapshot_requires_load: read raw snapshots through load_observed_values before use")
        return self

    @field_validator("external_signal", "mapping_status", "conversion_note", "mapped_at", "conversion_property")
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
    properties: dict[str, PhysicalPropertySpec] = Field(default_factory=dict)
    variables: dict[str, ObservedValueSpec]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_observation(self) -> "ObservedValuesSpec":
        if not self.variables:
            raise ValueError("observed variables cannot be empty")
        for name, row in self.variables.items():
            if not is_qualified_variable_name(name):
                raise ValueError(
                    f"observed variable '{name}' must use component.variable format"
                )
            if row.conversion_property is not None and row.conversion_property not in self.properties:
                raise ValueError(
                    f"{name}: conversion_property {row.conversion_property} is not declared under properties"
                )
        try:
            json.dumps(self.metadata)
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must be JSON-serializable") from exc
        return self
