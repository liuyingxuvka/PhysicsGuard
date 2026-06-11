"""Schemas for database-level project catalogs and maps."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.project_evidence import GapSeverity, ReviewState
from physicsguard.schema.variable import ensure_non_empty


ProjectStatus = Literal["draft", "active", "archived", "missing", "review_required", "deprecated"]
DatabaseProjectLifecycleState = Literal[
    "candidate",
    "placeholder",
    "active_registered",
    "active_validated",
    "active_reusable",
    "blocked",
    "archived",
    "deprecated",
    "superseded",
    "rejected",
]
DatabaseHistoryEventType = Literal[
    "database_created",
    "policy_updated",
    "project_candidate_found",
    "project_admitted",
    "project_updated",
    "project_archived",
    "project_deprecated",
    "project_superseded",
    "project_rejected",
    "project_restored",
    "maintenance_audit",
    "handoff_rendered",
]
CatalogFreshnessState = Literal["unknown", "current", "stale", "review_required"]
ConfidenceState = Literal["unknown", "low", "medium", "high", "review_required", "not_applicable"]
ValidationState = Literal["unknown", "not_started", "partial", "validated", "failed", "stale", "blocked"]
ReuseState = Literal["unknown", "not_started", "partial", "validated", "failed", "stale", "blocked", "not_applicable"]
CandidateKind = Literal["project_evidence_registry", "model_library", "database_catalog", "other"]


class CatalogConfidenceSummarySpec(BaseModel):
    """Separated confidence and freshness summary for catalog navigation."""

    model_config = ConfigDict(extra="forbid")

    source_confidence: Optional[float] = None
    source_state: ConfidenceState = "unknown"
    mapping_confidence: Optional[float] = None
    mapping_state: ConfidenceState = "unknown"
    data_quality_state: ConfidenceState = "unknown"
    validation_state: ValidationState = "unknown"
    reuse_state: ReuseState = "unknown"
    catalog_freshness: CatalogFreshnessState = "unknown"
    review_state: ReviewState = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_confidence", "mapping_confidence")
    @classmethod
    def _confidence_valid(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not 0 <= value <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "CatalogConfidenceSummarySpec":
        _ensure_json_serializable(self.metadata, "catalog confidence metadata")
        return self


class CatalogPoliciesSpec(BaseModel):
    """Catalog-level claim and storage policies."""

    model_config = ConfigDict(extra="forbid")

    require_project_registry_for_cross_project_claims: bool = True
    require_gap_check_before_query_claims: bool = True
    require_explicit_scope_before_comparison: bool = True
    forbid_raw_data_payloads: bool = True
    stale_after_days: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("stale_after_days")
    @classmethod
    def _stale_after_days_valid(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value <= 0:
            raise ValueError("stale_after_days must be positive")
        return value

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "CatalogPoliciesSpec":
        _ensure_json_serializable(self.metadata, "catalog policies metadata")
        return self


class CatalogTagDictionarySpec(BaseModel):
    """Optional tag aliases and normalization hints."""

    model_config = ConfigDict(extra="forbid")

    aliases: dict[str, str] = Field(default_factory=dict)
    descriptions: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _dictionary_valid(self) -> "CatalogTagDictionarySpec":
        for key, value in {**self.aliases, **self.descriptions}.items():
            ensure_non_empty(key, "tag key")
            ensure_non_empty(value, "tag value")
        _ensure_json_serializable(self.metadata, "catalog tag dictionary metadata")
        return self


class CatalogModelLibraryReferenceSpec(BaseModel):
    """Database-level reference to a model-library index."""

    model_config = ConfigDict(extra="forbid")

    library_id: Optional[str] = None
    path: str
    registered_at: Optional[str] = None
    status: ProjectStatus = "active"
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("path")
    @classmethod
    def _path_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "path")

    @field_validator("library_id")
    @classmethod
    def _optional_library_id_not_empty(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            return ensure_non_empty(value, "library_id")
        return value

    @field_validator("notes")
    @classmethod
    def _notes_not_empty(cls, values: list[str]) -> list[str]:
        for value in values:
            ensure_non_empty(value, "notes")
        return values

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "CatalogModelLibraryReferenceSpec":
        _ensure_json_serializable(self.metadata, "model library reference metadata")
        return self


class DatabaseArchiveRecordSpec(BaseModel):
    """Lifecycle archive/deprecation/supersession marker for a project."""

    model_config = ConfigDict(extra="forbid")

    archive_state: Literal["archived", "deprecated", "superseded", "rejected"] = "archived"
    reason: str
    recorded_at: Optional[str] = None
    recorded_by: Optional[str] = None
    superseded_by_project_id: Optional[str] = None
    previous_state: Optional[DatabaseProjectLifecycleState] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("reason")
    @classmethod
    def _reason_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "reason")

    @model_validator(mode="after")
    def _archive_valid(self) -> "DatabaseArchiveRecordSpec":
        if self.archive_state == "superseded" and not self.superseded_by_project_id:
            raise ValueError("superseded archive records require superseded_by_project_id")
        _ensure_json_serializable(self.metadata, "archive record metadata")
        return self


class DatabaseProjectAdmissionSpec(BaseModel):
    """Admission evidence for promoting a project into a database lifecycle state."""

    model_config = ConfigDict(extra="forbid")

    requested_state: DatabaseProjectLifecycleState = "candidate"
    project_root: Optional[str] = None
    project_adoption_record: Optional[str] = None
    project_adoption_missing_reason: Optional[str] = None
    project_evidence_registry: Optional[str] = None
    project_evidence_missing_reason: Optional[str] = None
    evidence_gap_status: Literal["unknown", "pass", "partial", "fail"] = "unknown"
    validation_evidence: list[str] = Field(default_factory=list)
    model_library_evidence: list[str] = Field(default_factory=list)
    admitted_at: Optional[str] = None
    admitted_by: Optional[str] = None
    admission_reason: Optional[str] = None
    review_state: ReviewState = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "project_root",
        "project_adoption_record",
        "project_adoption_missing_reason",
        "project_evidence_registry",
        "project_evidence_missing_reason",
        "admitted_at",
        "admitted_by",
        "admission_reason",
    )
    @classmethod
    def _optional_strings_not_empty(cls, value: Optional[str], info) -> Optional[str]:
        if value is not None:
            return ensure_non_empty(value, info.field_name)
        return value

    @field_validator("validation_evidence", "model_library_evidence")
    @classmethod
    def _evidence_values_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "DatabaseProjectAdmissionSpec":
        _ensure_json_serializable(self.metadata, "database project admission metadata")
        return self


class CatalogProjectRecordSpec(BaseModel):
    """Lightweight database-level card for one project."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    project_name: Optional[str] = None
    project_name_unknown_reason: Optional[str] = None
    project_evidence_registry: Optional[str] = None
    registry_missing_reason: Optional[str] = None
    registry_digest: Optional[str] = None
    project_status: ProjectStatus = "active"
    lifecycle_state: DatabaseProjectLifecycleState = "active_registered"
    admission: DatabaseProjectAdmissionSpec = Field(default_factory=DatabaseProjectAdmissionSpec)
    archive_record: Optional[DatabaseArchiveRecordSpec] = None
    superseded_by_project_id: Optional[str] = None
    rejected_reason: Optional[str] = None
    domain_tags: list[str] = Field(default_factory=list)
    system_tags: list[str] = Field(default_factory=list)
    subsystem_tags: list[str] = Field(default_factory=list)
    component_tags: list[str] = Field(default_factory=list)
    test_object_tags: list[str] = Field(default_factory=list)
    testbench_tags: list[str] = Field(default_factory=list)
    measurement_tags: list[str] = Field(default_factory=list)
    run_period_summary: Optional[str] = None
    location_summary: Optional[str] = None
    has_test_data: Optional[bool] = None
    has_model: Optional[bool] = None
    has_validation: Optional[bool] = None
    has_model_library_entry: Optional[bool] = None
    artifact_counts: dict[str, int] = Field(default_factory=dict)
    fact_counts: dict[str, int] = Field(default_factory=dict)
    binding_counts: dict[str, int] = Field(default_factory=dict)
    gap_counts: dict[str, int] = Field(default_factory=dict)
    confidence_summary: CatalogConfidenceSummarySpec = Field(default_factory=CatalogConfidenceSummarySpec)
    last_scanned_at: Optional[str] = None
    stale_reason: Optional[str] = None
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("project_id")
    @classmethod
    def _project_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "project_id")

    @field_validator(
        "domain_tags",
        "system_tags",
        "subsystem_tags",
        "component_tags",
        "test_object_tags",
        "testbench_tags",
        "measurement_tags",
        "notes",
    )
    @classmethod
    def _list_values_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values

    @field_validator("artifact_counts", "fact_counts", "binding_counts", "gap_counts")
    @classmethod
    def _counts_nonnegative(cls, values: dict[str, int], info) -> dict[str, int]:
        for key, value in values.items():
            ensure_non_empty(key, info.field_name)
            if value < 0:
                raise ValueError(f"{info.field_name} values must be nonnegative")
        return values

    @model_validator(mode="after")
    def _project_valid(self) -> "CatalogProjectRecordSpec":
        if self.project_name is not None:
            ensure_non_empty(self.project_name, "project_name")
        if self.project_name_unknown_reason is not None:
            ensure_non_empty(self.project_name_unknown_reason, "project_name_unknown_reason")
        if self.project_evidence_registry is not None:
            ensure_non_empty(self.project_evidence_registry, "project_evidence_registry")
        if self.registry_missing_reason is not None:
            ensure_non_empty(self.registry_missing_reason, "registry_missing_reason")
        if self.superseded_by_project_id is not None:
            ensure_non_empty(self.superseded_by_project_id, "superseded_by_project_id")
        if self.rejected_reason is not None:
            ensure_non_empty(self.rejected_reason, "rejected_reason")
        if self.lifecycle_state == "superseded" and not self.superseded_by_project_id:
            raise ValueError("superseded projects require superseded_by_project_id")
        if self.lifecycle_state == "rejected" and not self.rejected_reason:
            raise ValueError("rejected projects require rejected_reason")
        _ensure_json_serializable(self.metadata, "catalog project metadata")
        return self


