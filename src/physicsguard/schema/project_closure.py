"""Schemas for project-level PhysicsGuard closure reports."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_non_empty


ClaimScope = Literal[
    "project_ready",
    "analysis_ready",
    "validation_ready",
    "validated_reuse_ready",
    "fault_localization_ready",
]
ClosureStatus = Literal["passed", "partial", "downgraded", "blocked"]
FindingSeverity = Literal["error", "warning", "info"]


class ProjectClosureRequiredChecksSpec(BaseModel):
    """Which route checks must be present for this closure."""

    model_config = ConfigDict(extra="forbid")

    project_audit: bool = True
    evidence_check: bool = True
    evidence_gap_check: bool = True
    evidence_map: bool = True
    test_contracts: bool = False
    validation: bool = False
    model_library: bool = False
    hierarchy_closure: bool = False


class ProjectClosureAuditPairSpec(BaseModel):
    """Optional hierarchy audit evidence used for fault-localization closure."""

    model_config = ConfigDict(extra="forbid")

    audit_file: str
    observed_file: str
    label: Optional[str] = None

    @field_validator("audit_file", "observed_file")
    @classmethod
    def _path_not_empty(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)


class ProjectClosurePlanSpec(BaseModel):
    """Plan for deriving one project-level closure report."""

    model_config = ConfigDict(extra="forbid")

    closure_id: str
    claim_scope: ClaimScope = "project_ready"
    project_root: str = "."
    evidence_registry: Optional[str] = None
    evidence_bundle_ids: list[str] = Field(default_factory=list)
    test_contracts: list[str] = Field(default_factory=list)
    validation_plans: list[str] = Field(default_factory=list)
    model_library_indexes: list[str] = Field(default_factory=list)
    audit_pairs: list[ProjectClosureAuditPairSpec] = Field(default_factory=list)
    required_checks: ProjectClosureRequiredChecksSpec = Field(default_factory=ProjectClosureRequiredChecksSpec)
    allow_review_gaps: bool = True
    allow_optional_gaps: bool = True
    allow_skipped_required_checks: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("closure_id")
    @classmethod
    def _closure_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "closure_id")

    @field_validator(
        "evidence_bundle_ids",
        "test_contracts",
        "validation_plans",
        "model_library_indexes",
    )
    @classmethod
    def _list_values_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values

    @model_validator(mode="after")
    def _claim_scope_requirements(self) -> "ProjectClosurePlanSpec":
        if self.claim_scope in {"validation_ready", "validated_reuse_ready"} and not self.required_checks.validation:
            raise ValueError("validation_ready and validated_reuse_ready closure require validation checks")
        if self.claim_scope == "validated_reuse_ready" and not self.required_checks.model_library:
            raise ValueError("validated_reuse_ready closure requires model_library checks")
        if self.claim_scope == "fault_localization_ready" and not self.required_checks.hierarchy_closure:
            raise ValueError("fault_localization_ready closure requires hierarchy_closure checks")
        return self


class ProjectClosureFindingSpec(BaseModel):
    """One finding in a project closure report."""

    model_config = ConfigDict(extra="forbid")

    severity: FindingSeverity
    type: str
    message: str
    source: str
    target: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type", "message", "source")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)


class ProjectClosureSkippedCheckSpec(BaseModel):
    """Required closure input that was not run."""

    model_config = ConfigDict(extra="forbid")

    check: str
    reason: str
    required: bool = True

    @field_validator("check", "reason")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)


class ProjectClosureReportSpec(BaseModel):
    """Stable project closure report schema."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["physicsguard_project_closure_report"]
    closure_id: str
    claim_scope: ClaimScope
    closure_status: ClosureStatus
    ok: bool
    checked_inputs: list[dict[str, Any]] = Field(default_factory=list)
    blocking_findings: list[ProjectClosureFindingSpec] = Field(default_factory=list)
    review_findings: list[ProjectClosureFindingSpec] = Field(default_factory=list)
    optional_findings: list[ProjectClosureFindingSpec] = Field(default_factory=list)
    skipped_checks: list[ProjectClosureSkippedCheckSpec] = Field(default_factory=list)
    safe_claim: str
    unsafe_claim_boundary: str
    next_actions: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)

    @field_validator("closure_id", "safe_claim", "unsafe_claim_boundary")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)


__all__ = [
    "ClaimScope",
    "ClosureStatus",
    "FindingSeverity",
    "ProjectClosureAuditPairSpec",
    "ProjectClosureFindingSpec",
    "ProjectClosurePlanSpec",
    "ProjectClosureReportSpec",
    "ProjectClosureRequiredChecksSpec",
    "ProjectClosureSkippedCheckSpec",
]
