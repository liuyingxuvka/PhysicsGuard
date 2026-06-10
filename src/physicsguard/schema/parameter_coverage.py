"""Schemas for test-file parameter coverage contracts."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_non_empty


CoverageStatus = Literal[
    "covered",
    "review_required",
    "planned_child_model",
    "excluded",
    "unmapped",
    "missing",
]
MappingTargetType = Literal[
    "physics_variable",
    "model_variable",
    "variable",
    "model_parameter",
    "parameter",
    "hierarchy_block",
    "block",
    "residual",
    "post_check",
    "metadata",
    "source_field",
    "derived_quantity",
]
MappingEvidenceType = Literal[
    "field_name_match",
    "label_match",
    "unit_match",
    "pid_topology",
    "testbench_topology",
    "datasheet",
    "human_provided",
    "code_reference",
    "derived_formula",
    "other",
]


class ParameterCatalogEntrySpec(BaseModel):
    """Stable identity for one source field in a test data file."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    field_name: str
    canonical_id: Optional[str] = None
    unit: Optional[str] = None
    required: bool = True
    description: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_id", "field_name")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "ParameterCatalogEntrySpec":
        _ensure_json_serializable(self.metadata, "catalog entry metadata")
        return self


class ParameterCatalogSpec(BaseModel):
    """All source fields known for one resolved test file contract."""

    model_config = ConfigDict(extra="forbid")

    parameters: list[ParameterCatalogEntrySpec]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _unique_catalog_entries(self) -> "ParameterCatalogSpec":
        source_ids = [item.source_id for item in self.parameters]
        field_names = [item.field_name for item in self.parameters]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("parameter catalog source_id values must be unique")
        if len(field_names) != len(set(field_names)):
            raise ValueError("parameter catalog field_name values must be unique")
        _ensure_json_serializable(self.metadata, "parameter catalog metadata")
        return self


class RoleAssignmentSpec(BaseModel):
    """Role and disposition assigned to one source field."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    testbench_role: str
    physical_role: str
    model_role: str
    coverage_status: CoverageStatus
    owner_block_id: Optional[str] = None
    verification_role: Optional[str] = None
    reason: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_id", "testbench_role", "physical_role", "model_role")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _role_consistent(self) -> "RoleAssignmentSpec":
        if self.coverage_status in {"excluded", "planned_child_model", "review_required"}:
            if not self.reason or not self.reason.strip():
                raise ValueError(f"{self.coverage_status} role assignments require reason")
        _ensure_json_serializable(self.metadata, "role metadata")
        return self


class ParameterRoleMatrixSpec(BaseModel):
    """Coverage role matrix for the manifest fields."""

    model_config = ConfigDict(extra="forbid")

    roles: list[RoleAssignmentSpec]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _unique_roles(self) -> "ParameterRoleMatrixSpec":
        source_ids = [item.source_id for item in self.roles]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("role matrix source_id values must be unique")
        _ensure_json_serializable(self.metadata, "role matrix metadata")
        return self


class MappingEvidenceSpec(BaseModel):
    """Evidence explaining why a mapping edge is justified."""

    model_config = ConfigDict(extra="forbid")

    evidence_type: MappingEvidenceType
    source: str
    description: str
    anchor: Optional[str] = None
    confidence: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source", "description")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("confidence")
    @classmethod
    def _confidence_valid(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not 0 <= value <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "MappingEvidenceSpec":
        _ensure_json_serializable(self.metadata, "mapping evidence metadata")
        return self


class MappingEdgeSpec(BaseModel):
    """Relationship from a test-file source field to model or coverage target."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source_id: str
    relation: str
    target_type: MappingTargetType
    target: str
    confidence: Optional[float] = None
    unit_evidence: Optional[str] = None
    evidence: list[MappingEvidenceSpec] = Field(default_factory=list)
    stale_when: list[str] = Field(default_factory=list)
    review_required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "source_id", "relation", "target")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("confidence")
    @classmethod
    def _confidence_valid(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not 0 <= value <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @field_validator("stale_when")
    @classmethod
    def _stale_when_not_empty(cls, values: list[str]) -> list[str]:
        for value in values:
            ensure_non_empty(value, "stale_when")
        return values

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "MappingEdgeSpec":
        _ensure_json_serializable(self.metadata, "mapping edge metadata")
        return self


class ParameterMappingEdgesSpec(BaseModel):
    """Mapping edge set for a test file contract."""

    model_config = ConfigDict(extra="forbid")

    edges: list[MappingEdgeSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _unique_edges(self) -> "ParameterMappingEdgesSpec":
        ids = [item.id for item in self.edges]
        if len(ids) != len(set(ids)):
            raise ValueError("mapping edge ids must be unique")
        _ensure_json_serializable(self.metadata, "mapping edge set metadata")
        return self


class CoveragePolicySpec(BaseModel):
    """Policy knobs for fail-closed coverage checking."""

    model_config = ConfigDict(extra="forbid")

    require_all_manifest_fields: bool = True
    allow_review_required: bool = False
    allow_unmapped_planned: bool = True
    fail_on_stale: bool = True
    fail_on_duplicate_active_mappings: bool = True
    require_mapping_for_covered_roles: bool = True
    require_mapping_evidence: bool = True
    minimum_mapping_confidence: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("minimum_mapping_confidence")
    @classmethod
    def _minimum_mapping_confidence_valid(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not 0 <= value <= 1:
            raise ValueError("minimum_mapping_confidence must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "CoveragePolicySpec":
        _ensure_json_serializable(self.metadata, "coverage policy metadata")
        return self


def _ensure_json_serializable(value: Any, field_name: str) -> None:
    try:
        json.dumps(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be JSON-serializable") from exc


__all__ = [
    "CoveragePolicySpec",
    "CoverageStatus",
    "MappingEdgeSpec",
    "MappingEvidenceSpec",
    "MappingEvidenceType",
    "MappingTargetType",
    "ParameterCatalogEntrySpec",
    "ParameterCatalogSpec",
    "ParameterMappingEdgesSpec",
    "ParameterRoleMatrixSpec",
    "RoleAssignmentSpec",
]
