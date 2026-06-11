"""Schemas for project evidence registries and gap reports."""

from __future__ import annotations

import json
import math
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_non_empty


ArtifactKind = Literal[
    "raw_test_data",
    "cleaned_test_data",
    "derived_test_data",
    "source_document",
    "model_file",
    "test_file_contract",
    "logical_dataset",
    "relation_index",
    "validation_plan",
    "validation_report",
    "model_library",
    "parameter_catalog",
    "context_card",
    "evidence_bundle",
    "other",
]
FactKind = Literal[
    "physical_parameter",
    "component_identity",
    "vendor_identity",
    "software_version",
    "configuration_fact",
    "testbench_fact",
    "test_object_fact",
    "time_series_reference",
    "derived_value",
    "calibrated_value",
    "human_override",
    "other",
]
BehaviorKind = Literal[
    "static",
    "configuration_static",
    "piecewise_static",
    "time_series_reference",
    "derived",
    "calibrated",
    "human_override",
    "equipment_identity",
    "software_version",
    "other",
]
ContextKind = Literal["model", "testbench", "test_object", "dataset", "generic"]
RequirementKind = Literal["fact", "artifact", "context", "bundle", "validation_report", "binding"]
BindingKind = Literal[
    "source_field_to_model_target",
    "fact_to_model_parameter",
    "artifact_to_contract",
    "validation_report_to_model_library",
    "context_to_artifact",
    "other",
]
BindingExpectationKind = Literal["test_field", "engineering_fact", "model_target", "artifact", "other"]
BindingExpectationPolicy = Literal["must_bind", "exempt", "unknown"]
GapSeverity = Literal["blocking", "review", "optional"]
ReviewState = Literal[
    "unknown",
    "ai_registered",
    "ai_extracted",
    "human_confirmed",
    "review_required",
    "source_missing",
    "rejected",
]
RecordStatus = Literal["draft", "active", "superseded", "deprecated", "missing", "unresolved", "resolved"]


