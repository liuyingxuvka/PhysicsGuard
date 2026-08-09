"""Strict portable physical-DNA bundle and bounded query schemas.

The full bundle is a deterministic disk artifact.  AI-facing callers receive
only compact or one-id deep projections; the bundle itself is never the
default projection.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.physical_model_blueprint import (
    BlueprintTraceEdge,
    BlueprintTraceNode,
    ObjectDnaReadinessStatus,
    ObservedSourceMember,
    PhysicalBehaviorCase,
    PhysicalModelBlueprint,
    PhysicalModelBlueprintReview,
    SourceModelMapping,
    TargetInventoryAuthority,
    UnderstandingTarget,
    fingerprint_blueprint,
)


PHYSICAL_BLUEPRINT_EXPORT_BUNDLE_SCHEMA = (
    "physicsguard.physical-blueprint-export-bundle.v1"
)
PHYSICAL_BLUEPRINT_BUNDLE_QUERY_SCHEMA = (
    "physicsguard.physical-blueprint-bundle-query.v1"
)
MODULE_BEHAVIOR_CONTRACT_INDEX_SCHEMA = (
    "physicsguard.module-behavior-contract-index.v1"
)

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

PortableStatus = Literal[
    "pass",
    "incomplete",
    "stale",
    "blocked",
    "not_run",
]
PortableSelectorKind = Literal["status", "module", "element", "case", "impact", "reverse"]
PortableExecutionTrustStatus = Literal[
    "observed_at_export_unlicensed",
    "trusted_terminal_receipt",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    return normalized


def _stable_id(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name)
    if any(character.isspace() for character in normalized):
        raise ValueError(f"{field_name} cannot contain whitespace")
    return normalized


def _sha256(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name).lower()
    if not SHA256_PATTERN.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase sha256 digest")
    return normalized


def canonical_portable_json(value: Any) -> str:
    """Canonical JSON for bundle identity while preserving list order."""

    if isinstance(value, BaseModel):
        # Required explicit-empty fields (for example review.first_gap_id=None)
        # must survive materialization so the strict current schema reloads.
        value = value.model_dump(mode="json", exclude_none=False)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def canonical_portable_bytes(value: Any) -> bytes:
    return canonical_portable_json(value).encode("utf-8")


def portable_fingerprint(value: Any, *, fingerprint_field: str) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude_none=True)
    else:
        payload = dict(value)
    payload.pop(fingerprint_field, None)
    return hashlib.sha256(canonical_portable_bytes(_drop_none(payload))).hexdigest()


def _drop_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _drop_none(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [_drop_none(item) for item in value]
    return value


class PortableCoverageLayer(_StrictModel):
    layer_id: Literal[
        "structural_inventory",
        "scenario_role",
        "domain_semantics",
        "independent_review",
        "claim_licensing",
    ]
    status: PortableStatus
    covered_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    first_gap_code: str | None = None

    @field_validator("first_gap_code")
    @classmethod
    def _gap_valid(cls, value: str | None) -> str | None:
        return None if value is None else _stable_id(value, "first_gap_code")

    @model_validator(mode="after")
    def _counts_consistent(self) -> "PortableCoverageLayer":
        if self.covered_count > self.total_count:
            raise ValueError("covered_count cannot exceed total_count")
        if self.status == "pass" and self.covered_count != self.total_count:
            raise ValueError("passing coverage requires the complete denominator")
        if self.status != "pass" and self.total_count and self.covered_count < self.total_count and self.first_gap_code is None:
            raise ValueError("incomplete coverage requires first_gap_code")
        return self


class PortableModuleBehaviorContract(_StrictModel):
    module_type: str
    category: str
    behavior_contract: dict[str, Any]
    dimension_statuses: dict[str, PortableStatus]
    scenario_role_status: Literal["resolved", "unresolved"]
    direction_scope: str | None = None
    relation_directionality: str | None = None
    first_gap: dict[str, Any] | None = None
    physical_claim_licensed: bool
    contract_fingerprint: str

    @field_validator("module_type", "category")
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("direction_scope", "relation_directionality")
    @classmethod
    def _optional_identity_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("contract_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "contract_fingerprint")

    @model_validator(mode="after")
    def _contract_consistent(self) -> "PortableModuleBehaviorContract":
        embedded = self.behavior_contract.get("contract_fingerprint")
        if embedded != self.contract_fingerprint:
            raise ValueError("module behavior contract fingerprint does not match its payload")
        if self.scenario_role_status == "resolved" and not self.direction_scope:
            raise ValueError("resolved scenario roles require an exact direction_scope")
        return self


class ModuleBehaviorContractIndex(_StrictModel):
    schema_version: Literal[
        "physicsguard.module-behavior-contract-index.v1"
    ] = MODULE_BEHAVIOR_CONTRACT_INDEX_SCHEMA
    checker_identity: str
    live_registry_fingerprint: str
    contracts: list[PortableModuleBehaviorContract]
    coverage_layers: list[PortableCoverageLayer]
    first_gap_code: str | None
    index_fingerprint: str

    @field_validator("checker_identity", "first_gap_code")
    @classmethod
    def _identity_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("live_registry_fingerprint", "index_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str, info) -> str:
        return _sha256(value, info.field_name)

    @model_validator(mode="after")
    def _index_consistent(self) -> "ModuleBehaviorContractIndex":
        module_types = [item.module_type for item in self.contracts]
        if len(module_types) != len(set(module_types)):
            raise ValueError("module behavior contracts require unique module types")
        layer_ids = [item.layer_id for item in self.coverage_layers]
        expected = [
            "structural_inventory",
            "scenario_role",
            "domain_semantics",
            "independent_review",
            "claim_licensing",
        ]
        if layer_ids != expected:
            raise ValueError("module coverage layers must use the stable ordered five-layer spine")
        if any(item.total_count != len(self.contracts) for item in self.coverage_layers):
            raise ValueError("every module coverage layer must retain the exact contract denominator")
        if self.index_fingerprint != portable_fingerprint(
            self,
            fingerprint_field="index_fingerprint",
        ):
            raise ValueError("module behavior contract index fingerprint is stale or invalid")
        return self


class PortableElementBehaviorContract(_StrictModel):
    contract_id: str
    element_id: str
    input_port_ids: list[str]
    pre_state_port_ids: list[str]
    output_port_ids: list[str]
    post_state_port_ids: list[str]
    effect_port_ids: list[str]
    semantic_ids: list[str]
    preconditions: list[str]
    postconditions: list[str]
    protected_failures: list[str]
    termination_semantic_ids: list[str]
    oracle_binding_ids: list[str]
    behavior_cases: list[PhysicalBehaviorCase]
    status: PortableStatus
    first_gap_code: str | None
    contract_fingerprint: str

    @field_validator("contract_id", "element_id", "first_gap_code")
    @classmethod
    def _identity_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("contract_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "contract_fingerprint")

    @model_validator(mode="after")
    def _contract_consistent(self) -> "PortableElementBehaviorContract":
        if self.status == "pass" and self.first_gap_code is not None:
            raise ValueError("passing element behavior contract cannot contain a first gap")
        if self.status != "pass" and self.first_gap_code is None:
            raise ValueError("non-passing element behavior contract requires a first gap")
        if self.contract_fingerprint != portable_fingerprint(
            self,
            fingerprint_field="contract_fingerprint",
        ):
            raise ValueError("element behavior contract fingerprint is stale or invalid")
        return self


class PortableGraph(_StrictModel):
    nodes: list[BlueprintTraceNode]
    edges: list[BlueprintTraceEdge]
    aliases: dict[str, list[str]]
    graph_fingerprint: str

    @field_validator("graph_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "graph_fingerprint")

    @model_validator(mode="after")
    def _graph_consistent(self) -> "PortableGraph":
        node_ids = [item.node_id for item in self.nodes]
        edge_ids = [item.edge_id for item in self.edges]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("portable graph node ids must be unique")
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("portable graph edge ids must be unique")
        if self.graph_fingerprint != portable_fingerprint(
            self,
            fingerprint_field="graph_fingerprint",
        ):
            raise ValueError("portable graph fingerprint is stale or invalid")
        return self


class PortableEvidenceManifestEntry(_StrictModel):
    manifest_id: str
    artifact_kind: str
    subject_id: str
    subject_revision: str
    sha256: str
    locator_kind: Literal["repo_path", "external_uri"]
    locator: str
    content_mode: Literal["identity_only"] = "identity_only"
    status: PortableStatus
    claim_boundary: str

    @field_validator("manifest_id", "artifact_kind", "subject_id", "subject_revision")
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("sha256")
    @classmethod
    def _sha_valid(cls, value: str) -> str:
        return _sha256(value, "sha256")

    @field_validator("locator", "claim_boundary")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)


class PortableEvidenceManifest(_StrictModel):
    entries: list[PortableEvidenceManifestEntry]
    manifest_fingerprint: str

    @field_validator("manifest_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "manifest_fingerprint")

    @model_validator(mode="after")
    def _manifest_consistent(self) -> "PortableEvidenceManifest":
        ids = [item.manifest_id for item in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("portable evidence manifest ids must be unique")
        if self.manifest_fingerprint != portable_fingerprint(
            self,
            fingerprint_field="manifest_fingerprint",
        ):
            raise ValueError("portable evidence manifest fingerprint is stale or invalid")
        return self


class PhysicalBlueprintExportBundle(_StrictModel):
    schema_version: Literal[
        "physicsguard.physical-blueprint-export-bundle.v1"
    ] = PHYSICAL_BLUEPRINT_EXPORT_BUNDLE_SCHEMA
    bundle_id: str
    target_system_id: str
    subject_revision: str
    blueprint: PhysicalModelBlueprint
    target_inventory_authority: TargetInventoryAuthority
    review: PhysicalModelBlueprintReview
    understanding_target: UnderstandingTarget
    declared_consistency_status: Literal["pass", "incomplete", "stale", "blocked"]
    object_dna_readiness: ObjectDnaReadinessStatus
    source_census: list[ObservedSourceMember]
    source_mappings: list[SourceModelMapping]
    element_behavior_contracts: list[PortableElementBehaviorContract]
    module_behavior_contract_index: ModuleBehaviorContractIndex | None
    relation_graph: PortableGraph
    evidence_manifest: PortableEvidenceManifest
    source_fingerprints: dict[str, str]
    execution_trust_status: PortableExecutionTrustStatus
    first_gap_code: str | None
    safe_claim: str
    claim_boundary: str
    bundle_fingerprint: str

    @field_validator("bundle_id", "target_system_id", "subject_revision", "first_gap_code")
    @classmethod
    def _identity_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("source_fingerprints")
    @classmethod
    def _source_fingerprints_valid(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("source_fingerprints cannot be empty")
        return {key: _sha256(digest, f"source_fingerprints.{key}") for key, digest in value.items()}

    @field_validator("safe_claim", "claim_boundary")
    @classmethod
    def _claim_valid(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)

    @field_validator("bundle_fingerprint")
    @classmethod
    def _bundle_fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "bundle_fingerprint")

    @model_validator(mode="after")
    def _bundle_consistent(self) -> "PhysicalBlueprintExportBundle":
        if self.target_system_id != self.blueprint.target.target_system_id:
            raise ValueError("bundle target_system_id does not match blueprint")
        if self.subject_revision != self.blueprint.target.subject_revision:
            raise ValueError("bundle subject_revision does not match blueprint")
        if self.review.blueprint_fingerprint != fingerprint_blueprint(self.blueprint):
            raise ValueError("bundle review does not belong to the embedded blueprint")
        if self.understanding_target != self.blueprint.understanding_target:
            raise ValueError("bundle understanding target does not match blueprint")
        if self.declared_consistency_status != self.review.declared_consistency_status:
            raise ValueError("bundle declared-consistency status does not match review")
        if self.object_dna_readiness != self.review.object_dna_readiness:
            raise ValueError("bundle object-DNA readiness does not match review")
        if self.source_census != self.review.source_census:
            raise ValueError("bundle source census must equal the frozen review projection")
        if self.source_mappings != self.blueprint.source_mappings:
            raise ValueError("bundle source mappings must equal the frozen blueprint mappings")
        if self.execution_trust_status == "trusted_terminal_receipt":
            raise ValueError(
                "trusted terminal execution requires a signed producer contract that this bundle schema does not yet carry"
            )
        if self.review.target_system_id != self.target_system_id or self.review.subject_revision != self.subject_revision:
            raise ValueError("bundle review target identity does not match blueprint")
        authority = self.target_inventory_authority
        if authority.target_system_id != self.target_system_id or authority.subject_revision != self.subject_revision:
            raise ValueError("bundle target inventory authority belongs to another target")
        if authority.authority_fingerprint != self.review.target_inventory_authority_fingerprint:
            raise ValueError("bundle review does not bind the embedded target inventory authority")
        element_ids = [item.element_id for item in self.element_behavior_contracts]
        expected_element_ids = [item.element_id for item in self.blueprint.elements]
        if element_ids != expected_element_ids:
            raise ValueError("element behavior contracts must cover blueprint elements in canonical order")
        if self.bundle_fingerprint != portable_fingerprint(
            self,
            fingerprint_field="bundle_fingerprint",
        ):
            raise ValueError("portable bundle fingerprint is stale or invalid")
        return self


class PortableBundleQueryGap(_StrictModel):
    code: str
    status: PortableStatus
    target_ids: list[str] = Field(default_factory=list)
    message: str
    claim_boundary: str

    @field_validator("code")
    @classmethod
    def _code_valid(cls, value: str) -> str:
        return _stable_id(value, "code")

    @field_validator("message", "claim_boundary")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)


class PortableBundleQueryResult(_StrictModel):
    schema_version: Literal[
        "physicsguard.physical-blueprint-bundle-query.v1"
    ] = PHYSICAL_BLUEPRINT_BUNDLE_QUERY_SCHEMA
    bundle_fingerprint: str
    query_kind: PortableSelectorKind
    query_id: str | None
    status: PortableStatus
    source_review_status: Literal["pass", "incomplete", "stale", "blocked"]
    deepest_licensed_layer: str | None
    coverage_layers: list[PortableCoverageLayer]
    first_gap_code: str | None
    safe_claim: str
    claim_boundary: str
    payload: dict[str, Any]
    gaps: list[PortableBundleQueryGap]
    bundle_canonical_bytes: int = Field(ge=1)
    projection_canonical_bytes: int = Field(ge=1)
    projection_byte_limit: int = Field(ge=1)

    @field_validator("bundle_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "bundle_fingerprint")

    @field_validator("query_id", "first_gap_code")
    @classmethod
    def _identity_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("safe_claim", "claim_boundary")
    @classmethod
    def _claim_valid(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)

    @model_validator(mode="after")
    def _query_consistent(self) -> "PortableBundleQueryResult":
        if self.query_kind == "status" and self.query_id is not None:
            raise ValueError("status projection cannot carry a deep query id")
        if self.query_kind != "status" and self.query_id is None:
            raise ValueError("deep bundle queries require exactly one explicit id")
        return self


__all__ = [
    "MODULE_BEHAVIOR_CONTRACT_INDEX_SCHEMA",
    "PHYSICAL_BLUEPRINT_BUNDLE_QUERY_SCHEMA",
    "PHYSICAL_BLUEPRINT_EXPORT_BUNDLE_SCHEMA",
    "ModuleBehaviorContractIndex",
    "PhysicalBlueprintExportBundle",
    "PortableBundleQueryGap",
    "PortableBundleQueryResult",
    "PortableCoverageLayer",
    "PortableElementBehaviorContract",
    "PortableEvidenceManifest",
    "PortableEvidenceManifestEntry",
    "PortableGraph",
    "PortableModuleBehaviorContract",
    "PortableSelectorKind",
    "PortableStatus",
    "canonical_portable_bytes",
    "canonical_portable_json",
    "portable_fingerprint",
]
