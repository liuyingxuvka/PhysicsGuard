"""Canonical provider-neutral physical-model blueprint contracts.

The schema captures PhysicsGuard-owned physical meaning.  It deliberately does
not model generic software structure or depend on FlowGuard at runtime.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import PurePosixPath
from typing import Any, Literal, Mapping
from urllib.parse import parse_qsl, urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_non_empty


PHYSICAL_MODEL_BLUEPRINT_SCHEMA = "physicsguard.physical-model-blueprint.v1"
PHYSICAL_MODEL_BLUEPRINT_REVIEW_SCHEMA = "physicsguard.physical-model-blueprint-review.v1"
PHYSICAL_BLUEPRINT_PROJECTION_SCHEMA = "physicsguard.physical-blueprint-projection.v1"
TARGET_INVENTORY_AUTHORITY_SCHEMA = "physicsguard.target-inventory-authority.v1"
PROVIDER_REGISTRY_SCHEMA = "physicsguard.provider-registry.v1"
TARGET_MATERIAL_SCHEMA = "physicsguard.target-material.v1"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

TargetKind = Literal[
    "physical_system",
    "experiment",
    "testbench",
    "simulation_model",
    "physical_workflow",
    "mixed_physical_workflow",
]
ProviderStatus = Literal["current", "stale", "unsupported", "blocked"]
InventoryDisposition = Literal["modeled", "supporting", "excluded", "unsupported", "unresolved"]
InventoryMemberKind = Literal[
    "physical_element",
    "interface",
    "module",
    "equation",
    "variable",
    "parameter",
    "file",
    "dataset",
    "test",
    "observation",
    "evidence",
    "oracle",
    "resource",
    "provider_artifact",
    "workflow",
]
PhysicalElementKind = Literal[
    "system",
    "subsystem",
    "component",
    "experiment",
    "testbench",
    "model",
    "physical_workflow",
    "helper",
]
PortDirection = Literal["input", "output", "state", "effect"]
SemanticKind = Literal[
    "equation",
    "residual",
    "constraint",
    "state_update",
    "parameter",
    "assumption",
    "invariant",
    "validity_limit",
    "protected_failure",
    "conservation_law",
    "constitutive_relation",
    "conversion",
    "guarantee",
    "operating_envelope",
    "termination",
]
MappingKind = Literal[
    "parent_input_to_child_input",
    "parent_state_to_child_input",
    "sibling_output_to_child_input",
    "external_input_to_child_input",
    "child_output_to_parent_output",
    "child_output_to_parent_state",
    "child_state_to_parent_state",
    "child_effect_to_parent_effect",
]
ContributionKind = Literal["preserves", "aggregates", "constrains", "weakens"]
BindingKind = Literal[
    "implementation",
    "workflow",
    "source",
    "test",
    "dataset",
    "observation",
    "evidence",
    "oracle",
    "resource",
    "project_record",
    "model_library",
    "hierarchy",
    "validation",
    "model_revision",
]
ValidationMode = Literal[
    "pointwise",
    "temporal_stateful",
    "conservation_residual",
    "interface_unit",
    "boundary_invalid_region",
    "cross_coupling",
]
NativeSchemaKind = Literal[
    "generic_artifact",
    "fmi_observation_request",
    "hierarchical_audit",
    "project_evidence_registry",
    "project_profile",
    "signal_mapping_ledger",
    "data_file_manifest",
    "logical_dataset_record",
    "test_file_contract",
    "test_file_project_index",
    "validation_depth_receipt",
    "validation_adequacy_receipt",
    "model_validation_plan",
    "model_dataset_validation_report",
    "model_library_index",
    "native_depth_receipt",
    "candidate_model_revision",
    "evidence_mesh",
]
ReviewStatus = Literal["pass", "incomplete", "stale", "blocked"]
BlueprintLayerName = Literal[
    "target_inventory",
    "hierarchy_ownership",
    "typed_interfaces",
    "independent_physical_semantics",
    "parent_child_refinement",
    "native_model_code_test",
    "resource_oracle",
    "static_blueprint",
]
ProjectionKind = Literal["summary", "affected", "reverse_trace", "full"]
AuthorityResultStatus = Literal["pass", "unverified", "stale", "blocked", "failed"]
AuthorityTerminalStatus = Literal["success", "unverified", "stale", "blocked", "failed"]
ProviderExecutionMode = Literal["local", "external"]
BehaviorCaseKind = Literal["positive", "boundary", "counterexample", "protected_failure"]
BehaviorCaseStatus = Literal["pass", "stale", "blocked", "not_run"]
UnderstandingTarget = Literal["declared_consistency", "object_dna"]
ObjectDnaReadinessStatus = Literal["pass", "incomplete", "stale", "blocked", "not_requested"]
SourceMappingRelation = Literal["realizes", "defines", "exercises", "supports", "dispositioned"]
FmiSourceStateRole = Literal[
    "time",
    "parameter",
    "constant",
    "continuous_state",
    "continuous_derivative",
]
PortStateRole = Literal[
    "parameter_input",
    "constant_input",
    "state_storage",
    "state_read",
    "derivative_output",
    "event_post_state",
]
QuantityRelation = Literal["identity", "stateful_alias"]
UnitConversionKind = Literal["identity", "dimensionless_identity", "affine"]
SemanticSelectorStatus = Literal["verified", "unresolved"]
NativeBehaviorCaseDisposition = Literal["required", "dispositioned"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _required_text(value: str, field_name: str) -> str:
    return ensure_non_empty(value, field_name).strip()


def _stable_id(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name)
    if any(character.isspace() for character in normalized):
        raise ValueError(f"{field_name} cannot contain whitespace")
    return normalized


def _sha256(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name).lower()
    if not SHA256_PATTERN.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase 64-character sha256 digest")
    return normalized


def _relative_repo_path(value: str, field_name: str = "repo_path") -> str:
    normalized = _required_text(value, field_name).replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or (path.parts and ":" in path.parts[0]):
        raise ValueError(f"{field_name} must remain relative to the declared target boundary")
    return path.as_posix()


def _unique(values: list[str], field_name: str, *, allow_empty: bool = True) -> list[str]:
    normalized = [_stable_id(value, field_name) for value in values]
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique identities")
    return normalized


def _canonicalize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key])
            for key in sorted(value)
            if value[key] is not None
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        normalized = [_canonicalize(item) for item in value]
        return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    return value


def canonical_blueprint_json(value: Any) -> str:
    """Return the canonical logical JSON used by every blueprint fingerprint."""

    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_blueprint_fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_blueprint_json(value).encode("utf-8")).hexdigest()


def fingerprint_inventory(value: Any) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude_none=True)
    else:
        payload = dict(value)
        if "members" in payload:
            payload["members"] = [
                InventoryMember.model_validate(item).model_dump(mode="json", exclude_none=True)
                for item in payload["members"]
            ]
    payload.pop("inventory_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


def fingerprint_target_inventory_execution(value: Any) -> str:
    payload = value.model_dump(mode="json", exclude_none=True) if isinstance(value, BaseModel) else dict(value)
    payload.pop("execution_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


def fingerprint_target_inventory_authority(value: Any) -> str:
    payload = value.model_dump(mode="json", exclude_none=True) if isinstance(value, BaseModel) else dict(value)
    payload.pop("authority_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


def fingerprint_provider_registry_entry(value: Any) -> str:
    payload = value.model_dump(mode="json", exclude_none=True) if isinstance(value, BaseModel) else dict(value)
    payload.pop("entry_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


def fingerprint_provider_registry(value: Any) -> str:
    payload = value.model_dump(mode="json", exclude_none=True) if isinstance(value, BaseModel) else dict(value)
    payload.pop("registry_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


def fingerprint_target_material_revision(value: Any) -> str:
    payload = value.model_dump(mode="json", exclude_none=True) if isinstance(value, BaseModel) else dict(value)
    payload.pop("material_revision_fingerprint", None)
    payload.pop("request_id", None)
    if "semantics" in payload:
        payload["semantics"] = [
            {
                key: item[key]
                for key in item
                if not (key == "member_kind" and item[key] == "equation")
            }
            for item in payload["semantics"]
        ]
    return canonical_blueprint_fingerprint(payload)


def target_material_request_id(material_revision_fingerprint: str) -> str:
    revision = _sha256(
        material_revision_fingerprint,
        "material_revision_fingerprint",
    )
    return f"request.target-material.{revision}"


def fingerprint_blueprint(value: Any) -> str:
    return canonical_blueprint_fingerprint(value)


def fingerprint_review(value: Any) -> str:
    payload = value.model_dump(mode="json", exclude_none=True) if isinstance(value, BaseModel) else dict(value)
    payload.pop("logical_report_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


def fingerprint_projection(value: Any) -> str:
    payload = value.model_dump(mode="json", exclude_none=True) if isinstance(value, BaseModel) else dict(value)
    payload.pop("projection_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


def fingerprint_physical_behavior_case(value: Any) -> str:
    payload = value.model_dump(mode="json", exclude_none=True) if isinstance(value, BaseModel) else dict(value)
    payload.pop("case_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


def fingerprint_observed_semantic_selector(value: Any) -> str:
    payload = value.model_dump(mode="json", exclude_none=True) if isinstance(value, BaseModel) else dict(value)
    payload.pop("selector_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


def fingerprint_native_behavior_case_universe_member(value: Any) -> str:
    payload = value.model_dump(mode="json", exclude_none=True) if isinstance(value, BaseModel) else dict(value)
    payload.pop("member_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


class ArtifactReference(_StrictModel):
    """Content-addressed reference rooted at the canonical blueprint directory."""

    repo_path: str | None = None
    external_uri: str | None = None
    sha256: str

    @field_validator("sha256")
    @classmethod
    def _digest_valid(cls, value: str) -> str:
        return _sha256(value, "artifact sha256")

    @field_validator("repo_path")
    @classmethod
    def _repo_path_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _relative_repo_path(value)

    @field_validator("external_uri")
    @classmethod
    def _external_uri_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _required_text(value, "external_uri")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"https", "s3", "urn", "provider"}:
            raise ValueError("external_uri must use https, s3, urn, or provider")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("external_uri must not contain embedded credentials")
        secret_query_names = {
            "access_token",
            "api_key",
            "apikey",
            "credential",
            "password",
            "private_key",
            "secret",
            "signature",
            "token",
        }
        if any(key.lower() in secret_query_names for key, _ in parse_qsl(parsed.query)):
            raise ValueError("external_uri must not contain credential-like query parameters")
        return normalized

    @model_validator(mode="after")
    def _one_location(self) -> "ArtifactReference":
        if (self.repo_path is None) == (self.external_uri is None):
            raise ValueError("artifact reference requires exactly one of repo_path or external_uri")
        return self


class TargetIdentity(_StrictModel):
    target_system_id: str
    target_kind: TargetKind
    subject_revision: str
    boundary_fingerprint: str
    purpose: str
    claim_boundary: str

    @field_validator("target_system_id", "subject_revision")
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("purpose", "claim_boundary")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)

    @field_validator("boundary_fingerprint")
    @classmethod
    def _boundary_fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "boundary_fingerprint")


class ProviderBindingObservation(_StrictModel):
    """Exact provider attestation for one externally held native binding."""

    subject_id: str
    subject_revision: str
    binding_kind: BindingKind
    native_schema: NativeSchemaKind
    artifact_sha256: str
    semantic_ids: list[str] = Field(default_factory=list)
    obligation_ids: list[str] = Field(default_factory=list)
    status: ProviderStatus
    observation_fingerprint: str

    @field_validator("subject_id", "subject_revision")
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("artifact_sha256", "observation_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str, info) -> str:
        return _sha256(value, info.field_name)

    @field_validator("semantic_ids", "obligation_ids")
    @classmethod
    def _lists_valid(cls, values: list[str], info) -> list[str]:
        return _unique(values, info.field_name)

    @model_validator(mode="after")
    def _observation_current(self) -> "ProviderBindingObservation":
        payload = self.model_dump(mode="json", exclude={"observation_fingerprint"})
        expected = canonical_blueprint_fingerprint(payload)
        if self.observation_fingerprint != expected:
            raise ValueError("provider binding observation fingerprint is stale or invalid")
        return self


def fingerprint_provider_binding_observation(value: Any) -> str:
    payload = (
        value.model_dump(mode="json", exclude_none=True)
        if isinstance(value, BaseModel)
        else dict(value)
    )
    payload.pop("observation_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


def fingerprint_native_execution_evidence(value: Any) -> str:
    payload = (
        value.model_dump(mode="json", exclude_none=True)
        if isinstance(value, BaseModel)
        else dict(value)
    )
    payload.pop("execution_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


class NativeExecutionEvidence(_StrictModel):
    """Expected terminal identity that must be reproduced by a native owner."""

    execution_id: str
    native_owner_id: str
    operation_id: str
    native_schema: NativeSchemaKind
    input_artifact_sha256: str
    target_system_id: str
    subject_revision: str
    tool_id: Literal["physicsguard"] = "physicsguard"
    tool_version: str
    expected_terminal_status: str
    terminal_receipt_fingerprint: str
    execution_fingerprint: str

    @field_validator(
        "execution_id",
        "native_owner_id",
        "operation_id",
        "target_system_id",
        "subject_revision",
        "tool_version",
        "expected_terminal_status",
    )
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator(
        "input_artifact_sha256",
        "terminal_receipt_fingerprint",
        "execution_fingerprint",
    )
    @classmethod
    def _fingerprint_valid(cls, value: str, info) -> str:
        return _sha256(value, info.field_name)

    @model_validator(mode="after")
    def _execution_current(self) -> "NativeExecutionEvidence":
        if self.execution_fingerprint != fingerprint_native_execution_evidence(self):
            raise ValueError("native execution evidence fingerprint is stale or invalid")
        return self


class ProviderResult(_StrictModel):
    provider_id: str
    provider_kind: str
    provider_version: str
    target_system_id: str
    subject_revision: str
    capability_ids: list[str]
    input_fingerprints: dict[str, str]
    payload_fingerprint: str
    status: ProviderStatus
    binding_observations: list[ProviderBindingObservation] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    claim_boundary: str

    @field_validator("provider_id", "provider_kind", "provider_version", "target_system_id", "subject_revision")
    @classmethod
    def _ids_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("capability_ids")
    @classmethod
    def _capabilities_valid(cls, values: list[str]) -> list[str]:
        return _unique(values, "capability_ids", allow_empty=False)

    @field_validator("input_fingerprints")
    @classmethod
    def _inputs_valid(cls, values: dict[str, str]) -> dict[str, str]:
        if not values:
            raise ValueError("input_fingerprints cannot be empty")
        return {_stable_id(key, "input fingerprint id"): _sha256(value, key) for key, value in values.items()}

    @field_validator("payload_fingerprint")
    @classmethod
    def _payload_valid(cls, value: str) -> str:
        return _sha256(value, "payload_fingerprint")

    @field_validator("findings")
    @classmethod
    def _findings_valid(cls, values: list[str]) -> list[str]:
        return [_required_text(value, "provider finding") for value in values]

    @field_validator("claim_boundary")
    @classmethod
    def _claim_valid(cls, value: str) -> str:
        return _required_text(value, "claim_boundary")

    @model_validator(mode="after")
    def _binding_observations_unique_and_bound(self) -> "ProviderResult":
        keys = [
            (item.subject_id, item.subject_revision, item.artifact_sha256)
            for item in self.binding_observations
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("provider binding observations must have unique subject/revision/artifact identities")
        declared = set(self.input_fingerprints.values())
        unbound = [
            item.observation_fingerprint
            for item in self.binding_observations
            if item.observation_fingerprint not in declared
        ]
        if unbound:
            raise ValueError("provider binding observation fingerprint is absent from input_fingerprints")
        return self


class InventoryMember(_StrictModel):
    member_id: str
    member_kind: InventoryMemberKind
    disposition: InventoryDisposition
    blueprint_element_id: str | None = None
    binding_ids: list[str] = Field(default_factory=list)
    reason: str | None = None
    disposition_evidence: list[ArtifactReference] = Field(default_factory=list)

    @field_validator("member_id", "blueprint_element_id")
    @classmethod
    def _identity_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("binding_ids")
    @classmethod
    def _bindings_valid(cls, values: list[str]) -> list[str]:
        return _unique(values, "binding_ids")

    @model_validator(mode="after")
    def _disposition_complete(self) -> "InventoryMember":
        if self.disposition == "modeled" and self.blueprint_element_id is None:
            raise ValueError("modeled inventory members require blueprint_element_id")
        if self.disposition == "supporting" and not self.binding_ids:
            raise ValueError("supporting inventory members require binding_ids")
        if self.disposition in {"excluded", "unsupported", "unresolved"}:
            if not self.reason:
                raise ValueError(f"{self.disposition} inventory members require reason")
            if not self.disposition_evidence:
                raise ValueError(f"{self.disposition} inventory members require disposition_evidence")
        elif self.reason is not None:
            self.reason = _required_text(self.reason, "inventory reason")
        return self


class IndependentInventory(_StrictModel):
    inventory_id: str
    provider_id: str
    target_system_id: str
    subject_revision: str
    boundary_fingerprint: str
    members: list[InventoryMember]
    inventory_fingerprint: str

    @field_validator("inventory_id", "provider_id", "target_system_id", "subject_revision")
    @classmethod
    def _ids_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("boundary_fingerprint", "inventory_fingerprint")
    @classmethod
    def _fingerprints_valid(cls, value: str, info) -> str:
        return _sha256(value, info.field_name)

    @model_validator(mode="after")
    def _inventory_valid(self) -> "IndependentInventory":
        if not self.members:
            raise ValueError("independent inventory requires at least one member")
        member_ids = [item.member_id for item in self.members]
        if len(member_ids) != len(set(member_ids)):
            raise ValueError("inventory member ids must be unique")
        expected = fingerprint_inventory(self)
        if self.inventory_fingerprint != expected:
            raise ValueError("inventory_fingerprint is stale or invalid")
        return self


class TargetMaterialElement(_StrictModel):
    element_id: str

    @field_validator("element_id")
    @classmethod
    def _identity_valid(cls, value: str) -> str:
        return _stable_id(value, "element_id")


class TargetMaterialPort(_StrictModel):
    port_id: str
    owner_element_id: str

    @field_validator("port_id", "owner_element_id")
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)


class TargetMaterialSemantic(_StrictModel):
    semantic_id: str
    owner_element_id: str
    member_kind: Literal["equation", "variable", "parameter"] = "equation"

    @field_validator("semantic_id", "owner_element_id")
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)


class TargetMaterialBoundary(_StrictModel):
    boundary_id: str
    owner_element_id: str

    @field_validator("boundary_id", "owner_element_id")
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)


class TargetMaterialArtifact(_StrictModel):
    material_id: str
    material_kind: InventoryMemberKind
    binding_ids: list[str]

    @field_validator("material_id")
    @classmethod
    def _material_id_valid(cls, value: str) -> str:
        return _stable_id(value, "material_id")

    @field_validator("binding_ids")
    @classmethod
    def _binding_ids_valid(cls, values: list[str]) -> list[str]:
        return _unique(values, "binding_ids", allow_empty=False)


class TargetMaterialDocument(_StrictModel):
    """Raw target-native observations; it carries no inventory disposition rows."""

    schema_version: Literal["physicsguard.target-material.v1"] = TARGET_MATERIAL_SCHEMA
    request_id: str
    inventory_id: str
    provider_id: str
    target_system_id: str
    subject_revision: str
    boundary_fingerprint: str
    material_revision_fingerprint: str
    elements: list[TargetMaterialElement]
    ports: list[TargetMaterialPort] = Field(default_factory=list)
    semantics: list[TargetMaterialSemantic] = Field(default_factory=list)
    validity_boundaries: list[TargetMaterialBoundary] = Field(default_factory=list)
    materials: list[TargetMaterialArtifact] = Field(default_factory=list)

    @field_validator(
        "request_id",
        "inventory_id",
        "provider_id",
        "target_system_id",
        "subject_revision",
    )
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("boundary_fingerprint", "material_revision_fingerprint")
    @classmethod
    def _boundary_valid(cls, value: str) -> str:
        return _sha256(value, "target material fingerprint")

    @model_validator(mode="after")
    def _raw_material_consistent(self) -> "TargetMaterialDocument":
        expected_revision = fingerprint_target_material_revision(self)
        if self.material_revision_fingerprint != expected_revision:
            raise ValueError("target material revision fingerprint is stale or invalid")
        if self.request_id != target_material_request_id(expected_revision):
            raise ValueError("target material request id is not derived from its current revision")
        element_ids = [item.element_id for item in self.elements]
        if not element_ids or len(element_ids) != len(set(element_ids)):
            raise ValueError("target material requires unique physical elements")
        owners = set(element_ids)
        for collection, identity_field in (
            (self.ports, "port_id"),
            (self.semantics, "semantic_id"),
            (self.validity_boundaries, "boundary_id"),
            (self.materials, "material_id"),
        ):
            identities = [getattr(item, identity_field) for item in collection]
            if len(identities) != len(set(identities)):
                raise ValueError(f"target material {identity_field} values must be unique")
        for item in (*self.ports, *self.semantics, *self.validity_boundaries):
            if item.owner_element_id not in owners:
                raise ValueError("target material member references an unknown element owner")
        all_member_ids = [
            *element_ids,
            *(item.port_id for item in self.ports),
            *(item.semantic_id for item in self.semantics),
            *(item.boundary_id for item in self.validity_boundaries),
            *(item.material_id for item in self.materials),
        ]
        if len(all_member_ids) != len(set(all_member_ids)):
            raise ValueError("target material member identities must be globally unique")
        return self


class AuthorityInputReference(_StrictModel):
    reference_id: str
    artifact: ArtifactReference

    @field_validator("reference_id")
    @classmethod
    def _reference_id_valid(cls, value: str) -> str:
        return _stable_id(value, "reference_id")


class TargetInventoryExecutionAttestation(_StrictModel):
    execution_id: str
    owner_id: str
    request_id: str
    input_reference_ids: list[str]
    target_system_id: str
    subject_revision: str
    adapter_tool_id: str
    adapter_tool_version: str
    result_status: AuthorityResultStatus
    terminal_status: AuthorityTerminalStatus
    result_fingerprint: str
    terminal_receipt_fingerprint: str
    execution_fingerprint: str

    @field_validator(
        "execution_id",
        "owner_id",
        "request_id",
        "target_system_id",
        "subject_revision",
        "adapter_tool_id",
        "adapter_tool_version",
    )
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("input_reference_ids")
    @classmethod
    def _input_refs_valid(cls, values: list[str]) -> list[str]:
        return _unique(values, "input_reference_ids", allow_empty=False)

    @field_validator(
        "result_fingerprint",
        "terminal_receipt_fingerprint",
        "execution_fingerprint",
    )
    @classmethod
    def _fingerprints_valid(cls, value: str, info) -> str:
        return _sha256(value, info.field_name)

    @model_validator(mode="after")
    def _execution_current(self) -> "TargetInventoryExecutionAttestation":
        if self.execution_fingerprint != fingerprint_target_inventory_execution(self):
            raise ValueError("target inventory execution fingerprint is stale or invalid")
        return self


class TargetInventoryAuthority(_StrictModel):
    """Frozen target denominator issued outside the caller-owned blueprint."""

    schema_version: Literal["physicsguard.target-inventory-authority.v1"] = TARGET_INVENTORY_AUTHORITY_SCHEMA
    authority_id: str
    status: ProviderStatus
    owner_id: str
    request_id: str
    provider_id: str
    target_system_id: str
    subject_revision: str
    boundary_fingerprint: str
    input_references: list[AuthorityInputReference]
    inventory: IndependentInventory
    execution: TargetInventoryExecutionAttestation
    authority_fingerprint: str

    @field_validator(
        "authority_id",
        "owner_id",
        "request_id",
        "provider_id",
        "target_system_id",
        "subject_revision",
    )
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("boundary_fingerprint", "authority_fingerprint")
    @classmethod
    def _fingerprints_valid(cls, value: str, info) -> str:
        return _sha256(value, info.field_name)

    @model_validator(mode="after")
    def _authority_current(self) -> "TargetInventoryAuthority":
        input_ids = [item.reference_id for item in self.input_references]
        if not input_ids or len(input_ids) != len(set(input_ids)):
            raise ValueError("target inventory authority requires unique input references")
        if self.execution.input_reference_ids != sorted(input_ids):
            raise ValueError("target inventory execution must consume every authority input exactly once")
        exact_identity = (
            self.inventory.provider_id == self.provider_id
            and self.inventory.target_system_id == self.target_system_id
            and self.inventory.subject_revision == self.subject_revision
            and self.inventory.boundary_fingerprint == self.boundary_fingerprint
            and self.execution.owner_id == self.owner_id
            and self.execution.request_id == self.request_id
            and self.execution.target_system_id == self.target_system_id
            and self.execution.subject_revision == self.subject_revision
        )
        if not exact_identity:
            raise ValueError("target inventory authority identities are not exact")
        if self.execution.result_fingerprint != self.inventory.inventory_fingerprint:
            raise ValueError("target inventory execution result does not bind the authority inventory")
        if self.authority_fingerprint != fingerprint_target_inventory_authority(self):
            raise ValueError("target inventory authority fingerprint is stale or invalid")
        return self


class ProviderRegistryEntry(_StrictModel):
    registration_id: str
    status: ProviderStatus
    capability_ids: list[str]
    owner_id: str
    adapter_tool_id: str
    adapter_tool_version: str
    execution_mode: ProviderExecutionMode
    input_reference_ids: list[str]
    input_schema_version: str
    entry_fingerprint: str

    @field_validator(
        "registration_id",
        "owner_id",
        "adapter_tool_id",
        "adapter_tool_version",
        "input_schema_version",
    )
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("capability_ids")
    @classmethod
    def _capability_ids_valid(cls, values: list[str]) -> list[str]:
        return _unique(values, "capability_ids", allow_empty=False)

    @field_validator("input_reference_ids")
    @classmethod
    def _input_reference_ids_valid(cls, values: list[str]) -> list[str]:
        return _unique(values, "input_reference_ids", allow_empty=False)

    @field_validator("entry_fingerprint")
    @classmethod
    def _fingerprints_valid(cls, value: str, info) -> str:
        return _sha256(value, info.field_name)

    @model_validator(mode="after")
    def _entry_current(self) -> "ProviderRegistryEntry":
        if self.entry_fingerprint != fingerprint_provider_registry_entry(self):
            raise ValueError("provider registry entry fingerprint is stale or invalid")
        return self


class ProviderRegistry(_StrictModel):
    schema_version: Literal["physicsguard.provider-registry.v1"] = PROVIDER_REGISTRY_SCHEMA
    registry_id: str
    registry_revision: str
    status: ProviderStatus
    entries: list[ProviderRegistryEntry]
    registry_fingerprint: str

    @field_validator("registry_id", "registry_revision")
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("registry_fingerprint")
    @classmethod
    def _registry_fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "registry_fingerprint")

    @model_validator(mode="after")
    def _registry_current(self) -> "ProviderRegistry":
        request_keys = [
            (
                item.registration_id,
                item.adapter_tool_id,
                item.adapter_tool_version,
            )
            for item in self.entries
        ]
        if not request_keys or len(request_keys) != len(set(request_keys)):
            raise ValueError("provider registry requires unique current request entries")
        if self.registry_fingerprint != fingerprint_provider_registry(self):
            raise ValueError("provider registry fingerprint is stale or invalid")
        return self


class ValidityBoundary(_StrictModel):
    boundary_id: str
    owner_element_id: str
    statement: str
    parameter_bounds: dict[str, tuple[float | None, float | None]] = Field(default_factory=dict)

    @field_validator("boundary_id", "owner_element_id")
    @classmethod
    def _ids_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("statement")
    @classmethod
    def _statement_valid(cls, value: str) -> str:
        return _required_text(value, "validity statement")

    @model_validator(mode="after")
    def _bounds_valid(self) -> "ValidityBoundary":
        for name, (lower, upper) in self.parameter_bounds.items():
            _stable_id(name, "validity parameter")
            if lower is not None and upper is not None and lower > upper:
                raise ValueError(f"validity lower bound exceeds upper bound for {name}")
        return self


class PhysicalPort(_StrictModel):
    port_id: str
    owner_element_id: str
    direction: PortDirection
    quantity_id: str
    unit: str
    time_basis: str
    value_shape: str
    required: bool = True
    reference_frame: str | None = None
    sign_convention: str | None = None
    uncertainty: str | None = None
    validity_boundary_id: str | None = None
    initial_state_semantic_id: str | None = None
    termination_semantic_id: str | None = None

    @field_validator(
        "port_id",
        "owner_element_id",
        "quantity_id",
        "validity_boundary_id",
        "initial_state_semantic_id",
        "termination_semantic_id",
    )
    @classmethod
    def _ids_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("unit", "time_basis", "value_shape", "reference_frame", "sign_convention", "uncertainty")
    @classmethod
    def _descriptors_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _required_text(value, info.field_name)

    @model_validator(mode="after")
    def _state_contract_valid(self) -> "PhysicalPort":
        if self.direction == "state" and self.initial_state_semantic_id is None:
            raise ValueError("state ports require initial_state_semantic_id")
        if self.direction != "state" and (
            self.initial_state_semantic_id is not None or self.termination_semantic_id is not None
        ):
            raise ValueError("state lifecycle semantics are valid only for state ports")
        return self


class PhysicalSemantic(_StrictModel):
    semantic_id: str
    owner_element_id: str
    semantic_kind: SemanticKind
    statement: str
    expression: str | None = None
    input_port_ids: list[str] = Field(default_factory=list)
    output_port_ids: list[str] = Field(default_factory=list)
    state_port_ids: list[str] = Field(default_factory=list)
    effect_port_ids: list[str] = Field(default_factory=list)
    validity_boundary_ids: list[str] = Field(default_factory=list)
    assumption_ids: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)

    @field_validator("semantic_id", "owner_element_id")
    @classmethod
    def _ids_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("statement", "expression")
    @classmethod
    def _text_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _required_text(value, info.field_name)

    @field_validator(
        "input_port_ids",
        "output_port_ids",
        "state_port_ids",
        "effect_port_ids",
        "validity_boundary_ids",
        "assumption_ids",
    )
    @classmethod
    def _lists_valid(cls, values: list[str], info) -> list[str]:
        return _unique(values, info.field_name)

    @field_validator("preconditions", "postconditions")
    @classmethod
    def _conditions_valid(cls, values: list[str], info) -> list[str]:
        normalized = [_required_text(value, info.field_name) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError(f"{info.field_name} must be unique")
        return normalized

    @model_validator(mode="after")
    def _expression_valid(self) -> "PhysicalSemantic":
        if self.semantic_kind in {
            "equation",
            "residual",
            "constraint",
            "state_update",
            "conservation_law",
            "constitutive_relation",
            "conversion",
        } and self.expression is None:
            raise ValueError(f"{self.semantic_kind} semantics require expression")
        return self


class NativeValueBinding(_StrictModel):
    """Map one modeled case value to one value returned by a native replay."""

    port_id: str
    native_variable_name: str
    absolute_tolerance: float = Field(default=0.0, ge=0.0)

    @field_validator("port_id")
    @classmethod
    def _port_id_valid(cls, value: str) -> str:
        return _stable_id(value, "port_id")

    @field_validator("native_variable_name")
    @classmethod
    def _variable_name_valid(cls, value: str) -> str:
        return _required_text(value, "native_variable_name")

    @field_validator("absolute_tolerance")
    @classmethod
    def _tolerance_valid(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("absolute_tolerance must be finite")
        return value


class PhysicalBehaviorCase(_StrictModel):
    """One exact model/test transition bound to native evidence and an oracle."""

    case_id: str
    owner_element_id: str
    native_case_id: str
    case_kind: BehaviorCaseKind
    purpose: str
    input_values: dict[str, float] = Field(default_factory=dict)
    pre_state_values: dict[str, float] = Field(default_factory=dict)
    expected_output_values: dict[str, float] = Field(default_factory=dict)
    expected_post_state_values: dict[str, float] = Field(default_factory=dict)
    expected_effect_port_ids: list[str] = Field(default_factory=list)
    expected_terminal_status: str
    observed_output_values: dict[str, float] = Field(default_factory=dict)
    observed_post_state_values: dict[str, float] = Field(default_factory=dict)
    observed_effect_port_ids: list[str] = Field(default_factory=list)
    observed_terminal_status: str
    native_result_binding_id: str | None = None
    native_value_bindings: list[NativeValueBinding] = Field(default_factory=list)
    semantic_ids: list[str]
    test_binding_ids: list[str]
    evidence_binding_ids: list[str]
    oracle_binding_ids: list[str]
    status: BehaviorCaseStatus
    first_gap_code: str | None = None
    case_fingerprint: str

    @field_validator(
        "case_id",
        "owner_element_id",
        "native_case_id",
        "native_result_binding_id",
        "first_gap_code",
    )
    @classmethod
    def _ids_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("purpose", "expected_terminal_status", "observed_terminal_status")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)

    @field_validator(
        "expected_effect_port_ids",
        "observed_effect_port_ids",
        "semantic_ids",
        "test_binding_ids",
        "evidence_binding_ids",
        "oracle_binding_ids",
    )
    @classmethod
    def _lists_valid(cls, values: list[str], info) -> list[str]:
        return _unique(
            values,
            info.field_name,
            allow_empty=info.field_name in {"expected_effect_port_ids", "observed_effect_port_ids"},
        )

    @field_validator(
        "input_values",
        "pre_state_values",
        "expected_output_values",
        "expected_post_state_values",
        "observed_output_values",
        "observed_post_state_values",
    )
    @classmethod
    def _values_valid(cls, values: dict[str, float], info) -> dict[str, float]:
        output: dict[str, float] = {}
        for port_id, value in values.items():
            normalized_id = _stable_id(port_id, info.field_name)
            if not math.isfinite(value):
                raise ValueError(f"{info.field_name}.{normalized_id} must be finite")
            output[normalized_id] = value
        return output

    @field_validator("case_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "case_fingerprint")

    @model_validator(mode="after")
    def _case_consistent(self) -> "PhysicalBehaviorCase":
        mapped_port_ids = [item.port_id for item in self.native_value_bindings]
        if len(mapped_port_ids) != len(set(mapped_port_ids)):
            raise ValueError("native_value_bindings must map each model port at most once")
        if self.status == "pass":
            if self.first_gap_code is not None:
                raise ValueError("passing behavior case cannot contain a first gap")
            if set(self.observed_output_values) != set(self.expected_output_values):
                raise ValueError("passing behavior case must observe every expected output")
            if set(self.observed_post_state_values) != set(self.expected_post_state_values):
                raise ValueError("passing behavior case must observe every expected post-state")
            if set(self.observed_effect_port_ids) != set(self.expected_effect_port_ids):
                raise ValueError("passing behavior case must observe every expected effect")
            if self.observed_terminal_status != self.expected_terminal_status:
                raise ValueError("passing behavior case terminal status differs from expectation")
        elif self.first_gap_code is None:
            raise ValueError("non-passing behavior case requires first_gap_code")
        if self.case_fingerprint != fingerprint_physical_behavior_case(self):
            raise ValueError("case_fingerprint is stale or invalid")
        return self


class FmiVariableSemanticContract(_StrictModel):
    """FMI-native meaning observed for one scalar variable.

    This is intentionally narrower than a generic provider contract.  It is
    the first verified native adapter contract and must never be inferred from
    target port names alone.
    """

    variable_name: str
    value_reference: int = Field(ge=0)
    variable_type: str
    causality: str
    variability: str
    unit: str | None = None
    derivative_of_value_reference: int | None = Field(default=None, ge=0)
    reinit: bool | None = None
    physical_quantity_id: str
    source_state_role: FmiSourceStateRole

    @field_validator(
        "variable_name",
        "variable_type",
        "causality",
        "variability",
        "unit",
        "physical_quantity_id",
    )
    @classmethod
    def _text_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _required_text(value, info.field_name)


class SourceUnitConversion(_StrictModel):
    conversion_kind: UnitConversionKind
    scale: float = 1.0
    offset: float = 0.0
    authority_binding_id: str | None = None

    @field_validator("authority_binding_id")
    @classmethod
    def _authority_valid(cls, value: str | None) -> str | None:
        return None if value is None else _stable_id(value, "authority_binding_id")

    @model_validator(mode="after")
    def _conversion_valid(self) -> "SourceUnitConversion":
        if not math.isfinite(self.scale) or not math.isfinite(self.offset):
            raise ValueError("unit conversion scale and offset must be finite")
        if self.conversion_kind in {"identity", "dimensionless_identity"}:
            if self.scale != 1.0 or self.offset != 0.0:
                raise ValueError("identity conversions require scale=1 and offset=0")
            if self.authority_binding_id is not None:
                raise ValueError("identity conversions cannot claim a separate authority")
        elif self.authority_binding_id is None:
            raise ValueError("affine conversion requires an exact authority binding")
        return self


class SourcePortContract(_StrictModel):
    target_port_id: str
    expected_direction: PortDirection
    expected_quantity_id: str
    expected_unit: str
    port_state_role: PortStateRole
    quantity_relation: QuantityRelation = "identity"
    conversion: SourceUnitConversion
    governing_semantic_ids: list[str] = Field(default_factory=list)

    @field_validator("target_port_id", "expected_quantity_id")
    @classmethod
    def _ids_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("expected_unit")
    @classmethod
    def _unit_valid(cls, value: str) -> str:
        return _required_text(value, "expected_unit")

    @field_validator("governing_semantic_ids")
    @classmethod
    def _semantics_valid(cls, values: list[str]) -> list[str]:
        return _unique(values, "governing_semantic_ids")


class SourceSemanticContract(_StrictModel):
    target_semantic_id: str
    selector_id: str
    expected_selector_fingerprint: str

    @field_validator("target_semantic_id", "selector_id")
    @classmethod
    def _ids_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("expected_selector_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "expected_selector_fingerprint")


class SourceModelMapping(_StrictModel):
    """One terminal mapping from an observed source member into the living model."""

    mapping_id: str
    source_binding_id: str
    source_member_id: str
    relation: SourceMappingRelation
    target_ids: list[str] = Field(default_factory=list)
    reason: str
    fmi_variable_contract: FmiVariableSemanticContract | None = None
    port_contracts: list[SourcePortContract] = Field(default_factory=list)
    semantic_contracts: list[SourceSemanticContract] = Field(default_factory=list)

    @field_validator("mapping_id", "source_binding_id", "source_member_id")
    @classmethod
    def _ids_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("target_ids")
    @classmethod
    def _targets_valid(cls, values: list[str]) -> list[str]:
        return _unique(values, "target_ids")

    @field_validator("reason")
    @classmethod
    def _reason_valid(cls, value: str) -> str:
        return _required_text(value, "source mapping reason")

    @model_validator(mode="after")
    def _terminal_mapping_valid(self) -> "SourceModelMapping":
        if self.relation == "dispositioned" and self.target_ids:
            raise ValueError("dispositioned source mappings cannot target model objects")
        if self.relation != "dispositioned" and not self.target_ids:
            raise ValueError("non-disposition source mappings require at least one target id")
        if self.port_contracts and self.fmi_variable_contract is None:
            raise ValueError("port contracts require an FMI variable semantic contract")
        contracted_target_ids = [item.target_port_id for item in self.port_contracts]
        if len(contracted_target_ids) != len(set(contracted_target_ids)):
            raise ValueError("port_contracts must bind each target port at most once")
        semantic_target_ids = [item.target_semantic_id for item in self.semantic_contracts]
        if len(semantic_target_ids) != len(set(semantic_target_ids)):
            raise ValueError("semantic_contracts must bind each target semantic at most once")
        if any(target_id not in self.target_ids for target_id in contracted_target_ids + semantic_target_ids):
            raise ValueError("source contracts may reference only this mapping's target_ids")
        return self


class ObservedSemanticSelector(_StrictModel):
    """A source fragment resolved by the native adapter, not by the blueprint."""

    selector_id: str
    function_name: str
    normalized_source_fragment: str
    source_fragment_fingerprint: str
    semantic_kind: SemanticKind
    semantic_statement: str
    semantic_expression: str | None = None
    status: SemanticSelectorStatus
    claim_boundary: str
    first_gap_code: str | None = None
    selector_fingerprint: str

    @field_validator("selector_id", "first_gap_code")
    @classmethod
    def _ids_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator(
        "function_name",
        "normalized_source_fragment",
        "semantic_statement",
        "semantic_expression",
        "claim_boundary",
    )
    @classmethod
    def _text_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _required_text(value, info.field_name)

    @field_validator("source_fragment_fingerprint", "selector_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str, info) -> str:
        return _sha256(value, info.field_name)

    @model_validator(mode="after")
    def _selector_valid(self) -> "ObservedSemanticSelector":
        actual_fragment_fingerprint = canonical_blueprint_fingerprint(self.normalized_source_fragment)
        if self.source_fragment_fingerprint != actual_fragment_fingerprint:
            raise ValueError("source_fragment_fingerprint is stale or invalid")
        if self.status == "verified" and self.first_gap_code is not None:
            raise ValueError("verified semantic selectors cannot contain a gap")
        if self.status == "unresolved" and self.first_gap_code is None:
            raise ValueError("unresolved semantic selectors require first_gap_code")
        if self.selector_fingerprint != fingerprint_observed_semantic_selector(self):
            raise ValueError("selector_fingerprint is stale or invalid")
        return self


class ObservedSourceMember(_StrictModel):
    """Provider-neutral compact projection of one native-observed source member."""

    source_member_id: str
    source_kind: str
    locator: str
    role: str
    member_fingerprint: str
    semantic_expression: str | None = None
    fmi_variable_contract: FmiVariableSemanticContract | None = None
    semantic_selectors: list[ObservedSemanticSelector] = Field(default_factory=list)

    @field_validator("source_member_id", "source_kind")
    @classmethod
    def _ids_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("locator", "role", "semantic_expression")
    @classmethod
    def _text_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _required_text(value, info.field_name)

    @field_validator("member_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "member_fingerprint")

    @model_validator(mode="after")
    def _nested_contracts_valid(self) -> "ObservedSourceMember":
        selector_ids = [item.selector_id for item in self.semantic_selectors]
        if len(selector_ids) != len(set(selector_ids)):
            raise ValueError("semantic_selectors must contain unique selector ids")
        return self


class ObservedNativeBehaviorCase(_StrictModel):
    native_case_id: str
    disposition: NativeBehaviorCaseDisposition
    disposition_reason: str | None = None
    disposition_authority_binding_id: str | None = None
    native_input_fingerprint: str
    member_fingerprint: str

    @field_validator("native_case_id", "disposition_authority_binding_id")
    @classmethod
    def _ids_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("disposition_reason")
    @classmethod
    def _reason_valid(cls, value: str | None) -> str | None:
        return None if value is None else _required_text(value, "disposition_reason")

    @field_validator("native_input_fingerprint", "member_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str, info) -> str:
        return _sha256(value, info.field_name)

    @model_validator(mode="after")
    def _case_valid(self) -> "ObservedNativeBehaviorCase":
        if self.disposition == "required":
            if self.disposition_reason is not None or self.disposition_authority_binding_id is not None:
                raise ValueError("required native cases cannot carry a disposition")
        elif self.disposition_reason is None or self.disposition_authority_binding_id is None:
            raise ValueError("dispositioned native cases require independent reason and authority")
        if self.member_fingerprint != fingerprint_native_behavior_case_universe_member(self):
            raise ValueError("native behavior case member_fingerprint is stale or invalid")
        return self


class UnresolvedPhysicalRelation(_StrictModel):
    relation_id: str
    relation_kind: str
    source_ids: list[str]
    target_ids: list[str]
    status: Literal["unresolved", "stale", "unsupported"]
    reason: str
    evidence: list[ArtifactReference]

    @field_validator("relation_id", "relation_kind")
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("source_ids", "target_ids")
    @classmethod
    def _endpoint_ids_valid(cls, values: list[str], info) -> list[str]:
        return _unique(values, info.field_name, allow_empty=False)

    @field_validator("reason")
    @classmethod
    def _reason_valid(cls, value: str) -> str:
        return _required_text(value, "unresolved relation reason")

    @field_validator("evidence")
    @classmethod
    def _evidence_present(cls, values: list[ArtifactReference]) -> list[ArtifactReference]:
        if not values:
            raise ValueError("unresolved physical relations require evidence")
        return values


class PhysicalElement(_StrictModel):
    element_id: str
    name: str
    element_kind: PhysicalElementKind
    parent_id: str | None = None
    depth: int = Field(ge=0)
    description: str
    port_ids: list[str] = Field(default_factory=list)
    semantic_ids: list[str] = Field(default_factory=list)
    validity_boundary_ids: list[str] = Field(default_factory=list)
    native_binding_ids: list[str] = Field(default_factory=list)
    owned_behavior_ids: list[str] = Field(default_factory=list)
    supporting_only: bool = False

    @field_validator("element_id", "parent_id")
    @classmethod
    def _ids_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("name", "description")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)

    @field_validator("port_ids", "semantic_ids", "validity_boundary_ids", "native_binding_ids", "owned_behavior_ids")
    @classmethod
    def _lists_valid(cls, values: list[str], info) -> list[str]:
        return _unique(values, info.field_name)


class PortMapping(_StrictModel):
    mapping_id: str
    mapping_kind: MappingKind
    source_port_id: str | None = None
    external_source_id: str | None = None
    target_port_id: str
    conversion_semantic_id: str | None = None
    evidence_binding_ids: list[str] = Field(default_factory=list)

    @field_validator("mapping_id", "source_port_id", "external_source_id", "target_port_id", "conversion_semantic_id")
    @classmethod
    def _ids_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("evidence_binding_ids")
    @classmethod
    def _evidence_valid(cls, values: list[str]) -> list[str]:
        return _unique(values, "evidence_binding_ids")

    @model_validator(mode="after")
    def _source_valid(self) -> "PortMapping":
        if (self.source_port_id is None) == (self.external_source_id is None):
            raise ValueError("port mapping requires exactly one source_port_id or external_source_id")
        if self.mapping_kind == "external_input_to_child_input" and self.external_source_id is None:
            raise ValueError("external input mappings require external_source_id")
        if self.mapping_kind != "external_input_to_child_input" and self.source_port_id is None:
            raise ValueError("non-external mappings require source_port_id")
        return self


class SemanticContribution(_StrictModel):
    contribution_id: str
    child_semantic_id: str
    parent_semantic_id: str
    relation: ContributionKind
    rationale: str
    evidence_binding_ids: list[str] = Field(default_factory=list)

    @field_validator("contribution_id", "child_semantic_id", "parent_semantic_id")
    @classmethod
    def _ids_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("rationale")
    @classmethod
    def _rationale_valid(cls, value: str) -> str:
        return _required_text(value, "contribution rationale")

    @field_validator("evidence_binding_ids")
    @classmethod
    def _evidence_valid(cls, values: list[str]) -> list[str]:
        return _unique(values, "evidence_binding_ids")


class RefinementContract(_StrictModel):
    refinement_id: str
    parent_element_id: str
    child_element_ids: list[str]
    port_mappings: list[PortMapping] = Field(default_factory=list)
    semantic_contributions: list[SemanticContribution] = Field(default_factory=list)
    child_local_state_ids: list[str] = Field(default_factory=list)
    terminal_output_ids: list[str] = Field(default_factory=list)
    terminal_effect_ids: list[str] = Field(default_factory=list)
    propagated_validity_boundary_ids: list[str] = Field(default_factory=list)

    @field_validator("refinement_id", "parent_element_id")
    @classmethod
    def _ids_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator(
        "child_element_ids",
        "child_local_state_ids",
        "terminal_output_ids",
        "terminal_effect_ids",
        "propagated_validity_boundary_ids",
    )
    @classmethod
    def _lists_valid(cls, values: list[str], info) -> list[str]:
        return _unique(values, info.field_name, allow_empty=info.field_name != "child_element_ids")

    @model_validator(mode="after")
    def _nested_ids_unique(self) -> "RefinementContract":
        mapping_ids = [item.mapping_id for item in self.port_mappings]
        contribution_ids = [item.contribution_id for item in self.semantic_contributions]
        if len(mapping_ids) != len(set(mapping_ids)):
            raise ValueError("refinement port mapping ids must be unique")
        if len(contribution_ids) != len(set(contribution_ids)):
            raise ValueError("semantic contribution ids must be unique")
        return self


class NativeBinding(_StrictModel):
    binding_id: str
    owner_element_id: str
    binding_kind: BindingKind
    native_schema: NativeSchemaKind = "generic_artifact"
    subject_id: str
    subject_revision: str
    artifact: ArtifactReference
    provider_id: str | None = None
    native_execution_id: str | None = None
    status: ProviderStatus = "current"
    semantic_ids: list[str] = Field(default_factory=list)
    obligation_ids: list[str] = Field(default_factory=list)
    validation_modes: list[ValidationMode] = Field(default_factory=list)

    @field_validator(
        "binding_id",
        "owner_element_id",
        "subject_id",
        "subject_revision",
        "provider_id",
        "native_execution_id",
    )
    @classmethod
    def _ids_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("semantic_ids", "obligation_ids", "validation_modes")
    @classmethod
    def _lists_valid(cls, values: list[str], info) -> list[str]:
        return _unique(values, info.field_name)


class PhysicalModelBlueprint(_StrictModel):
    """One canonical physical-domain blueprint and no caller-owned readiness."""

    schema_version: Literal["physicsguard.physical-model-blueprint.v1"] = PHYSICAL_MODEL_BLUEPRINT_SCHEMA
    blueprint_id: str
    qualification_target: Literal["external_physical_target"] = "external_physical_target"
    understanding_target: UnderstandingTarget = "declared_consistency"
    artifact_root: Literal["blueprint_directory", "explicit_material_root"]
    target: TargetIdentity
    required_capability_ids: list[str]
    capability_owners: dict[str, str]
    providers: list[ProviderResult]
    inventory: IndependentInventory
    elements: list[PhysicalElement]
    ports: list[PhysicalPort]
    semantics: list[PhysicalSemantic]
    behavior_cases: list[PhysicalBehaviorCase] = Field(default_factory=list)
    validity_boundaries: list[ValidityBoundary]
    refinements: list[RefinementContract] = Field(default_factory=list)
    unresolved_relations: list[UnresolvedPhysicalRelation] = Field(default_factory=list)
    native_executions: list[NativeExecutionEvidence] = Field(default_factory=list)
    bindings: list[NativeBinding]
    source_mappings: list[SourceModelMapping] = Field(default_factory=list)

    @field_validator("blueprint_id")
    @classmethod
    def _blueprint_id_valid(cls, value: str) -> str:
        return _stable_id(value, "blueprint_id")

    @field_validator("required_capability_ids")
    @classmethod
    def _required_capabilities_valid(cls, values: list[str]) -> list[str]:
        return _unique(values, "required_capability_ids", allow_empty=False)

    @model_validator(mode="after")
    def _cross_references_valid(self) -> "PhysicalModelBlueprint":
        _reject_secret_fields(self.model_dump(mode="json", exclude_none=True))
        if self.inventory.target_system_id != self.target.target_system_id:
            raise ValueError("inventory target_system_id does not match blueprint target")
        if self.inventory.subject_revision != self.target.subject_revision:
            raise ValueError("inventory subject_revision does not match blueprint target")
        if self.inventory.boundary_fingerprint != self.target.boundary_fingerprint:
            raise ValueError("inventory boundary_fingerprint does not match blueprint target")

        provider_by_id = _index_unique(self.providers, "provider_id", "provider")
        if set(self.capability_owners) != set(self.required_capability_ids):
            raise ValueError("capability_owners must exactly cover required_capability_ids")
        for capability_id, provider_id in self.capability_owners.items():
            provider = provider_by_id.get(provider_id)
            if provider is None:
                raise ValueError(f"capability owner references unknown provider: {provider_id}")
            if capability_id not in provider.capability_ids:
                raise ValueError(f"provider {provider_id} does not declare capability {capability_id}")
        if self.inventory.provider_id not in provider_by_id:
            raise ValueError("inventory references unknown provider")

        element_by_id = _index_unique(self.elements, "element_id", "physical element")
        if not element_by_id:
            raise ValueError("blueprint requires at least one physical element")
        roots = [element for element in self.elements if element.parent_id is None]
        if len(roots) != 1:
            raise ValueError(f"blueprint requires exactly one root; found {[item.element_id for item in roots]}")
        for element in self.elements:
            if element.parent_id is None:
                if element.depth != 0:
                    raise ValueError("root physical element must have depth zero")
                continue
            parent = element_by_id.get(element.parent_id)
            if parent is None:
                raise ValueError(f"physical element has unknown parent: {element.element_id}")
            if element.depth != parent.depth + 1:
                raise ValueError(
                    "child physical element depth must equal parent depth plus one"
                )
            _assert_acyclic(element, element_by_id)

        port_by_id = _index_unique(self.ports, "port_id", "physical port")
        semantic_by_id = _index_unique(self.semantics, "semantic_id", "physical semantic")
        case_by_id = _index_unique(self.behavior_cases, "case_id", "physical behavior case")
        boundary_by_id = _index_unique(self.validity_boundaries, "boundary_id", "validity boundary")
        binding_by_id = _index_unique(self.bindings, "binding_id", "native binding")
        execution_by_id = _index_unique(self.native_executions, "execution_id", "native execution")
        _index_unique(self.refinements, "refinement_id", "refinement")
        _index_unique(self.unresolved_relations, "relation_id", "unresolved relation")
        _index_unique(self.source_mappings, "mapping_id", "source mapping")

        behavior_owners: dict[str, str] = {}
        for element in self.elements:
            for behavior_id in element.owned_behavior_ids:
                previous = behavior_owners.get(behavior_id)
                if previous is not None:
                    raise ValueError(f"behavior {behavior_id} has duplicate primary owners: {previous}, {element.element_id}")
                behavior_owners[behavior_id] = element.element_id
            _require_exact_owned_ids(element.port_ids, port_by_id, element.element_id, "owner_element_id", "port")
            _require_exact_owned_ids(element.semantic_ids, semantic_by_id, element.element_id, "owner_element_id", "semantic")
            _require_exact_owned_ids(element.validity_boundary_ids, boundary_by_id, element.element_id, "owner_element_id", "validity boundary")
            _require_exact_owned_ids(element.native_binding_ids, binding_by_id, element.element_id, "owner_element_id", "native binding")

        for port in self.ports:
            if port.owner_element_id not in element_by_id:
                raise ValueError(f"port references unknown owner element: {port.port_id}")
            if port.validity_boundary_id and port.validity_boundary_id not in boundary_by_id:
                raise ValueError(f"port references unknown validity boundary: {port.port_id}")
            if port.initial_state_semantic_id and port.initial_state_semantic_id not in semantic_by_id:
                raise ValueError(f"state port references unknown initial-state semantic: {port.port_id}")
            if port.termination_semantic_id:
                termination = semantic_by_id.get(port.termination_semantic_id)
                if termination is None or termination.semantic_kind != "termination":
                    raise ValueError(f"state port references unknown termination semantic: {port.port_id}")

        for semantic in self.semantics:
            if semantic.owner_element_id not in element_by_id:
                raise ValueError(f"semantic references unknown owner element: {semantic.semantic_id}")
            for field_name in ("input_port_ids", "output_port_ids", "state_port_ids", "effect_port_ids"):
                for port_id in getattr(semantic, field_name):
                    if port_id not in port_by_id:
                        raise ValueError(f"semantic {semantic.semantic_id} references unknown port {port_id}")
            for boundary_id in semantic.validity_boundary_ids:
                if boundary_id not in boundary_by_id:
                    raise ValueError(f"semantic {semantic.semantic_id} references unknown validity boundary {boundary_id}")
            for assumption_id in semantic.assumption_ids:
                assumption = semantic_by_id.get(assumption_id)
                if assumption is None or assumption.semantic_kind != "assumption":
                    raise ValueError(f"semantic {semantic.semantic_id} references unknown assumption {assumption_id}")

        for boundary in self.validity_boundaries:
            if boundary.owner_element_id not in element_by_id:
                raise ValueError(f"validity boundary references unknown owner: {boundary.boundary_id}")
        for binding in self.bindings:
            if binding.owner_element_id not in element_by_id:
                raise ValueError(f"native binding references unknown owner: {binding.binding_id}")
            if binding.provider_id is not None and binding.provider_id not in provider_by_id:
                raise ValueError(f"native binding references unknown provider: {binding.binding_id}")
            if binding.native_execution_id is not None:
                execution = execution_by_id.get(binding.native_execution_id)
                if execution is None:
                    raise ValueError(
                        f"native binding references unknown native execution: {binding.binding_id}"
                    )
                if execution.native_schema != binding.native_schema:
                    raise ValueError(
                        f"native execution schema does not match binding: {binding.binding_id}"
                    )
                if execution.input_artifact_sha256 != binding.artifact.sha256:
                    raise ValueError(
                        f"native execution input fingerprint does not match binding: {binding.binding_id}"
                    )
                if (
                    execution.target_system_id != self.target.target_system_id
                    or execution.subject_revision != self.target.subject_revision
                ):
                    raise ValueError(
                        f"native execution targets another blueprint subject: {binding.binding_id}"
                    )
            for semantic_id in binding.semantic_ids:
                if semantic_id not in semantic_by_id:
                    raise ValueError(f"native binding {binding.binding_id} references unknown semantic {semantic_id}")
        for case in self.behavior_cases:
            owner = element_by_id.get(case.owner_element_id)
            if owner is None:
                raise ValueError(f"behavior case references unknown owner: {case.case_id}")
            for semantic_id in case.semantic_ids:
                semantic = semantic_by_id.get(semantic_id)
                if semantic is None or semantic.owner_element_id != case.owner_element_id:
                    raise ValueError(f"behavior case references foreign semantic: {case.case_id}:{semantic_id}")
            for field_name, direction in (
                ("input_values", "input"),
                ("pre_state_values", "state"),
                ("expected_output_values", "output"),
                ("observed_output_values", "output"),
                ("expected_post_state_values", "state"),
                ("observed_post_state_values", "state"),
            ):
                for port_id in getattr(case, field_name):
                    port = port_by_id.get(port_id)
                    if port is None or port.owner_element_id != case.owner_element_id or port.direction != direction:
                        raise ValueError(
                            f"behavior case {case.case_id} {field_name} references a non-{direction} owner port: {port_id}"
                        )
            for port_id in (*case.expected_effect_port_ids, *case.observed_effect_port_ids):
                port = port_by_id.get(port_id)
                if port is None or port.owner_element_id != case.owner_element_id or port.direction != "effect":
                    raise ValueError(f"behavior case references a non-effect owner port: {case.case_id}:{port_id}")
            if case.native_result_binding_id is not None:
                native_result_binding = binding_by_id.get(case.native_result_binding_id)
                if (
                    native_result_binding is None
                    or native_result_binding.native_schema == "generic_artifact"
                    or native_result_binding.native_execution_id is None
                ):
                    raise ValueError(
                        f"behavior case {case.case_id} native result binding must name one replayable native binding"
                    )
            for value_binding in case.native_value_bindings:
                port = port_by_id.get(value_binding.port_id)
                if (
                    port is None
                    or port.owner_element_id != case.owner_element_id
                    or value_binding.port_id
                    not in {
                        *case.expected_output_values,
                        *case.expected_post_state_values,
                    }
                ):
                    raise ValueError(
                        f"behavior case {case.case_id} native value mapping references an unclaimed output/state port: {value_binding.port_id}"
                    )
            for binding_ids, binding_kind in (
                (case.test_binding_ids, "test"),
                (case.evidence_binding_ids, "evidence"),
                (case.oracle_binding_ids, "oracle"),
            ):
                for binding_id in binding_ids:
                    binding = binding_by_id.get(binding_id)
                    if binding is None or binding.owner_element_id != case.owner_element_id or binding.binding_kind != binding_kind:
                        raise ValueError(
                            f"behavior case {case.case_id} references a foreign or non-{binding_kind} binding: {binding_id}"
                        )
        referenced_execution_ids = {
            binding.native_execution_id
            for binding in self.bindings
            if binding.native_execution_id is not None
        }
        unused_execution_ids = sorted(set(execution_by_id) - referenced_execution_ids)
        if unused_execution_ids:
            raise ValueError(
                f"native execution evidence must be consumed by a binding: {unused_execution_ids}"
            )

        children_by_parent: dict[str, set[str]] = {}
        for element in self.elements:
            if element.parent_id:
                children_by_parent.setdefault(element.parent_id, set()).add(element.element_id)
        refinement_by_parent: dict[str, RefinementContract] = {}
        for refinement in self.refinements:
            if refinement.parent_element_id in refinement_by_parent:
                raise ValueError(f"parent has duplicate refinement contracts: {refinement.parent_element_id}")
            refinement_by_parent[refinement.parent_element_id] = refinement
            expected_children = children_by_parent.get(refinement.parent_element_id, set())
            if set(refinement.child_element_ids) != expected_children:
                raise ValueError(f"refinement children do not match hierarchy for {refinement.parent_element_id}")
            _validate_refinement_references(refinement, port_by_id, semantic_by_id, boundary_by_id, binding_by_id)
        for parent_id in children_by_parent:
            if parent_id not in refinement_by_parent:
                raise ValueError(f"parent element requires refinement contract: {parent_id}")

        for member in self.inventory.members:
            if member.blueprint_element_id and member.blueprint_element_id not in element_by_id:
                raise ValueError(f"inventory member references unknown blueprint element: {member.member_id}")
            for binding_id in member.binding_ids:
                if binding_id not in binding_by_id:
                    raise ValueError(f"inventory member references unknown binding: {member.member_id}")
        known_relation_endpoints = (
            set(element_by_id)
            | set(port_by_id)
            | set(semantic_by_id)
            | set(boundary_by_id)
            | set(binding_by_id)
            | {item.member_id for item in self.inventory.members}
        )
        for relation in self.unresolved_relations:
            unknown = sorted((set(relation.source_ids) | set(relation.target_ids)) - known_relation_endpoints)
            if unknown:
                raise ValueError(f"unresolved physical relation references unknown endpoints: {unknown}")
        source_mapping_keys: set[str] = set()
        for mapping in self.source_mappings:
            if mapping.source_binding_id not in binding_by_id:
                raise ValueError(
                    f"source mapping references unknown native binding: {mapping.mapping_id}"
                )
            source_key = mapping.source_member_id
            if source_key in source_mapping_keys:
                raise ValueError(
                    "each observed source member must have exactly one terminal mapping: "
                    f"{mapping.source_member_id}"
                )
            source_mapping_keys.add(source_key)
            unknown_targets = sorted(set(mapping.target_ids) - known_relation_endpoints - set(case_by_id))
            if unknown_targets:
                raise ValueError(
                    f"source mapping references unknown model targets: {mapping.mapping_id}:{unknown_targets}"
                )
        return self


class BlueprintGap(_StrictModel):
    gap_id: str
    layer: BlueprintLayerName
    status: Literal["incomplete", "stale", "blocked"]
    code: str
    message: str
    target_ids: list[str] = Field(default_factory=list)
    next_action: str

    @field_validator("gap_id", "code")
    @classmethod
    def _ids_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("message", "next_action")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)

    @field_validator("target_ids")
    @classmethod
    def _targets_valid(cls, values: list[str]) -> list[str]:
        return _unique(values, "target_ids")


class BlueprintLayerResult(_StrictModel):
    layer: BlueprintLayerName
    status: ReviewStatus
    gap_ids: list[str] = Field(default_factory=list)
    covered_ids: list[str] = Field(default_factory=list)

    @field_validator("gap_ids", "covered_ids")
    @classmethod
    def _ids_valid(cls, values: list[str], info) -> list[str]:
        return _unique(values, info.field_name)


class BlueprintCoverage(_StrictModel):
    governed_member_ids: list[str]
    covered_member_ids: list[str]
    uncovered_member_ids: list[str]

    @field_validator("governed_member_ids", "covered_member_ids", "uncovered_member_ids")
    @classmethod
    def _ids_valid(cls, values: list[str], info) -> list[str]:
        return _unique(values, info.field_name)

    @model_validator(mode="after")
    def _coverage_consistent(self) -> "BlueprintCoverage":
        governed = set(self.governed_member_ids)
        covered = set(self.covered_member_ids)
        uncovered = set(self.uncovered_member_ids)
        if covered & uncovered:
            raise ValueError("covered and uncovered member ids must be disjoint")
        if covered | uncovered != governed:
            raise ValueError("covered plus uncovered must exactly equal governed members")
        return self


class PhysicalModelBlueprintReview(_StrictModel):
    schema_version: Literal["physicsguard.physical-model-blueprint-review.v1"] = PHYSICAL_MODEL_BLUEPRINT_REVIEW_SCHEMA
    review_id: str
    status: ReviewStatus
    scope: Literal["whole", "affected"]
    understanding_target: UnderstandingTarget
    declared_consistency_status: ReviewStatus
    object_dna_readiness: ObjectDnaReadinessStatus
    target_system_id: str
    subject_revision: str
    blueprint_fingerprint: str
    inventory_fingerprint: str
    target_inventory_authority_fingerprint: str
    provider_registry_fingerprint: str
    layer_results: list[BlueprintLayerResult]
    deepest_licensed_layer: BlueprintLayerName | None
    first_gap_id: str | None
    gaps: list[BlueprintGap]
    coverage: BlueprintCoverage
    global_governed_member_ids: list[str] = Field(default_factory=list)
    outside_scope_member_ids: list[str] = Field(default_factory=list)
    source_census_fingerprint: str | None = None
    source_census: list[ObservedSourceMember] = Field(default_factory=list)
    source_census_member_ids: list[str] = Field(default_factory=list)
    mapped_source_member_ids: list[str] = Field(default_factory=list)
    unmapped_source_member_ids: list[str] = Field(default_factory=list)
    native_behavior_case_universe_fingerprint: str | None = None
    native_behavior_case_universe: list[ObservedNativeBehaviorCase] = Field(default_factory=list)
    required_native_behavior_case_ids: list[str] = Field(default_factory=list)
    mapped_native_behavior_case_ids: list[str] = Field(default_factory=list)
    unmapped_native_behavior_case_ids: list[str] = Field(default_factory=list)
    dispositioned_native_behavior_case_ids: list[str] = Field(default_factory=list)
    affected_element_ids: list[str] = Field(default_factory=list)
    external_identity_only_binding_ids: list[str] = Field(default_factory=list)
    byte_identity_only_binding_ids: list[str] = Field(default_factory=list)
    safe_claim: str
    unsafe_claim_boundary: str
    logical_report_fingerprint: str

    @field_validator("review_id", "target_system_id", "subject_revision", "first_gap_id")
    @classmethod
    def _ids_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator(
        "blueprint_fingerprint",
        "inventory_fingerprint",
        "target_inventory_authority_fingerprint",
        "provider_registry_fingerprint",
        "source_census_fingerprint",
        "native_behavior_case_universe_fingerprint",
        "logical_report_fingerprint",
    )
    @classmethod
    def _fingerprints_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _sha256(value, info.field_name)

    @field_validator(
        "affected_element_ids",
        "external_identity_only_binding_ids",
        "byte_identity_only_binding_ids",
        "global_governed_member_ids",
        "outside_scope_member_ids",
        "source_census_member_ids",
        "mapped_source_member_ids",
        "unmapped_source_member_ids",
        "required_native_behavior_case_ids",
        "mapped_native_behavior_case_ids",
        "unmapped_native_behavior_case_ids",
        "dispositioned_native_behavior_case_ids",
    )
    @classmethod
    def _affected_valid(cls, values: list[str]) -> list[str]:
        return _unique(values, "affected_element_ids")

    @field_validator("safe_claim", "unsafe_claim_boundary")
    @classmethod
    def _claims_valid(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)

    @model_validator(mode="after")
    def _review_consistent(self) -> "PhysicalModelBlueprintReview":
        expected = fingerprint_review(self)
        if self.logical_report_fingerprint != expected:
            raise ValueError("logical_report_fingerprint is stale or invalid")
        if self.status == "pass" and self.gaps:
            raise ValueError("passing blueprint reviews cannot contain gaps")
        if self.status != "pass" and not self.gaps:
            raise ValueError("non-passing blueprint reviews require gaps")
        gap_ids = [gap.gap_id for gap in self.gaps]
        if len(gap_ids) != len(set(gap_ids)):
            raise ValueError("blueprint gap ids must be unique")
        if self.first_gap_id != (gap_ids[0] if gap_ids else None):
            raise ValueError("first_gap_id must name the first deterministic gap")
        if self.understanding_target == "declared_consistency":
            if self.object_dna_readiness != "not_requested":
                raise ValueError("declared-consistency review must report object DNA as not_requested")
            if self.status != self.declared_consistency_status:
                raise ValueError("declared-consistency overall status must equal declared status")
        elif self.object_dna_readiness == "not_requested":
            raise ValueError("object-DNA review cannot report not_requested readiness")
        source_ids = set(self.source_census_member_ids)
        projected_source_ids = [item.source_member_id for item in self.source_census]
        if len(projected_source_ids) != len(set(projected_source_ids)):
            raise ValueError("source census projection ids must be unique")
        if set(projected_source_ids) != source_ids:
            raise ValueError("source census projection must exactly match source_census_member_ids")
        if set(self.mapped_source_member_ids) | set(self.unmapped_source_member_ids) != source_ids:
            raise ValueError("mapped plus unmapped source ids must equal the source census")
        if set(self.mapped_source_member_ids) & set(self.unmapped_source_member_ids):
            raise ValueError("mapped and unmapped source ids must be disjoint")
        native_case_ids = [item.native_case_id for item in self.native_behavior_case_universe]
        if len(native_case_ids) != len(set(native_case_ids)):
            raise ValueError("native behavior case universe ids must be unique")
        required_case_ids = {
            item.native_case_id for item in self.native_behavior_case_universe if item.disposition == "required"
        }
        dispositioned_case_ids = {
            item.native_case_id for item in self.native_behavior_case_universe if item.disposition == "dispositioned"
        }
        if set(self.required_native_behavior_case_ids) != required_case_ids:
            raise ValueError("required native case ids must match the adapter-owned universe")
        if set(self.dispositioned_native_behavior_case_ids) != dispositioned_case_ids:
            raise ValueError("dispositioned native case ids must match the adapter-owned universe")
        if set(self.mapped_native_behavior_case_ids) | set(self.unmapped_native_behavior_case_ids) != required_case_ids:
            raise ValueError("mapped plus unmapped native cases must equal required native cases")
        if set(self.mapped_native_behavior_case_ids) & set(self.unmapped_native_behavior_case_ids):
            raise ValueError("mapped and unmapped native case ids must be disjoint")
        if self.native_behavior_case_universe:
            universe_payload = [
                item.model_dump(mode="json", exclude_none=True)
                for item in self.native_behavior_case_universe
            ]
            if self.native_behavior_case_universe_fingerprint != canonical_blueprint_fingerprint(universe_payload):
                raise ValueError("native_behavior_case_universe_fingerprint is stale or invalid")
        elif self.native_behavior_case_universe_fingerprint is not None:
            raise ValueError("empty native behavior case universe cannot carry a fingerprint")
        if set(self.coverage.governed_member_ids) - set(self.global_governed_member_ids):
            raise ValueError("scope coverage must remain inside the global denominator")
        if set(self.coverage.governed_member_ids) & set(self.outside_scope_member_ids):
            raise ValueError("scope-governed and outside-scope members must be disjoint")
        if set(self.coverage.governed_member_ids) | set(self.outside_scope_member_ids) != set(
            self.global_governed_member_ids
        ):
            raise ValueError("scope-governed plus outside-scope members must equal the global denominator")
        return self


class BlueprintTraceNode(_StrictModel):
    node_id: str
    node_kind: str
    owner_element_id: str | None = None
    fingerprint: str | None = None

    @field_validator("node_id", "node_kind", "owner_element_id")
    @classmethod
    def _ids_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str | None) -> str | None:
        return None if value is None else _sha256(value, "node fingerprint")


class BlueprintTraceEdge(_StrictModel):
    edge_id: str
    source_id: str
    target_id: str
    relation: str
    propagates_change: bool = True

    @field_validator("edge_id", "source_id", "target_id", "relation")
    @classmethod
    def _ids_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)


class BlueprintProjection(_StrictModel):
    schema_version: Literal["physicsguard.physical-blueprint-projection.v1"] = PHYSICAL_BLUEPRINT_PROJECTION_SCHEMA
    projection_kind: ProjectionKind
    source_blueprint_fingerprint: str
    source_review_fingerprint: str
    relation_set_fingerprint: str
    projection_recipe_fingerprint: str
    target_system_id: str
    subject_revision: str
    seed_ids: list[str]
    nodes: list[BlueprintTraceNode]
    edges: list[BlueprintTraceEdge]
    included_member_ids: list[str]
    outside_scope_ids: list[str]
    gaps: list[BlueprintGap]
    first_gap_id: str | None = None
    trace_status: ReviewStatus
    terminal_input_ids: list[str] = Field(default_factory=list)
    terminal_binding_ids: list[str] = Field(default_factory=list)
    terminal_resource_ids: list[str] = Field(default_factory=list)
    source_safe_claim: str
    safe_claim: str
    projection_fingerprint: str

    @field_validator(
        "source_blueprint_fingerprint",
        "source_review_fingerprint",
        "relation_set_fingerprint",
        "projection_recipe_fingerprint",
        "projection_fingerprint",
    )
    @classmethod
    def _fingerprints_valid(cls, value: str, info) -> str:
        return _sha256(value, info.field_name)

    @field_validator("target_system_id", "subject_revision", "first_gap_id")
    @classmethod
    def _identity_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator(
        "seed_ids",
        "included_member_ids",
        "outside_scope_ids",
        "terminal_input_ids",
        "terminal_binding_ids",
        "terminal_resource_ids",
    )
    @classmethod
    def _lists_valid(cls, values: list[str], info) -> list[str]:
        return _unique(values, info.field_name)

    @field_validator("source_safe_claim", "safe_claim")
    @classmethod
    def _safe_claim_valid(cls, value: str) -> str:
        return _required_text(value, "safe_claim")

    @model_validator(mode="after")
    def _projection_valid(self) -> "BlueprintProjection":
        if self.projection_fingerprint != fingerprint_projection(self):
            raise ValueError("projection_fingerprint is stale or invalid")
        gap_ids = [gap.gap_id for gap in self.gaps]
        if self.first_gap_id != (gap_ids[0] if gap_ids else None):
            raise ValueError("first_gap_id must name the first deterministic projection gap")
        if self.trace_status == "pass" and self.gaps:
            raise ValueError("passing blueprint projection cannot contain gaps")
        if self.trace_status != "pass" and not self.gaps:
            raise ValueError("non-passing blueprint projection requires a typed gap")
        return self


def _index_unique(items: list[Any], field_name: str, item_name: str) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for item in items:
        identity = getattr(item, field_name)
        if identity in output:
            raise ValueError(f"{item_name} ids must be unique: {identity}")
        output[identity] = item
    return output


def _assert_acyclic(element: PhysicalElement, element_by_id: dict[str, PhysicalElement]) -> None:
    seen: set[str] = set()
    current = element
    while current.parent_id is not None:
        if current.element_id in seen:
            raise ValueError("physical element hierarchy cannot contain cycles")
        seen.add(current.element_id)
        current = element_by_id[current.parent_id]


def _require_exact_owned_ids(
    owned_ids: list[str],
    objects: dict[str, Any],
    owner_id: str,
    owner_field: str,
    item_name: str,
) -> None:
    for item_id in owned_ids:
        item = objects.get(item_id)
        if item is None:
            raise ValueError(f"element {owner_id} references unknown {item_name}: {item_id}")
        if getattr(item, owner_field) != owner_id:
            raise ValueError(f"element {owner_id} does not own {item_name}: {item_id}")
    declared = {item_id for item_id, item in objects.items() if getattr(item, owner_field) == owner_id}
    if set(owned_ids) != declared:
        raise ValueError(f"element {owner_id} must list every owned {item_name}")


def _validate_refinement_references(
    refinement: RefinementContract,
    ports: dict[str, PhysicalPort],
    semantics: dict[str, PhysicalSemantic],
    boundaries: dict[str, ValidityBoundary],
    bindings: dict[str, NativeBinding],
) -> None:
    for mapping in refinement.port_mappings:
        if mapping.source_port_id and mapping.source_port_id not in ports:
            raise ValueError(f"port mapping references unknown source port: {mapping.mapping_id}")
        if mapping.target_port_id not in ports:
            raise ValueError(f"port mapping references unknown target port: {mapping.mapping_id}")
        if mapping.conversion_semantic_id:
            conversion = semantics.get(mapping.conversion_semantic_id)
            if conversion is None or conversion.semantic_kind != "conversion":
                raise ValueError(f"port mapping references unknown conversion semantic: {mapping.mapping_id}")
        for binding_id in mapping.evidence_binding_ids:
            if binding_id not in bindings:
                raise ValueError(f"port mapping references unknown evidence binding: {mapping.mapping_id}")
    for contribution in refinement.semantic_contributions:
        if contribution.child_semantic_id not in semantics or contribution.parent_semantic_id not in semantics:
            raise ValueError(f"semantic contribution references unknown semantic: {contribution.contribution_id}")
        for binding_id in contribution.evidence_binding_ids:
            if binding_id not in bindings:
                raise ValueError(f"semantic contribution references unknown evidence binding: {contribution.contribution_id}")
    for boundary_id in refinement.propagated_validity_boundary_ids:
        if boundary_id not in boundaries:
            raise ValueError(f"refinement references unknown validity boundary: {boundary_id}")
    for port_id in (*refinement.child_local_state_ids, *refinement.terminal_output_ids, *refinement.terminal_effect_ids):
        if port_id not in ports:
            raise ValueError(f"refinement disposition references unknown port: {port_id}")


def _reject_secret_fields(value: Any, path: str = "blueprint") -> None:
    forbidden = ("password", "secret", "credential", "api_key", "private_key", "access_token")
    if isinstance(value, Mapping):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in forbidden):
                raise ValueError(f"secret-sensitive field is forbidden: {path}.{key}")
            _reject_secret_fields(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_secret_fields(nested, f"{path}[{index}]")


__all__ = [
    "ArtifactReference",
    "BlueprintCoverage",
    "BlueprintGap",
    "BlueprintLayerName",
    "BlueprintLayerResult",
    "BlueprintProjection",
    "BlueprintTraceEdge",
    "BlueprintTraceNode",
    "IndependentInventory",
    "InventoryMember",
    "NativeBinding",
    "NativeExecutionEvidence",
    "NativeValueBinding",
    "ObservedSourceMember",
    "PHYSICAL_BLUEPRINT_PROJECTION_SCHEMA",
    "PHYSICAL_MODEL_BLUEPRINT_REVIEW_SCHEMA",
    "PHYSICAL_MODEL_BLUEPRINT_SCHEMA",
    "PhysicalElement",
    "PhysicalBehaviorCase",
    "PhysicalModelBlueprint",
    "PhysicalModelBlueprintReview",
    "PhysicalPort",
    "PhysicalSemantic",
    "PortMapping",
    "ProviderBindingObservation",
    "ProviderResult",
    "RefinementContract",
    "SemanticContribution",
    "SourceModelMapping",
    "TargetIdentity",
    "UnresolvedPhysicalRelation",
    "ValidityBoundary",
    "canonical_blueprint_fingerprint",
    "canonical_blueprint_json",
    "fingerprint_blueprint",
    "fingerprint_physical_behavior_case",
    "fingerprint_inventory",
    "fingerprint_native_execution_evidence",
    "fingerprint_projection",
    "fingerprint_provider_binding_observation",
    "fingerprint_review",
]