class ReviewSpec(BaseModel):
    """Review and confidence state for evidence records."""

    model_config = ConfigDict(extra="forbid")

    state: ReviewState = "unknown"
    confidence: Optional[float] = None
    needs_human_review: bool = False
    reviewer: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("confidence")
    @classmethod
    def _confidence_valid(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not 0 <= value <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "ReviewSpec":
        _ensure_json_serializable(self.metadata, "review metadata")
        return self


class AppliesToSpec(BaseModel):
    """Scope where evidence is intended to apply."""

    model_config = ConfigDict(extra="forbid")

    project: Optional[str] = None
    testbench: Optional[str] = None
    test_object: Optional[str] = None
    dataset: Optional[str] = None
    model: Optional[str] = None
    test_run: Optional[str] = None
    test_phase: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "AppliesToSpec":
        _ensure_json_serializable(self.metadata, "applicability metadata")
        return self


class SourceReferenceSpec(BaseModel):
    """Source anchor for an artifact or fact."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: Optional[str] = None
    path: Optional[str] = None
    external_reference: Optional[str] = None
    location: Optional[str] = None
    anchor_text: Optional[str] = None
    source_missing_reason: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _source_reference_valid(self) -> "SourceReferenceSpec":
        if not any((self.artifact_id, self.path, self.external_reference, self.source_missing_reason)):
            raise ValueError("source reference needs artifact_id, path, external_reference, or source_missing_reason")
        _ensure_json_serializable(self.metadata, "source reference metadata")
        return self


class TimeContextSpec(BaseModel):
    """Optional file/test timing context."""

    model_config = ConfigDict(extra="forbid")

    produced_at: Optional[str] = None
    test_started_at: Optional[str] = None
    test_ended_at: Optional[str] = None
    data_time_range: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "TimeContextSpec":
        _ensure_json_serializable(self.metadata, "time context metadata")
        return self


class ProjectRunPeriodSpec(BaseModel):
    """Project-level run or evidence coverage period."""

    model_config = ConfigDict(extra="forbid")

    run_started_at: Optional[str] = None
    run_ended_at: Optional[str] = None
    coverage_period: Optional[str] = None
    unknown_reason: Optional[str] = None
    source_refs: list[SourceReferenceSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "ProjectRunPeriodSpec":
        _ensure_json_serializable(self.metadata, "project run period metadata")
        return self


class ProjectLocationSpec(BaseModel):
    """Project-level location record; may be a site, lab, vehicle route, or unknown placeholder."""

    model_config = ConfigDict(extra="forbid")

    location_id: str
    label: Optional[str] = None
    role: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    facility: Optional[str] = None
    external_reference: Optional[str] = None
    unknown_reason: Optional[str] = None
    source_refs: list[SourceReferenceSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("location_id")
    @classmethod
    def _location_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "location_id")

    @model_validator(mode="after")
    def _location_valid(self) -> "ProjectLocationSpec":
        has_detail = any((self.label, self.country, self.region, self.city, self.facility, self.external_reference))
        if not has_detail and not self.unknown_reason:
            raise ValueError("project location requires location detail or unknown_reason")
        _ensure_json_serializable(self.metadata, "project location metadata")
        return self


class ProjectProfileSpec(BaseModel):
    """Basic project profile for AI onboarding and evidence maintenance."""

    model_config = ConfigDict(extra="forbid")

    project_name: Optional[str] = None
    project_name_unknown_reason: Optional[str] = None
    owner: Optional[str] = None
    customer: Optional[str] = None
    objective: Optional[str] = None
    run_period: ProjectRunPeriodSpec = Field(default_factory=ProjectRunPeriodSpec)
    locations: list[ProjectLocationSpec] = Field(default_factory=list)
    location_unknown_reason: Optional[str] = None
    source_refs: list[SourceReferenceSpec] = Field(default_factory=list)
    review: ReviewSpec = Field(default_factory=ReviewSpec)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _profile_valid(self) -> "ProjectProfileSpec":
        _ensure_json_serializable(self.metadata, "project profile metadata")
        return self


class ArtifactLineageSpec(BaseModel):
    """How an artifact was derived, split, merged, or cleaned."""

    model_config = ConfigDict(extra="forbid")

    derived_from: list[str] = Field(default_factory=list)
    split_from: list[str] = Field(default_factory=list)
    merged_from: list[str] = Field(default_factory=list)
    process_notes: list[str] = Field(default_factory=list)
    original_source_missing_reason: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("derived_from", "split_from", "merged_from", "process_notes")
    @classmethod
    def _list_values_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "ArtifactLineageSpec":
        _ensure_json_serializable(self.metadata, "artifact lineage metadata")
        return self


class ArtifactRecordSpec(BaseModel):
    """Project-level record for any important file or artifact."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    artifact_kind: ArtifactKind
    path: Optional[str] = None
    local_copy_path: Optional[str] = None
    external_reference: Optional[str] = None
    do_not_copy: bool = False
    copied_at: Optional[str] = None
    copy_hash: Optional[str] = None
    registered_at: str
    created_at: Optional[str] = None
    physicsguard_version: Optional[str] = None
    schema_version: str = "1.0"
    status: RecordStatus = "active"
    hash: Optional[str] = None
    size_bytes: Optional[int] = None
    time_context: TimeContextSpec = Field(default_factory=TimeContextSpec)
    source_refs: list[SourceReferenceSpec] = Field(default_factory=list)
    lineage: ArtifactLineageSpec = Field(default_factory=ArtifactLineageSpec)
    applies_to: AppliesToSpec = Field(default_factory=AppliesToSpec)
    review: ReviewSpec = Field(default_factory=ReviewSpec)
    ai_workspace: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_id", "registered_at")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("size_bytes")
    @classmethod
    def _size_valid(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("size_bytes must be nonnegative")
        return value

    @model_validator(mode="after")
    def _artifact_valid(self) -> "ArtifactRecordSpec":
        if not self.path and not self.external_reference and not self.local_copy_path:
            raise ValueError("artifact requires path, local_copy_path, or external_reference")
        if self.do_not_copy and self.local_copy_path:
            raise ValueError("do_not_copy artifact cannot declare local_copy_path")
        _ensure_json_serializable(self.ai_workspace, "artifact ai_workspace")
        _ensure_json_serializable(self.metadata, "artifact metadata")
        return self


class PiecewiseSegmentSpec(BaseModel):
    """Small piecewise fact segment."""

    model_config = ConfigDict(extra="forbid")

    segment_id: str
    value: Optional[Any] = None
    unit: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    valid_from_test_time_s: Optional[float] = None
    valid_until_test_time_s: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("segment_id")
    @classmethod
    def _segment_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "segment_id")

    @model_validator(mode="after")
    def _segment_valid(self) -> "PiecewiseSegmentSpec":
        for field_name in ("valid_from_test_time_s", "valid_until_test_time_s"):
            value = getattr(self, field_name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite")
        if (
            self.valid_from_test_time_s is not None
            and self.valid_until_test_time_s is not None
            and self.valid_from_test_time_s >= self.valid_until_test_time_s
        ):
            raise ValueError("segment valid_from_test_time_s must be less than valid_until_test_time_s")
        _ensure_json_serializable(self.value, "piecewise segment value")
        _ensure_json_serializable(self.metadata, "piecewise segment metadata")
        return self


class FactBehaviorSpec(BaseModel):
    """How a fact behaves in time or derivation."""

    model_config = ConfigDict(extra="forbid")

    kind: BehaviorKind = "static"
    time_series_artifact: Optional[str] = None
    time_series_field: Optional[str] = None
    piecewise_segments: list[PiecewiseSegmentSpec] = Field(default_factory=list)
    expression: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _behavior_valid(self) -> "FactBehaviorSpec":
        if self.kind == "time_series_reference" and not (self.time_series_artifact and self.time_series_field):
            raise ValueError("time_series_reference requires time_series_artifact and time_series_field")
        if self.kind == "piecewise_static" and not self.piecewise_segments:
            raise ValueError("piecewise_static requires piecewise_segments")
        _ensure_json_serializable(self.metadata, "fact behavior metadata")
        return self


class EvidenceBindingSpec(BaseModel):
    """Optional links from facts to model/test targets."""

    model_config = ConfigDict(extra="forbid")

    model_targets: list[str] = Field(default_factory=list)
    dataset_fields: list[str] = Field(default_factory=list)
    validation_roles: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("model_targets", "dataset_fields", "validation_roles")
    @classmethod
    def _list_values_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "EvidenceBindingSpec":
        _ensure_json_serializable(self.metadata, "evidence binding metadata")
        return self


class EvidenceBindingRecordSpec(BaseModel):
    """Project-level binding summary; authority remains in the named source artifact."""

    model_config = ConfigDict(extra="forbid")

    binding_id: str
    binding_kind: BindingKind
    authority: str
    source_artifact: Optional[str] = None
    source_contract: Optional[str] = None
    source_field: Optional[str] = None
    source_fact: Optional[str] = None
    canonical_quantity: Optional[str] = None
    unit: Optional[str] = None
    model_target: Optional[str] = None
    model_part: Optional[str] = None
    validation_role: Optional[str] = None
    mapping_confidence: Optional[float] = None
    status: RecordStatus = "active"
    review: ReviewSpec = Field(default_factory=ReviewSpec)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("binding_id", "authority")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("mapping_confidence")
    @classmethod
    def _confidence_valid(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not 0 <= value <= 1:
            raise ValueError("mapping_confidence must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def _binding_valid(self) -> "EvidenceBindingRecordSpec":
        if self.binding_kind == "source_field_to_model_target" and not (self.source_field and self.model_target):
            raise ValueError("source_field_to_model_target requires source_field and model_target")
        if self.binding_kind == "fact_to_model_parameter" and not (self.source_fact and self.model_target):
            raise ValueError("fact_to_model_parameter requires source_fact and model_target")
        _ensure_json_serializable(self.metadata, "evidence binding record metadata")
        return self


class BindingExpectationSpec(BaseModel):
    """Binding maintenance expectation for a field, fact, or model target."""

    model_config = ConfigDict(extra="forbid")

    expectation_id: str
    subject_kind: BindingExpectationKind
    subject_id: str
    policy: BindingExpectationPolicy = "must_bind"
    source_artifact: Optional[str] = None
    source_contract: Optional[str] = None
    source_field: Optional[str] = None
    source_fact: Optional[str] = None
    model_target: Optional[str] = None
    model_part: Optional[str] = None
    required_for: list[str] = Field(default_factory=list)
    missing_severity: GapSeverity = "review"
    exemption_reason: Optional[str] = None
    review: ReviewSpec = Field(default_factory=ReviewSpec)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("expectation_id", "subject_id")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("required_for")
    @classmethod
    def _required_for_not_empty(cls, values: list[str]) -> list[str]:
        for value in values:
            ensure_non_empty(value, "required_for")
        return values

    @model_validator(mode="after")
    def _expectation_valid(self) -> "BindingExpectationSpec":
        if self.policy == "exempt" and not (self.exemption_reason and self.exemption_reason.strip()):
            raise ValueError("exempt binding expectation requires exemption_reason")
        if self.subject_kind == "test_field" and not (self.source_field or self.subject_id):
            raise ValueError("test_field binding expectation requires source_field or subject_id")
        if self.subject_kind == "engineering_fact" and not (self.source_fact or self.subject_id):
            raise ValueError("engineering_fact binding expectation requires source_fact or subject_id")
        _ensure_json_serializable(self.metadata, "binding expectation metadata")
        return self


class LifecycleSpec(BaseModel):
    """Lifecycle, replacement, and conflict state."""

    model_config = ConfigDict(extra="forbid")

    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    conflict_with: list[str] = Field(default_factory=list)
    status: RecordStatus = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("conflict_with")
    @classmethod
    def _conflicts_not_empty(cls, values: list[str]) -> list[str]:
        for value in values:
            ensure_non_empty(value, "conflict_with")
        return values

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "LifecycleSpec":
        _ensure_json_serializable(self.metadata, "lifecycle metadata")
        return self


class EngineeringFactRecordSpec(BaseModel):
    """Project evidence for parameters and non-parameter engineering facts."""

    model_config = ConfigDict(extra="forbid")

    fact_id: str
    fact_kind: FactKind
    value: Optional[Any] = None
    value_missing_reason: Optional[str] = None
    unit: Optional[str] = None
    behavior: FactBehaviorSpec = Field(default_factory=FactBehaviorSpec)
    source_refs: list[SourceReferenceSpec] = Field(default_factory=list)
    applies_to: AppliesToSpec = Field(default_factory=AppliesToSpec)
    bindings: EvidenceBindingSpec = Field(default_factory=EvidenceBindingSpec)
    review: ReviewSpec = Field(default_factory=ReviewSpec)
    lifecycle: LifecycleSpec = Field(default_factory=LifecycleSpec)
    ai_workspace: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("fact_id")
    @classmethod
    def _fact_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "fact_id")

    @model_validator(mode="after")
    def _fact_valid(self) -> "EngineeringFactRecordSpec":
        if self.value is None and not self.value_missing_reason:
            raise ValueError("fact requires value or value_missing_reason")
        _ensure_json_serializable(self.value, "engineering fact value")
        _ensure_json_serializable(self.ai_workspace, "engineering fact ai_workspace")
        _ensure_json_serializable(self.metadata, "engineering fact metadata")
        return self


class EvidenceRequirementSpec(BaseModel):
    """Requirement declared by a model/test/context."""

    model_config = ConfigDict(extra="forbid")

    requirement_id: Optional[str] = None
    kind: RequirementKind
    target_id: str
    required_for: list[str] = Field(default_factory=list)
    missing_severity: GapSeverity = "review"
    source_policy: Optional[str] = None
    reason: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("target_id")
    @classmethod
    def _target_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "target_id")

    @field_validator("required_for")
    @classmethod
    def _required_for_not_empty(cls, values: list[str]) -> list[str]:
        for value in values:
            ensure_non_empty(value, "required_for")
        return values

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "EvidenceRequirementSpec":
        _ensure_json_serializable(self.metadata, "evidence requirement metadata")
        return self


class ContextCardSpec(BaseModel):
    """Applicability and requirement context for a model, testbench, object, or dataset."""

    model_config = ConfigDict(extra="forbid")

    context_id: str
    context_kind: ContextKind
    artifact_id: Optional[str] = None
    created_at: Optional[str] = None
    physicsguard_version: Optional[str] = None
    intended_scope: AppliesToSpec = Field(default_factory=AppliesToSpec)
    known_invalid_scope: list[str] = Field(default_factory=list)
    model_parts: list["ModelPartSpec"] = Field(default_factory=list)
    required_evidence: list[EvidenceRequirementSpec] = Field(default_factory=list)
    source_refs: list[SourceReferenceSpec] = Field(default_factory=list)
    review: ReviewSpec = Field(default_factory=ReviewSpec)
    lifecycle: LifecycleSpec = Field(default_factory=LifecycleSpec)
    ai_workspace: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("context_id")
    @classmethod
    def _context_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "context_id")

    @field_validator("known_invalid_scope")
    @classmethod
    def _known_invalid_scope_not_empty(cls, values: list[str]) -> list[str]:
        for value in values:
            ensure_non_empty(value, "known_invalid_scope")
        return values

    @model_validator(mode="after")
    def _context_valid(self) -> "ContextCardSpec":
        _ensure_json_serializable(self.ai_workspace, "context card ai_workspace")
        _ensure_json_serializable(self.metadata, "context card metadata")
        return self


class ModelPartSpec(BaseModel):
    """Declared part or subsystem in a low-fidelity model context."""

    model_config = ConfigDict(extra="forbid")

    part_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    model_targets: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("part_id")
    @classmethod
    def _part_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "part_id")

    @field_validator("model_targets")
    @classmethod
    def _model_targets_not_empty(cls, values: list[str]) -> list[str]:
        for value in values:
            ensure_non_empty(value, "model_targets")
        return values

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "ModelPartSpec":
        _ensure_json_serializable(self.metadata, "model part metadata")
        return self


