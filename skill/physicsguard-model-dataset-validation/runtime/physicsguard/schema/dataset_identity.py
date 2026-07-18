"""Schemas for logical test dataset identity and symmetric file relations."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_non_empty


DatasetRelationType = Literal[
    "byte_identical",
    "canonical_equivalent",
    "same_test_run",
    "same_testbench",
    "overlapping_fields",
    "redundant_sensor",
    "fallback_sensor",
    "same_physical_quantity",
    "related_only",
    "review_required",
]


class ManifestReferenceSpec(BaseModel):
    """Reference to a file-representation manifest without moving raw data."""

    model_config = ConfigDict(extra="forbid")

    manifest: str
    representation_id: Optional[str] = None
    content_hash: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("manifest")
    @classmethod
    def _manifest_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "manifest")

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "ManifestReferenceSpec":
        _ensure_json_serializable(self.metadata, "manifest reference metadata")
        return self


class RawDataPolicySpec(BaseModel):
    """Policy for large raw data referenced by project metadata."""

    model_config = ConfigDict(extra="forbid")

    do_not_move_raw_data: bool = True
    source_path_is_reference_only: bool = True
    allowed_copy_reason: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "RawDataPolicySpec":
        _ensure_json_serializable(self.metadata, "raw data policy metadata")
        return self


class LogicalDatasetRecordSpec(BaseModel):
    """Project-local identity record for one logical test dataset."""

    model_config = ConfigDict(extra="forbid")

    logical_dataset_id: str
    representation_manifests: list[ManifestReferenceSpec]
    testbench_profile_id: Optional[str] = None
    relation_group_ids: list[str] = Field(default_factory=list)
    semantic_signature_hash: Optional[str] = None
    value_fingerprint_hash: Optional[str] = None
    raw_data_policy: RawDataPolicySpec = Field(default_factory=RawDataPolicySpec)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("logical_dataset_id")
    @classmethod
    def _dataset_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "logical_dataset_id")

    @field_validator("relation_group_ids")
    @classmethod
    def _relation_groups_not_empty(cls, values: list[str]) -> list[str]:
        for value in values:
            ensure_non_empty(value, "relation_group_id")
        return values

    @model_validator(mode="after")
    def _record_valid(self) -> "LogicalDatasetRecordSpec":
        if not self.representation_manifests:
            raise ValueError("logical dataset requires at least one representation manifest")
        _ensure_json_serializable(self.metadata, "logical dataset metadata")
        return self


class DatasetRelationSpec(BaseModel):
    """Symmetric relation among datasets or source ids."""

    model_config = ConfigDict(extra="forbid")

    relation_id: str
    relation_type: DatasetRelationType
    members: list[str]
    target: Optional[str] = None
    confidence: Optional[float] = None
    evidence: list[str] = Field(default_factory=list)
    review_required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("relation_id")
    @classmethod
    def _relation_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "relation_id")

    @field_validator("members", "evidence")
    @classmethod
    def _list_values_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values

    @field_validator("confidence")
    @classmethod
    def _confidence_valid(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not 0 <= value <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def _relation_valid(self) -> "DatasetRelationSpec":
        if len(self.members) < 2:
            raise ValueError("dataset relation requires at least two members")
        if self.review_required and not self.evidence:
            raise ValueError("review-required relation must record evidence or reason")
        _ensure_json_serializable(self.metadata, "dataset relation metadata")
        return self


class TestFileRelationIndexSpec(BaseModel):
    """Project-level symmetric relation index for test files and datasets."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    logical_datasets: list[str] = Field(default_factory=list)
    relations: list[DatasetRelationSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("project_id")
    @classmethod
    def _project_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "project_id")

    @model_validator(mode="after")
    def _index_valid(self) -> "TestFileRelationIndexSpec":
        relation_ids = [item.relation_id for item in self.relations]
        if len(relation_ids) != len(set(relation_ids)):
            raise ValueError("relation ids must be unique")
        _ensure_json_serializable(self.metadata, "relation index metadata")
        return self


def _ensure_json_serializable(value: Any, field_name: str) -> None:
    try:
        json.dumps(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be JSON-serializable") from exc


__all__ = [
    "DatasetRelationSpec",
    "DatasetRelationType",
    "LogicalDatasetRecordSpec",
    "ManifestReferenceSpec",
    "RawDataPolicySpec",
    "TestFileRelationIndexSpec",
]