class DatabaseLifecycleArtifactsSpec(BaseModel):
    """Known file layout for one explicit local PhysicsGuard database."""

    model_config = ConfigDict(extra="forbid")

    database_readme: str = "DATABASE_README.md"
    database_status: str = "DATABASE_STATUS.md"
    database_policy: str = "database_policy.yaml"
    database_catalog: str = "database_catalog.yaml"
    database_history: str = "database_history.jsonl"
    database_maintenance_report: str = "database_maintenance_report.yaml"
    model_template_index: str = "model_template_index.yaml"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _artifacts_valid(self) -> "DatabaseLifecycleArtifactsSpec":
        for field_name in (
            "database_readme",
            "database_status",
            "database_policy",
            "database_catalog",
            "database_history",
            "database_maintenance_report",
            "model_template_index",
        ):
            ensure_non_empty(getattr(self, field_name), field_name)
        _ensure_json_serializable(self.metadata, "database lifecycle artifacts metadata")
        return self


class DatabasePolicySpec(BaseModel):
    """Explicit local database policy and lifecycle rules."""

    model_config = ConfigDict(extra="forbid")

    database_id: str
    database_name: Optional[str] = None
    schema_version: str = "1.0"
    physicsguard_version: Optional[str] = None
    physicsguard_repository: str = "https://github.com/liuyingxuvka/PhysicsGuard"
    scope_summary: Optional[str] = None
    maintainer: Optional[str] = None
    lifecycle_artifacts: DatabaseLifecycleArtifactsSpec = Field(default_factory=DatabaseLifecycleArtifactsSpec)
    require_explicit_user_authorization: bool = True
    require_apply_for_writes: bool = True
    forbid_raw_data_payloads: bool = True
    require_project_adoption_for_active: bool = True
    require_project_evidence_registry_for_active: bool = True
    require_no_blocking_project_gaps_for_active: bool = True
    require_validation_for_validated_state: bool = True
    require_model_library_for_reusable_state: bool = True
    default_project_state: DatabaseProjectLifecycleState = "candidate"
    allowed_project_states: list[DatabaseProjectLifecycleState] = Field(
        default_factory=lambda: [
            "candidate",
            "placeholder",
            "active_registered",
            "active_validated",
            "active_reusable",
            "blocked",
            "archived",
            "deprecated",
            "superseded",
            "rejected",
        ]
    )
    raw_data_policy: str = "Large raw datasets stay in source locations; database artifacts store only paths, hashes, summaries, and evidence references."
    write_policy: str = "Database lifecycle writes require explicit apply intent and history events."
    archive_policy: str = "Prefer archive, deprecate, supersede, or reject records instead of silent deletion."
    non_physicsguard_ai_guidance: str = "Read DATABASE_README.md, DATABASE_STATUS.md, database_policy.yaml, database_catalog.yaml, and database_maintenance_report.yaml before making claims."
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("database_id", "physicsguard_repository")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _policy_valid(self) -> "DatabasePolicySpec":
        if self.database_name is not None:
            ensure_non_empty(self.database_name, "database_name")
        if self.scope_summary is not None:
            ensure_non_empty(self.scope_summary, "scope_summary")
        if self.maintainer is not None:
            ensure_non_empty(self.maintainer, "maintainer")
        if self.default_project_state not in self.allowed_project_states:
            raise ValueError("default_project_state must be listed in allowed_project_states")
        _ensure_json_serializable(self.metadata, "database policy metadata")
        return self


