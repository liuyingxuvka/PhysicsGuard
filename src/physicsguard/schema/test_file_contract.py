"""Schemas for per-file testbench data contracts."""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.data_file_manifest import DataFileManifestSpec
from physicsguard.schema.parameter_coverage import (
    CoveragePolicySpec,
    ParameterCatalogSpec,
    ParameterMappingEdgesSpec,
    ParameterRoleMatrixSpec,
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


class ModelBindingSpec(BaseModel):
    """Binding from a test-file contract to PhysicsGuard model artifacts."""

    model_config = ConfigDict(extra="forbid")

    binding_id: str
    hierarchy_file: Optional[str] = None
    hierarchy_hash: Optional[str] = None
    physicsguard_version: Optional[str] = None
    expected_variables: list[str] = Field(default_factory=list)
    expected_parameters: list[str] = Field(default_factory=list)
    compatible_testbench_profiles: list[str] = Field(default_factory=list)
    compatible_manifest_signatures: list[str] = Field(default_factory=list)
    stale_when: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("binding_id")
    @classmethod
    def _binding_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "binding_id")

    @field_validator(
        "expected_variables",
        "expected_parameters",
        "compatible_testbench_profiles",
        "compatible_manifest_signatures",
        "stale_when",
    )
    @classmethod
    def _list_items_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "ModelBindingSpec":
        _ensure_json_serializable(self.metadata, "model binding metadata")
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


class TestFileContractSpec(BaseModel):
    """Resolved or resolvable contract for one concrete test data file."""

    model_config = ConfigDict(extra="forbid")

    contract_id: str
    file_id: str
    manifest: DataFileManifestSpec | str
    manifest_hash: Optional[str] = None
    testbench_profile: Optional[TestBenchProfileSpec | str] = None
    extractor_profile: Optional[ExtractorProfileSpec | str] = None
    model_binding: Optional[ModelBindingSpec | str] = None
    parameter_catalog: Optional[ParameterCatalogSpec | str] = None
    role_matrix: Optional[ParameterRoleMatrixSpec | str] = None
    mapping_edges: Optional[ParameterMappingEdgesSpec | str] = None
    coverage_policy: Optional[CoveragePolicySpec | str] = None
    segments: list[DatasetSegmentSpec] = Field(default_factory=list)
    known_defects: list[KnownDefectSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("contract_id", "file_id")
    @classmethod
    def _ids_not_empty(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("manifest_hash")
    @classmethod
    def _manifest_hash_not_empty(cls, value: Optional[str]) -> Optional[str]:
        return ensure_non_empty(value, "manifest_hash") if value is not None else value

    @model_validator(mode="after")
    def _contract_valid(self) -> "TestFileContractSpec":
        segment_ids = [segment.segment_id for segment in self.segments]
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError("dataset segment ids must be unique")
        defect_ids = [defect.id for defect in self.known_defects]
        if len(defect_ids) != len(set(defect_ids)):
            raise ValueError("known defect ids must be unique")
        _ensure_json_serializable(self.metadata, "test file contract metadata")
        return self


class TestFileReferenceSpec(BaseModel):
    """Project index reference to one test file contract."""

    model_config = ConfigDict(extra="forbid")

    contract: str
    file_id: Optional[str] = None
    testbench_profile_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("contract")
    @classmethod
    def _contract_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "contract")

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "TestFileReferenceSpec":
        _ensure_json_serializable(self.metadata, "test file reference metadata")
        return self


class TestFileProjectIndexSpec(BaseModel):
    """Project-level list of file-specific test contracts."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    test_files: list[TestFileReferenceSpec]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("project_id")
    @classmethod
    def _project_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "project_id")

    @model_validator(mode="after")
    def _index_valid(self) -> "TestFileProjectIndexSpec":
        contracts = [item.contract for item in self.test_files]
        if len(contracts) != len(set(contracts)):
            raise ValueError("project index contract references must be unique")
        _ensure_json_serializable(self.metadata, "project index metadata")
        return self


TestFileContract = TestFileContractSpec


def _ensure_json_serializable(value: Any, field_name: str) -> None:
    try:
        json.dumps(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be JSON-serializable") from exc


__all__ = [
    "DatasetSegmentSpec",
    "ExtractorProfileSpec",
    "FieldAliasSpec",
    "KnownDefectSpec",
    "ModelBindingSpec",
    "TestBenchProfileSpec",
    "TestFileContract",
    "TestFileContractSpec",
    "TestFileProjectIndexSpec",
    "TestFileReferenceSpec",
]
