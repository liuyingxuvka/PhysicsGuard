"""Schemas for FlowGuard-grade PhysicsGuard evidence mesh reports."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.project_closure import ClaimScope, FindingSeverity
from physicsguard.schema.variable import ensure_non_empty


EvidenceStatus = Literal["pass", "partial", "fail", "blocked", "skipped", "not_run"]
FreshnessStatus = Literal["current", "stale", "unknown", "scoped"]
RouteId = Literal[
    "model_mesh",
    "model_test_alignment",
    "contract_exhaustion",
    "test_mesh",
    "field_lifecycle",
    "risk_ledger",
]
TestScope = Literal["external", "mixed", "internal"]
RiskDecision = Literal["pass", "partial", "blocked"]


class MeshPartitionItemSpec(BaseModel):
    """Parent-space item owned by a parent, child, shared kernel, or scoped boundary."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    item_type: str
    owner_model_id: Optional[str] = None
    ownership: Literal["parent", "child", "shared_kernel", "read_only", "bridge", "out_of_scope"]
    scoped_out_reason: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("item_id", "item_type")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _ownership_valid(self) -> "MeshPartitionItemSpec":
        if self.ownership == "out_of_scope" and not self.scoped_out_reason:
            raise ValueError("out_of_scope partition item requires scoped_out_reason")
        if self.ownership != "out_of_scope" and not self.owner_model_id:
            raise ValueError("in-scope partition item requires owner_model_id")
        return self


class ChildModelEvidenceSpec(BaseModel):
    """Current evidence emitted by a child model boundary."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    model_id: str
    parent_model_id: Optional[str] = None
    risk_boundary: str
    status: EvidenceStatus = "pass"
    freshness: FreshnessStatus = "current"
    inputs_accepted: list[str] = Field(default_factory=list)
    outputs_emitted: list[str] = Field(default_factory=list)
    state_owned: list[str] = Field(default_factory=list)
    side_effects_owned: list[str] = Field(default_factory=list)
    contracts_out: list[str] = Field(default_factory=list)
    result_ref: Optional[str] = None
    scoped_reason: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence_id", "model_id", "risk_boundary")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator(
        "inputs_accepted",
        "outputs_emitted",
        "state_owned",
        "side_effects_owned",
        "contracts_out",
    )
    @classmethod
    def _list_values_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values

    @model_validator(mode="after")
    def _status_valid(self) -> "ChildModelEvidenceSpec":
        if self.freshness == "scoped" and not self.scoped_reason:
            raise ValueError("scoped child evidence requires scoped_reason")
        return self


class ParentModelMeshSpec(BaseModel):
    """Parent mesh row that consumes current child model evidence."""

    model_config = ConfigDict(extra="forbid")

    model_id: str
    claim_boundary: str
    required_child_evidence_ids: list[str] = Field(default_factory=list)
    consumed_child_evidence_ids: list[str] = Field(default_factory=list)
    partition_items: list[MeshPartitionItemSpec] = Field(default_factory=list)
    status: EvidenceStatus = "pass"
    freshness: FreshnessStatus = "current"
    result_ref: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("model_id", "claim_boundary")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("required_child_evidence_ids", "consumed_child_evidence_ids")
    @classmethod
    def _list_values_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values


class ModelObligationSpec(BaseModel):
    """Model-declared behavior that must bind to code and tests."""

    model_config = ConfigDict(extra="forbid")

    obligation_id: str
    description: str
    required: bool = True
    route_source: RouteId | Literal["core", "project_evidence", "project_closure"] = "core"
    required_test_kinds: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("obligation_id", "description")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)


class CodeContractSpec(BaseModel):
    """Owner code boundary that implements model obligations."""

    model_config = ConfigDict(extra="forbid")

    contract_id: str
    path: str
    symbol: str
    model_obligation_ids: list[str]
    required: bool = True
    status: EvidenceStatus = "pass"
    exact_boundary: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("contract_id", "path", "symbol")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("model_obligation_ids")
    @classmethod
    def _list_values_not_empty(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("code contract requires at least one model obligation")
        for value in values:
            ensure_non_empty(value, "model_obligation_ids")
        return values


class EvidenceMeshTestEvidenceSpec(BaseModel):
    """Test evidence row binding obligations and code contracts."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    test_name: str
    path: str
    status: EvidenceStatus = "pass"
    freshness: FreshnessStatus = "current"
    scope: TestScope = "external"
    covers_obligation_ids: list[str] = Field(default_factory=list)
    covers_code_contract_ids: list[str] = Field(default_factory=list)
    result_ref: Optional[str] = None
    progress_only: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence_id", "test_name", "path")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("covers_obligation_ids", "covers_code_contract_ids")
    @classmethod
    def _list_values_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values