class DatabaseCatalogSpec(BaseModel):
    """Database-level catalog for many PhysicsGuard projects."""

    model_config = ConfigDict(extra="forbid")

    catalog_id: str
    catalog_name: Optional[str] = None
    schema_version: str = "1.0"
    physicsguard_version: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    description: Optional[str] = None
    catalog_roots: list[str] = Field(default_factory=list)
    lifecycle_artifacts: DatabaseLifecycleArtifactsSpec = Field(default_factory=DatabaseLifecycleArtifactsSpec)
    database_policy: Optional[str] = None
    database_history: Optional[str] = None
    database_maintenance_report: Optional[str] = None
    model_template_index: Optional[str] = None
    projects: list[CatalogProjectRecordSpec] = Field(default_factory=list)
    model_library_indexes: list[CatalogModelLibraryReferenceSpec] = Field(default_factory=list)
    tag_dictionary: CatalogTagDictionarySpec = Field(default_factory=CatalogTagDictionarySpec)
    policies: CatalogPoliciesSpec = Field(default_factory=CatalogPoliciesSpec)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("catalog_id")
    @classmethod
    def _catalog_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "catalog_id")

    @field_validator("catalog_roots")
    @classmethod
    def _catalog_roots_not_empty(cls, values: list[str]) -> list[str]:
        for value in values:
            ensure_non_empty(value, "catalog_roots")
        return values

    @model_validator(mode="after")
    def _catalog_valid(self) -> "DatabaseCatalogSpec":
        _ensure_unique([item.project_id for item in self.projects], "project ids")
        library_ids = [item.library_id for item in self.model_library_indexes if item.library_id]
        _ensure_unique(library_ids, "model library ids")
        for field_name in (
            "database_policy",
            "database_history",
            "database_maintenance_report",
            "model_template_index",
        ):
            value = getattr(self, field_name)
            if value is not None:
                ensure_non_empty(value, field_name)
        _ensure_json_serializable(self.metadata, "database catalog metadata")
        return self