class ModelContextCardSpec(ContextCardSpec):
    """Model-specific context card."""

    context_kind: Literal["model"] = "model"


class TestbenchContextCardSpec(ContextCardSpec):
    """Testbench-specific context card."""

    context_kind: Literal["testbench"] = "testbench"


class TestObjectContextCardSpec(ContextCardSpec):
    """Test-object-specific context card."""

    context_kind: Literal["test_object"] = "test_object"


class EvidenceBundleSpec(BaseModel):
    """Handoff bundle consumed by validation and reuse routes."""

    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    model_context: Optional[str] = None
    artifacts: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    bindings: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)
    contracts: list[str] = Field(default_factory=list)
    validation_reports: list[str] = Field(default_factory=list)
    open_gaps: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    status: RecordStatus = "active"
    review: ReviewSpec = Field(default_factory=ReviewSpec)
    ai_workspace: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("bundle_id")
    @classmethod
    def _bundle_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "bundle_id")

    @field_validator("artifacts", "facts", "bindings", "contexts", "contracts", "validation_reports", "open_gaps", "missing_evidence")
    @classmethod
    def _list_values_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values

    @model_validator(mode="after")
    def _bundle_valid(self) -> "EvidenceBundleSpec":
        _ensure_json_serializable(self.ai_workspace, "evidence bundle ai_workspace")
        _ensure_json_serializable(self.metadata, "evidence bundle metadata")
        return self