class ContractExhaustionCaseSpec(BaseModel):
    """Generated finite bad-case receipt."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    source_boundary: str
    generated: bool = True
    oracle: str
    owner_test_evidence_id: str
    downstream_routes: list[RouteId] = Field(default_factory=list)
    required: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("case_id", "source_boundary", "oracle", "owner_test_evidence_id")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)


class TestSuiteEvidenceSpec(BaseModel):
    """Parent or child test mesh evidence."""

    model_config = ConfigDict(extra="forbid")

    suite_id: str
    suite_kind: Literal["parent", "child"]
    status: EvidenceStatus = "pass"
    freshness: FreshnessStatus = "current"
    child_suite_ids: list[str] = Field(default_factory=list)
    consumed_child_suite_ids: list[str] = Field(default_factory=list)
    required_cell_ids: list[str] = Field(default_factory=list)
    result_ref: Optional[str] = None
    progress_only: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("suite_id")
    @classmethod
    def _suite_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "suite_id")

    @field_validator("child_suite_ids", "consumed_child_suite_ids", "required_cell_ids")
    @classmethod
    def _list_values_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values


class FieldLifecycleRowSpec(BaseModel):
    """Behavior-bearing field lifecycle row."""

    model_config = ConfigDict(extra="forbid")

    field_id: str
    owner: str
    lifecycle: Literal["active", "added", "renamed", "deprecated", "removed", "preserved"]
    behavior_bearing: bool = False
    projection_target: Optional[str] = None
    downstream_evidence_ids: list[str] = Field(default_factory=list)
    old_field_disposition: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("field_id", "owner")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _field_valid(self) -> "FieldLifecycleRowSpec":
        if self.behavior_bearing and not self.projection_target:
            raise ValueError("behavior-bearing field requires projection_target")
        if self.lifecycle in {"renamed", "deprecated", "removed", "preserved"} and not self.old_field_disposition:
            raise ValueError("old or compatibility field requires old_field_disposition")
        return self


class RiskLedgerRowSpec(BaseModel):
    """Final claim row that consumes route receipts."""

    model_config = ConfigDict(extra="forbid")

    risk_id: str
    claim_scope: ClaimScope
    decision: RiskDecision = "pass"
    consumed_routes: list[RouteId]
    consumed_evidence_ids: list[str] = Field(default_factory=list)
    freshness: FreshnessStatus = "current"
    safe_claim: str
    unsafe_claim_boundary: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("risk_id", "safe_claim", "unsafe_claim_boundary")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("consumed_routes")
    @classmethod
    def _routes_not_empty(cls, values: list[RouteId]) -> list[RouteId]:
        if not values:
            raise ValueError("risk ledger row requires consumed_routes")
        return values


class EvidenceMeshSpec(BaseModel):
    """PhysicsGuard evidence mesh input artifact."""

    model_config = ConfigDict(extra="forbid")

    mesh_id: str
    claim_scope: ClaimScope
    required_routes: list[RouteId] = Field(
        default_factory=lambda: [
            "model_mesh",
            "model_test_alignment",
            "contract_exhaustion",
            "test_mesh",
            "field_lifecycle",
            "risk_ledger",
        ]
    )
    parent_models: list[ParentModelMeshSpec] = Field(default_factory=list)
    child_model_evidence: list[ChildModelEvidenceSpec] = Field(default_factory=list)
    model_obligations: list[ModelObligationSpec] = Field(default_factory=list)
    code_contracts: list[CodeContractSpec] = Field(default_factory=list)
    test_evidence: list[EvidenceMeshTestEvidenceSpec] = Field(default_factory=list)
    contract_cases: list[ContractExhaustionCaseSpec] = Field(default_factory=list)
    test_suites: list[TestSuiteEvidenceSpec] = Field(default_factory=list)
    field_lifecycle: list[FieldLifecycleRowSpec] = Field(default_factory=list)
    risk_ledger: list[RiskLedgerRowSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("mesh_id")
    @classmethod
    def _mesh_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "mesh_id")

    @model_validator(mode="after")
    def _unique_ids(self) -> "EvidenceMeshSpec":
        _ensure_unique([item.model_id for item in self.parent_models], "parent model ids")
        _ensure_unique([item.evidence_id for item in self.child_model_evidence], "child evidence ids")
        _ensure_unique([item.obligation_id for item in self.model_obligations], "model obligation ids")
        _ensure_unique([item.contract_id for item in self.code_contracts], "code contract ids")
        _ensure_unique([item.evidence_id for item in self.test_evidence], "test evidence ids")
        _ensure_unique([item.case_id for item in self.contract_cases], "contract case ids")
        _ensure_unique([item.suite_id for item in self.test_suites], "test suite ids")
        _ensure_unique([item.field_id for item in self.field_lifecycle], "field ids")
        _ensure_unique([item.risk_id for item in self.risk_ledger], "risk ledger ids")
        return self


class EvidenceMeshFindingSpec(BaseModel):
    """One evidence mesh review finding."""

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


class EvidenceMeshReportSpec(BaseModel):
    """Stable evidence mesh review report."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["physicsguard_evidence_mesh_report"]
    mesh_id: str
    claim_scope: ClaimScope
    status: Literal["pass", "partial", "fail"]
    ok: bool
    route_status: dict[str, str] = Field(default_factory=dict)
    blocking_findings: list[EvidenceMeshFindingSpec] = Field(default_factory=list)
    review_findings: list[EvidenceMeshFindingSpec] = Field(default_factory=list)
    optional_findings: list[EvidenceMeshFindingSpec] = Field(default_factory=list)
    safe_claim: str
    unsafe_claim_boundary: str
    next_actions: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)

    @field_validator("mesh_id", "safe_claim", "unsafe_claim_boundary")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)


def _ensure_unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


__all__ = [
    "ChildModelEvidenceSpec",
    "CodeContractSpec",
    "ContractExhaustionCaseSpec",
    "EvidenceMeshFindingSpec",
    "EvidenceMeshReportSpec",
    "EvidenceMeshSpec",
    "EvidenceMeshTestEvidenceSpec",
    "EvidenceStatus",
    "FieldLifecycleRowSpec",
    "FreshnessStatus",
    "MeshPartitionItemSpec",
    "ModelObligationSpec",
    "ParentModelMeshSpec",
    "RiskDecision",
    "RiskLedgerRowSpec",
    "RouteId",
    "TestScope",
    "TestSuiteEvidenceSpec",
]