class DatabaseCatalogCandidateSpec(BaseModel):
    """Read-only scanner candidate for a database catalog."""

    model_config = ConfigDict(extra="forbid")

    path: str
    candidate_kind: CandidateKind
    reason: str
    registered: bool = False
    matched_id: Optional[str] = None


class DatabaseCatalogScanReportSpec(BaseModel):
    """Stable database catalog scanner report."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["database_catalog_scan"]
    status: Literal["pass", "partial", "fail"]
    ok: bool
    candidates: list[DatabaseCatalogCandidateSpec]
    findings: list[dict[str, Any]]
    summary: dict[str, Any]


class DatabaseCatalogGapSpec(BaseModel):
    """One database-level catalog gap."""

    model_config = ConfigDict(extra="forbid")

    gap_id: str
    severity: GapSeverity
    gap_type: str
    target: str
    reason: str
    project_id: Optional[str] = None
    required_by: list[str] = Field(default_factory=list)
    suggested_action: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("gap_id", "gap_type", "target", "reason")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "DatabaseCatalogGapSpec":
        _ensure_json_serializable(self.metadata, "database catalog gap metadata")
        return self


class DatabaseCatalogGapReportSpec(BaseModel):
    """Stable database gap-check report."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["database_catalog_gap_report"]
    status: Literal["pass", "partial", "fail"]
    ok: bool
    catalog_id: str
    blocking_gaps: list[DatabaseCatalogGapSpec] = Field(default_factory=list)
    review_gaps: list[DatabaseCatalogGapSpec] = Field(default_factory=list)
    optional_gaps: list[DatabaseCatalogGapSpec] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class DatabaseCatalogRefreshReportSpec(BaseModel):
    """Read-only catalog refresh summary."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["database_catalog_refresh"]
    status: Literal["pass", "partial", "fail"]
    ok: bool
    catalog_id: str
    refreshed_projects: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class DatabaseMapReportSpec(BaseModel):
    """AI-readable database-level map."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["database_catalog_map"]
    status: Literal["pass", "partial", "fail"]
    ok: bool
    catalog_id: str
    catalog_name: Optional[str] = None
    projects: list[dict[str, Any]] = Field(default_factory=list)
    model_libraries: list[dict[str, Any]] = Field(default_factory=list)
    indexes: dict[str, Any] = Field(default_factory=dict)
    gaps: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)


