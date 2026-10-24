"""Schemas for per-file testbench data contracts."""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.data_file_manifest import DataFileManifestSpec
from physicsguard.schema.observation_spec import SourceModelSpec
from physicsguard.schema.parameter_coverage import (
    CoveragePolicySpec, MappingConfidence,
)
from physicsguard.schema.variable import ensure_non_empty


class FieldAliasSpec(BaseModel):
    """Accepted field-name alias for a testbench profile."""

    model_config = ConfigDict(extra="forbid")

    source_name: str
    canonical_name: str
    reason: Optional[str] = None

    @field_validator("source_name", "canonical_name")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)


class TestBenchProfileSpec(BaseModel):
    """Reusable profile for one testbench/version family."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    bench_id: Optional[str] = None
    bench_version: Optional[str] = None
    time_column: Optional[str] = None
    delimiter: Optional[str] = None
    encoding: str = "utf-8"
    field_units: dict[str, str] = Field(default_factory=dict)
    expected_fields: list[str] = Field(default_factory=list)
    aliases: list[FieldAliasSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("profile_id")
    @classmethod
    def _profile_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "profile_id")

    @field_validator("expected_fields")
    @classmethod
    def _expected_fields_valid(cls, values: list[str]) -> list[str]:
        for value in values:
            ensure_non_empty(value, "expected_fields")
        return values

    @model_validator(mode="after")
    def _profile_valid(self) -> "TestBenchProfileSpec":
        if len(self.expected_fields) != len(set(self.expected_fields)):
            raise ValueError("expected_fields must be unique")
        _ensure_json_serializable(self.metadata, "testbench profile metadata")
        return self


class ExtractorProfileSpec(BaseModel):
    """Reusable extractor profile bound to a manifest generation script."""

    model_config = ConfigDict(extra="forbid")

    profile_id: Optional[str] = None
    script: str
    script_hash: Optional[str] = None
    config_hash: Optional[str] = None
    format_kind: Optional[str] = None
    delimiter: Optional[str] = None
    encoding: str = "utf-8"
    time_column: Optional[str] = None
    field_units: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("profile_id")
    @classmethod
    def _profile_id_not_empty(cls, value: Optional[str]) -> Optional[str]:
        return ensure_non_empty(value, "profile_id") if value is not None else value

    @field_validator("script")
    @classmethod
    def _script_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "extractor script")

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "ExtractorProfileSpec":
        _ensure_json_serializable(self.metadata, "extractor profile metadata")
        return self


class DatasetSegmentSpec(BaseModel):
    """Optional segment within a single test file."""

    model_config = ConfigDict(extra="forbid")

    segment_id: str
    row_range: Optional[list[int]] = None
    time_range: Optional[list[str | float]] = None
    mode: Optional[str] = None
    coverage_policy: Optional[CoveragePolicySpec | str] = None
    audit_participation: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("segment_id")
    @classmethod
    def _segment_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "segment_id")

    @field_validator("row_range")
    @classmethod
    def _row_range_valid(cls, value: Optional[list[int]]) -> Optional[list[int]]:
        if value is None:
            return value
        if len(value) != 2 or value[0] < 0 or value[1] < value[0]:
            raise ValueError("row_range must be [start, end] with nonnegative start <= end")
        return value

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "DatasetSegmentSpec":
        _ensure_json_serializable(self.metadata, "dataset segment metadata")
        return self


class KnownDefectSpec(BaseModel):
    """Known file defect and the resulting safe-claim boundary."""

    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    impact: Optional[str] = None
    safe_claim: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "description")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "KnownDefectSpec":
        _ensure_json_serializable(self.metadata, "known defect metadata")
        return self


class ConversionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    factor: float = 1.0
    offset: float = 0.0


class ContractCoverageSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_confidence: MappingConfidence = "medium"


class FieldSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    role: str | None = None
    unit: str | None = None
    target: str | None = None
    targets: dict[str, str] = Field(default_factory=dict)
    confidence: Optional[MappingConfidence] = None
    evidence: str | None = None
    reason: str | None = None
    conversion: ConversionSpec | None = None
    planned_child_model: dict[str, Any] | None = None
    review_required: bool = False

    @model_validator(mode="after")
    def _targets_valid(self):
        if self.target is not None and self.targets:
            raise ValueError("use target or targets, not both")
        if set(self.targets) - {"row", "next_row"}:
            raise ValueError("targets keys must be row or next_row")
        return self


class TestFileContractSpec(BaseModel):
    """One executable file: identity, field roles, mapping evidence and units."""
    model_config = ConfigDict(extra="forbid")
    contract_id: str
    source_model: Optional[SourceModelSpec] = None
    data_file: str
    manifest: str
    model: str
    model_hash: str | None = None
    extractor: ExtractorProfileSpec | None = None
    time_column: str | None = None
    fields: dict[str, FieldSpec]
    coverage: ContractCoverageSpec = Field(default_factory=ContractCoverageSpec)
    segments: list[DatasetSegmentSpec] = Field(default_factory=list)
    known_defects: list[KnownDefectSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _reject_legacy(cls, value):
        old = {"testbench_profile", "model_binding", "parameter_catalog", "role_matrix", "mapping_edges", "coverage_policy", "logical_dataset", "extractor_profile"}
        if isinstance(value, dict) and old & value.keys():
            raise ValueError("This is a multi-file contract from before 0.15.19; rewrite it as one file using references/templates/test_file_contract.yaml")
        return value

    @field_validator("contract_id", "data_file", "manifest", "model")
    @classmethod
    def _required(cls, value, info):
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _unique_rows(self):
        for rows, key in [(self.segments, "segment_id"), (self.known_defects, "id")]:
            ids = [getattr(row, key) for row in rows]
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate {key}")
        return self


TestFileContract = TestFileContractSpec


def _ensure_json_serializable(value: Any, field_name: str) -> None:
    try:
        json.dumps(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be JSON-serializable") from exc