class ConflictRecordSpec(BaseModel):
    """Unresolved or resolved conflict among evidence records."""

    model_config = ConfigDict(extra="forbid")

    conflict_id: str
    members: list[str]
    severity: GapSeverity = "review"
    status: Literal["unresolved", "resolved"] = "unresolved"
    reason: str
    resolution: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("conflict_id", "reason")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("members")
    @classmethod
    def _members_not_empty(cls, values: list[str]) -> list[str]:
        for value in values:
            ensure_non_empty(value, "conflict member")
        return values

    @model_validator(mode="after")
    def _conflict_valid(self) -> "ConflictRecordSpec":
        if len(self.members) < 2:
            raise ValueError("conflict requires at least two members")
        if self.status == "resolved" and not self.resolution:
            raise ValueError("resolved conflict requires resolution")
        _ensure_json_serializable(self.metadata, "conflict metadata")
        return self


class MissingEvidenceRecordSpec(BaseModel):
    """Explicit record that required evidence could not be found yet."""

    model_config = ConfigDict(extra="forbid")

    missing_id: str
    missing_kind: RequirementKind
    target: str
    required_by: list[str] = Field(default_factory=list)
    severity: GapSeverity = "review"
    search_attempts: list[str] = Field(default_factory=list)
    status: Literal["unresolved", "resolved"] = "unresolved"
    next_action: Optional[str] = None
    source_missing_reason: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("missing_id", "target")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("required_by", "search_attempts")
    @classmethod
    def _list_values_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values

    @model_validator(mode="after")
    def _missing_valid(self) -> "MissingEvidenceRecordSpec":
        _ensure_json_serializable(self.metadata, "missing evidence metadata")
        return self