class DatabaseQueryReportSpec(BaseModel):
    """Safe database catalog query output."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["database_catalog_query"]
    status: Literal["pass", "partial", "fail"]
    ok: bool
    catalog_id: str
    filters: dict[str, Any] = Field(default_factory=dict)
    matches: list[dict[str, Any]] = Field(default_factory=list)
    gaps: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)


class DatabaseHistoryEventSpec(BaseModel):
    """Append-only lifecycle event for database maintenance."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: DatabaseHistoryEventType
    occurred_at: str
    actor: str = "PhysicsGuard AI"
    target_project_id: Optional[str] = None
    target_artifact: Optional[str] = None
    reason: Optional[str] = None
    dry_run: bool = False
    apply: bool = False
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    affected_paths: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_id", "occurred_at", "actor")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _history_valid(self) -> "DatabaseHistoryEventSpec":
        if self.target_project_id is not None:
            ensure_non_empty(self.target_project_id, "target_project_id")
        if self.target_artifact is not None:
            ensure_non_empty(self.target_artifact, "target_artifact")
        if self.reason is not None:
            ensure_non_empty(self.reason, "reason")
        for path in self.affected_paths:
            ensure_non_empty(path, "affected_paths")
        _ensure_json_serializable(self.metadata, "database history event metadata")
        return self


class DatabaseProjectIntakePlanSpec(BaseModel):
    """Plan for adding or updating one project in a database catalog."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["database_project_intake_plan"] = "database_project_intake_plan"
    database_root: str
    catalog_path: str
    project_id: str
    requested_state: DatabaseProjectLifecycleState = "candidate"
    project_root: Optional[str] = None
    project_name: Optional[str] = None
    project_evidence_registry: Optional[str] = None
    registry_missing_reason: Optional[str] = None
    project_adoption_record: Optional[str] = None
    project_adoption_missing_reason: Optional[str] = None
    admission_reason: Optional[str] = None
    domain_tags: list[str] = Field(default_factory=list)
    system_tags: list[str] = Field(default_factory=list)
    component_tags: list[str] = Field(default_factory=list)
    testbench_tags: list[str] = Field(default_factory=list)
    measurement_tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("database_root", "catalog_path", "project_id")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "DatabaseProjectIntakePlanSpec":
        _ensure_json_serializable(self.metadata, "database project intake plan metadata")
        return self


class DatabaseLifecycleOperationReportSpec(BaseModel):
    """Stable report for database lifecycle operations."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["database_lifecycle_operation"]
    operation: str
    status: Literal["pass", "partial", "fail", "dry_run"]
    ok: bool
    dry_run: bool = True
    applied: bool = False
    written_files: list[str] = Field(default_factory=list)
    skipped_files: list[str] = Field(default_factory=list)
    history_events: list[DatabaseHistoryEventSpec] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    next_actions: list[str] = Field(default_factory=list)


