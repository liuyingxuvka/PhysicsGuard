"""Schemas for generated test-data file manifests."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_non_empty


FieldDataType = Literal["empty", "boolean", "integer", "float", "string", "mixed"]
SamplingMode = Literal["unknown", "snapshot", "time_series", "event_series", "mixed"]
ContinuityStatus = Literal[
    "unknown",
    "not_applicable",
    "continuous",
    "continuous_with_gaps",
    "irregular",
]


class SourceFileSpec(BaseModel):
    """Identity evidence for the source data file."""

    model_config = ConfigDict(extra="forbid")

    path: str
    content_hash: Optional[str] = None
    size_bytes: Optional[int] = None

    @field_validator("path")
    @classmethod
    def _path_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "source file path")

    @field_validator("content_hash")
    @classmethod
    def _hash_not_empty(cls, value: Optional[str]) -> Optional[str]:
        return ensure_non_empty(value, "content_hash") if value is not None else value

    @field_validator("size_bytes")
    @classmethod
    def _size_nonnegative(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("size_bytes must be nonnegative")
        return value


class DataFormatSpec(BaseModel):
    """Machine-readable file format facts captured by the extractor."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    delimiter: Optional[str] = None
    encoding: Optional[str] = "utf-8"
    header_rows: int = 1
    decimal: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("kind")
    @classmethod
    def _kind_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "format kind")

    @field_validator("header_rows")
    @classmethod
    def _header_rows_nonnegative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("header_rows must be nonnegative")
        return value

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "DataFormatSpec":
        _ensure_json_serializable(self.metadata, "format metadata")
        return self


class FieldSummarySpec(BaseModel):
    """Per-column summary generated from the test data file."""

    model_config = ConfigDict(extra="forbid")

    name: str
    data_type: FieldDataType = "string"
    unit: Optional[str] = None
    non_null_count: Optional[int] = None
    null_count: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    role_hint: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _name_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "field name")

    @field_validator("non_null_count", "null_count")
    @classmethod
    def _counts_nonnegative(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("field counts must be nonnegative")
        return value

    @model_validator(mode="after")
    def _field_summary_valid(self) -> "FieldSummarySpec":
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError("min_value must be <= max_value")
        _ensure_json_serializable(self.metadata, "field metadata")
        return self


class DataShapeSpec(BaseModel):
    """File shape facts used for coverage and drift checks."""

    model_config = ConfigDict(extra="forbid")

    field_count: int
    row_count: Optional[int] = None
    sample_count: Optional[int] = None

    @field_validator("field_count", "row_count", "sample_count")
    @classmethod
    def _counts_valid(cls, value: Optional[int], info) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError(f"{info.field_name} must be nonnegative")
        return value


class TimeBasisSpec(BaseModel):
    """Time-series facts captured by the extractor when available."""

    model_config = ConfigDict(extra="forbid")

    time_column: Optional[str] = None
    start_time: Optional[str | float] = None
    end_time: Optional[str | float] = None
    duration_s: Optional[float] = None
    nominal_sample_rate_hz: Optional[float] = None
    sampling_mode: SamplingMode = "unknown"
    continuity: ContinuityStatus = "unknown"
    gap_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("time_column")
    @classmethod
    def _time_column_not_empty(cls, value: Optional[str]) -> Optional[str]:
        return ensure_non_empty(value, "time_column") if value is not None else value

    @field_validator("duration_s", "nominal_sample_rate_hz")
    @classmethod
    def _nonnegative_float(cls, value: Optional[float], info) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError(f"{info.field_name} must be nonnegative")
        return value

    @field_validator("gap_count")
    @classmethod
    def _gap_count_valid(cls, value: int) -> int:
        if value < 0:
            raise ValueError("gap_count must be nonnegative")
        return value

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "TimeBasisSpec":
        _ensure_json_serializable(self.metadata, "time metadata")
        return self


class ExtractorEvidenceSpec(BaseModel):
    """Extractor identity that makes the manifest reproducible."""

    model_config = ConfigDict(extra="forbid")

    script: str
    script_hash: Optional[str] = None
    config_hash: Optional[str] = None
    generated_at: Optional[str] = None
    version: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("script")
    @classmethod
    def _script_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "extractor script")

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "ExtractorEvidenceSpec":
        _ensure_json_serializable(self.metadata, "extractor metadata")
        return self


class DataFileManifestSpec(BaseModel):
    """Generated manifest for one concrete test data file."""

    model_config = ConfigDict(extra="forbid")

    manifest_id: Optional[str] = None
    source_file: SourceFileSpec
    format: DataFormatSpec
    shape: DataShapeSpec
    time: TimeBasisSpec = Field(default_factory=TimeBasisSpec)
    fields: list[FieldSummarySpec]
    extractor: ExtractorEvidenceSpec
    field_signature_hash: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("manifest_id")
    @classmethod
    def _manifest_id_not_empty(cls, value: Optional[str]) -> Optional[str]:
        return ensure_non_empty(value, "manifest_id") if value is not None else value

    @model_validator(mode="after")
    def _manifest_consistent(self) -> "DataFileManifestSpec":
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("manifest field names must be unique")
        if self.shape.field_count != len(self.fields):
            raise ValueError("shape.field_count must match number of fields")
        _ensure_json_serializable(self.metadata, "manifest metadata")
        return self


DataFileManifest = DataFileManifestSpec


def _ensure_json_serializable(value: Any, field_name: str) -> None:
    try:
        json.dumps(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be JSON-serializable") from exc


__all__ = [
    "ContinuityStatus",
    "DataFileManifest",
    "DataFileManifestSpec",
    "DataFormatSpec",
    "DataShapeSpec",
    "ExtractorEvidenceSpec",
    "FieldDataType",
    "FieldSummarySpec",
    "SamplingMode",
    "SourceFileSpec",
    "TimeBasisSpec",
]