class ProjectEvidenceRegistrySpec(BaseModel):
    """Project-level evidence registry."""

    model_config = ConfigDict(extra="forbid")

    registry_id: str
    project_id: Optional[str] = None
    schema_version: str = "1.0"
    physicsguard_version: Optional[str] = None
    created_at: Optional[str] = None
    project_profile: ProjectProfileSpec = Field(default_factory=ProjectProfileSpec)
    artifacts: list[ArtifactRecordSpec] = Field(default_factory=list)
    facts: list[EngineeringFactRecordSpec] = Field(default_factory=list)
    evidence_bindings: list[EvidenceBindingRecordSpec] = Field(default_factory=list)
    binding_expectations: list[BindingExpectationSpec] = Field(default_factory=list)
    context_cards: list[ContextCardSpec] = Field(default_factory=list)
    evidence_bundles: list[EvidenceBundleSpec] = Field(default_factory=list)
    conflicts: list[ConflictRecordSpec] = Field(default_factory=list)
    missing_evidence: list[MissingEvidenceRecordSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("registry_id")
    @classmethod
    def _registry_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "registry_id")

    @model_validator(mode="after")
    def _registry_valid(self) -> "ProjectEvidenceRegistrySpec":
        _ensure_unique([item.artifact_id for item in self.artifacts], "artifact ids")
        _ensure_unique([item.fact_id for item in self.facts], "fact ids")
        _ensure_unique([item.binding_id for item in self.evidence_bindings], "evidence binding ids")
        _ensure_unique([item.expectation_id for item in self.binding_expectations], "binding expectation ids")
        _ensure_unique([item.context_id for item in self.context_cards], "context ids")
        _ensure_unique([item.bundle_id for item in self.evidence_bundles], "bundle ids")
        _ensure_unique([item.conflict_id for item in self.conflicts], "conflict ids")
        _ensure_unique([item.missing_id for item in self.missing_evidence], "missing evidence ids")
        _ensure_json_serializable(self.metadata, "project evidence registry metadata")
        return self