class DatabaseMaintenanceReportSpec(BaseModel):
    """Stable database lifecycle maintenance audit report."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["database_maintenance_report"]
    status: Literal["pass", "partial", "fail"]
    ok: bool
    database_root: str
    catalog_path: str
    policy_path: Optional[str] = None
    blocking_gaps: list[DatabaseCatalogGapSpec] = Field(default_factory=list)
    review_gaps: list[DatabaseCatalogGapSpec] = Field(default_factory=list)
    optional_gaps: list[DatabaseCatalogGapSpec] = Field(default_factory=list)
    project_summaries: list[dict[str, Any]] = Field(default_factory=list)
    lifecycle_artifacts: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    next_actions: list[str] = Field(default_factory=list)


class DatabaseModelTemplateRecordSpec(BaseModel):
    """Database-level model template or reusable model asset reference."""

    model_config = ConfigDict(extra="forbid")

    template_id: str
    template_name: Optional[str] = None
    template_path: Optional[str] = None
    model_library_entry_id: Optional[str] = None
    source_project_id: Optional[str] = None
    evidence_registry: Optional[str] = None
    validation_reports: list[str] = Field(default_factory=list)
    compatible_tags: list[str] = Field(default_factory=list)
    known_limits: list[str] = Field(default_factory=list)
    safe_claim_boundary: str = "Template is a starting point only; project-specific validation is still required."
    review_state: ReviewState = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("template_id", "safe_claim_boundary")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _template_valid(self) -> "DatabaseModelTemplateRecordSpec":
        if self.template_name is not None:
            ensure_non_empty(self.template_name, "template_name")
        if self.template_path is not None:
            ensure_non_empty(self.template_path, "template_path")
        for values, label in (
            (self.validation_reports, "validation_reports"),
            (self.compatible_tags, "compatible_tags"),
            (self.known_limits, "known_limits"),
        ):
            for value in values:
                ensure_non_empty(value, label)
        _ensure_json_serializable(self.metadata, "database model template metadata")
        return self


class DatabaseModelTemplateIndexSpec(BaseModel):
    """Database-level index of model templates and reusable model assets."""

    model_config = ConfigDict(extra="forbid")

    index_id: str
    database_id: Optional[str] = None
    schema_version: str = "1.0"
    physicsguard_version: Optional[str] = None
    model_library_indexes: list[CatalogModelLibraryReferenceSpec] = Field(default_factory=list)
    templates: list[DatabaseModelTemplateRecordSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("index_id")
    @classmethod
    def _index_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "index_id")

    @model_validator(mode="after")
    def _index_valid(self) -> "DatabaseModelTemplateIndexSpec":
        _ensure_unique([item.template_id for item in self.templates], "model template ids")
        _ensure_json_serializable(self.metadata, "database model template index metadata")
        return self


def _ensure_unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def _ensure_json_serializable(value: Any, field_name: str) -> None:
    try:
        json.dumps(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be JSON-serializable") from exc


__all__ = [
    "CandidateKind",
    "CatalogConfidenceSummarySpec",
    "CatalogFreshnessState",
    "CatalogModelLibraryReferenceSpec",
    "CatalogPoliciesSpec",
    "CatalogProjectRecordSpec",
    "CatalogTagDictionarySpec",
    "ConfidenceState",
    "DatabaseArchiveRecordSpec",
    "DatabaseCatalogCandidateSpec",
    "DatabaseCatalogGapReportSpec",
    "DatabaseCatalogGapSpec",
    "DatabaseCatalogRefreshReportSpec",
    "DatabaseCatalogScanReportSpec",
    "DatabaseCatalogSpec",
    "DatabaseHistoryEventSpec",
    "DatabaseHistoryEventType",
    "DatabaseLifecycleArtifactsSpec",
    "DatabaseLifecycleOperationReportSpec",
    "DatabaseMaintenanceReportSpec",
    "DatabaseMapReportSpec",
    "DatabaseModelTemplateIndexSpec",
    "DatabaseModelTemplateRecordSpec",
    "DatabasePolicySpec",
    "DatabaseProjectAdmissionSpec",
    "DatabaseProjectIntakePlanSpec",
    "DatabaseProjectLifecycleState",
    "DatabaseQueryReportSpec",
    "ProjectStatus",
    "ReuseState",
    "ValidationState",
]
