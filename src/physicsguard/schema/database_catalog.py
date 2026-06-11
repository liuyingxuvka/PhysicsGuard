"""Schemas for database-level project catalogs and maps."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.project_evidence import GapSeverity, ReviewState
from physicsguard.schema.variable import ensure_non_empty


ProjectStatus = Literal["draft", "active", "archived", "missing", "review_required", "deprecated"]
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
        _ensure_json_serializable(self.metadata, "catalog project metadata")
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
    "DatabaseCatalogCandidateSpec",
    "DatabaseCatalogGapReportSpec",
    "DatabaseCatalogGapSpec",
    "DatabaseCatalogRefreshReportSpec",
    "DatabaseCatalogScanReportSpec",
    "DatabaseCatalogSpec",
    "DatabaseMapReportSpec",
    "DatabaseQueryReportSpec",
    "ProjectStatus",
    "ReuseState",
    "ValidationState",
]