class EvidenceCandidateSpec(BaseModel):
    """Read-only scanner candidate."""

    model_config = ConfigDict(extra="forbid")

    path: str
    artifact_kind: ArtifactKind
    reason: str
    registered: bool = False
    matched_artifact_id: Optional[str] = None


class EvidenceScanReportSpec(BaseModel):
    """Stable scanner report schema."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["project_evidence_scan"]
    status: Literal["pass", "partial", "fail"]
    ok: bool
    candidates: list[EvidenceCandidateSpec]
    findings: list[dict[str, Any]]
    summary: dict[str, Any]


class EvidenceGapSpec(BaseModel):
    """One evidence gap found by gap-check."""

    model_config = ConfigDict(extra="forbid")

    gap_id: str
    severity: GapSeverity
    gap_type: str
    target: str
    reason: str
    required_by: list[str] = Field(default_factory=list)
    suggested_search: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("gap_id", "gap_type", "target", "reason")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "EvidenceGapSpec":
        _ensure_json_serializable(self.metadata, "evidence gap metadata")
        return self


class EvidenceGapReportSpec(BaseModel):
    """Stable gap-check report schema."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["project_evidence_gap_report"]
    status: Literal["pass", "partial", "fail"]
    ok: bool
    registry_id: str
    bundle_id: Optional[str] = None
    blocking_gaps: list[EvidenceGapSpec] = Field(default_factory=list)
    review_gaps: list[EvidenceGapSpec] = Field(default_factory=list)
    optional_gaps: list[EvidenceGapSpec] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class ProjectEvidenceMapReportSpec(BaseModel):
    """AI-readable project evidence map for onboarding and navigation."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["project_evidence_map"]
    status: Literal["pass", "partial", "fail"]
    ok: bool
    registry_id: str
    project_id: Optional[str] = None
    project_scope: dict[str, Any] = Field(default_factory=dict)
    project_profile: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    tests: list[dict[str, Any]] = Field(default_factory=list)
    models: list[dict[str, Any]] = Field(default_factory=list)
    facts: list[dict[str, Any]] = Field(default_factory=list)
    bindings: list[dict[str, Any]] = Field(default_factory=list)
    binding_expectations: list[dict[str, Any]] = Field(default_factory=list)
    coverage_summary: dict[str, Any] = Field(default_factory=dict)
    gaps: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)


def _ensure_unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def _ensure_json_serializable(value: Any, field_name: str) -> None:
    try:
        json.dumps(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be JSON-serializable") from exc


__all__ = [
    "AppliesToSpec",
    "ArtifactKind",
    "ArtifactLineageSpec",
    "ArtifactRecordSpec",
    "BehaviorKind",
    "BindingExpectationKind",
    "BindingExpectationPolicy",
    "BindingExpectationSpec",
    "ConflictRecordSpec",
    "ContextCardSpec",
    "ContextKind",
    "EngineeringFactRecordSpec",
    "BindingKind",
    "EvidenceBindingSpec",
    "EvidenceBindingRecordSpec",
    "EvidenceBundleSpec",
    "EvidenceCandidateSpec",
    "EvidenceGapReportSpec",
    "EvidenceGapSpec",
    "EvidenceRequirementSpec",
    "EvidenceScanReportSpec",
    "FactBehaviorSpec",
    "FactKind",
    "GapSeverity",
    "LifecycleSpec",
    "MissingEvidenceRecordSpec",
    "ModelContextCardSpec",
    "ModelPartSpec",
    "PiecewiseSegmentSpec",
    "ProjectLocationSpec",
    "ProjectProfileSpec",
    "ProjectRunPeriodSpec",
    "ProjectEvidenceRegistrySpec",
    "ProjectEvidenceMapReportSpec",
    "RecordStatus",
    "RequirementKind",
    "ReviewSpec",
    "ReviewState",
    "SourceReferenceSpec",
    "TestObjectContextCardSpec",
    "TestbenchContextCardSpec",
    "TimeContextSpec",
]
