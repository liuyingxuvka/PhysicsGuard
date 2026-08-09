"""Strict, provider-neutral contracts for observing one FMI exchange package.

The request freezes independently supplied source and byte identities.  The
observer verifies those identities and, when requested, exercises only the
standard FMI interface declared by the package.  Neither request nor result
licenses the publisher identity, the physical truth of the equations, or an
empirical-equivalence claim.
"""

from __future__ import annotations

import math
from pathlib import PurePosixPath
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.physical_model_blueprint import (
    FmiSourceStateRole,
    FmiVariableSemanticContract,
    ObservedNativeBehaviorCase,
    ObservedSemanticSelector,
    SemanticKind,
    canonical_blueprint_fingerprint,
)


FMI_OBSERVATION_REQUEST_SCHEMA = "physicsguard.fmi-observation-request.v1"
FMI_OBSERVATION_RESULT_SCHEMA = "physicsguard.fmi-observation-result.v1"

FmiObservationStatus = Literal["pass", "incomplete", "blocked"]
FmiCaseOperation = Literal["read_after_initialization", "event_update", "rejected_set"]
FmiTerminalStatus = Literal["ok", "warning", "discard", "error", "fatal", "pending"]
FmiSourceCensusKind = Literal["artifact", "archive_member", "variable", "native_case", "semantic_fact"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    return normalized


def _stable_id(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name)
    if any(character.isspace() for character in normalized):
        raise ValueError(f"{field_name} cannot contain whitespace")
    return normalized


def _sha256(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name).lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError(f"{field_name} must be a lowercase 64-character sha256 digest")
    return normalized


def _relative_path(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name).replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or (path.parts and ":" in path.parts[0]):
        raise ValueError(f"{field_name} must be a forward-relative path")
    return path.as_posix()


def _finite(value: float, field_name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


def fingerprint_fmi_observation_request(value: Any) -> str:
    payload = value.model_dump(mode="json", exclude_none=False) if isinstance(value, BaseModel) else dict(value)
    payload.pop("request_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


def fingerprint_fmi_observation_result(value: Any) -> str:
    payload = value.model_dump(mode="json", exclude_none=False) if isinstance(value, BaseModel) else dict(value)
    payload.pop("result_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


def fingerprint_fmi_source_census(value: Any) -> str:
    payload = [
        item.model_dump(mode="json", exclude_none=True) if isinstance(item, BaseModel) else dict(item)
        for item in value
    ]
    return canonical_blueprint_fingerprint(payload)


def fingerprint_fmi_behavior_case_universe(value: Any) -> str:
    payload = [
        item.model_dump(mode="json", exclude_none=True) if isinstance(item, BaseModel) else dict(item)
        for item in value
    ]
    return canonical_blueprint_fingerprint(payload)


def normalize_fmi_source_fragment(value: str) -> str:
    return " ".join(_required_text(value, "source_fragment").split())


class FmiSourceIdentity(_StrictModel):
    provider_id: str
    source_uri: str
    release_uri: str
    release_version: str
    license_id: str
    claim_boundary: str

    @field_validator("provider_id", "release_version", "license_id")
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("source_uri", "release_uri")
    @classmethod
    def _uri_valid(cls, value: str, info) -> str:
        normalized = _required_text(value, info.field_name)
        if not normalized.startswith(("https://", "http://")):
            raise ValueError(f"{info.field_name} must be an explicit HTTP(S) source identity")
        return normalized

    @field_validator("claim_boundary")
    @classmethod
    def _claim_valid(cls, value: str) -> str:
        return _required_text(value, "claim_boundary")


class FmiArtifactExpectation(_StrictModel):
    artifact_id: str
    role: Literal["release_archive", "fmu", "license", "supporting"]
    relative_path: str
    sha256: str
    size_bytes: int = Field(ge=0)
    container_artifact_id: str | None = None
    container_member_path: str | None = None

    @field_validator("artifact_id", "container_artifact_id")
    @classmethod
    def _identity_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _stable_id(value, info.field_name)

    @field_validator("relative_path", "container_member_path")
    @classmethod
    def _path_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _relative_path(value, info.field_name)

    @field_validator("sha256")
    @classmethod
    def _sha_valid(cls, value: str) -> str:
        return _sha256(value, "sha256")

    @model_validator(mode="after")
    def _container_consistent(self) -> "FmiArtifactExpectation":
        if (self.container_artifact_id is None) != (self.container_member_path is None):
            raise ValueError("container_artifact_id and container_member_path must be supplied together")
        if self.container_artifact_id == self.artifact_id:
            raise ValueError("an artifact cannot contain itself")
        return self


class FmiMemberExpectation(_StrictModel):
    member_id: str
    role: Literal["model_description", "source", "documentation", "result", "binary", "resource", "other"]
    member_path: str
    sha256: str
    size_bytes: int = Field(ge=0)

    @field_validator("member_id")
    @classmethod
    def _identity_valid(cls, value: str) -> str:
        return _stable_id(value, "member_id")

    @field_validator("member_path")
    @classmethod
    def _path_valid(cls, value: str) -> str:
        return _relative_path(value, "member_path")

    @field_validator("sha256")
    @classmethod
    def _sha_valid(cls, value: str) -> str:
        return _sha256(value, "sha256")


class FmiVariableExpectation(_StrictModel):
    variable_name: str
    value_reference: int = Field(ge=0)
    variable_type: str
    causality: str
    variability: str
    unit: str | None = None
    start: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    derivative_of_value_reference: int | None = Field(default=None, ge=0)
    reinit: bool | None = None
    physical_quantity_id: str | None = None
    source_state_role: FmiSourceStateRole | None = None

    @field_validator("variable_name", "variable_type", "causality", "variability", "unit", "physical_quantity_id")
    @classmethod
    def _text_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _required_text(value, info.field_name)

    @field_validator("start", "minimum", "maximum")
    @classmethod
    def _number_valid(cls, value: float | None, info) -> float | None:
        return None if value is None else _finite(value, info.field_name)

    @model_validator(mode="after")
    def _bounds_consistent(self) -> "FmiVariableExpectation":
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum cannot exceed maximum")
        return self


class FmiSemanticSelectorExpectation(_StrictModel):
    """One exact source fragment the FMI adapter must resolve independently."""

    selector_id: str
    source_member_id: str
    function_name: str
    source_fragment: str
    semantic_kind: SemanticKind
    semantic_statement: str
    semantic_expression: str | None = None
    claim_boundary: str

    @field_validator("selector_id", "source_member_id")
    @classmethod
    def _ids_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("function_name", "semantic_statement", "semantic_expression", "claim_boundary")
    @classmethod
    def _text_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _required_text(value, info.field_name)

    @field_validator("source_fragment")
    @classmethod
    def _fragment_valid(cls, value: str) -> str:
        return normalize_fmi_source_fragment(value)


class FmiFloat64Assignment(_StrictModel):
    variable_name: str
    value: float

    @field_validator("variable_name")
    @classmethod
    def _name_valid(cls, value: str) -> str:
        return _required_text(value, "variable_name")

    @field_validator("value")
    @classmethod
    def _value_valid(cls, value: float) -> float:
        return _finite(value, "value")


class FmiExpectedFloat64(_StrictModel):
    variable_name: str
    value: float
    absolute_tolerance: float = Field(default=0.0, ge=0.0)

    @field_validator("variable_name")
    @classmethod
    def _name_valid(cls, value: str) -> str:
        return _required_text(value, "variable_name")

    @field_validator("value", "absolute_tolerance")
    @classmethod
    def _value_valid(cls, value: float, info) -> float:
        return _finite(value, info.field_name)


class FmiOracleExpression(_StrictModel):
    result_name: str
    expression: str

    @field_validator("result_name")
    @classmethod
    def _result_name_valid(cls, value: str) -> str:
        normalized = _stable_id(value, "result_name")
        if not normalized.isidentifier():
            raise ValueError("result_name must be a restricted-expression identifier")
        return normalized

    @field_validator("expression")
    @classmethod
    def _expression_valid(cls, value: str) -> str:
        return _required_text(value, "expression")


class FmiOracleDefinition(_StrictModel):
    oracle_id: str
    purpose: str
    input_names: list[str]
    expressions: list[FmiOracleExpression]
    source_member_ids: list[str]
    claim_boundary: str

    @field_validator("oracle_id")
    @classmethod
    def _oracle_id_valid(cls, value: str) -> str:
        return _stable_id(value, "oracle_id")

    @field_validator("purpose", "claim_boundary")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)

    @field_validator("input_names", "source_member_ids")
    @classmethod
    def _lists_valid(cls, value: list[str], info) -> list[str]:
        normalized = [_stable_id(item, info.field_name) for item in value]
        if info.field_name == "input_names" and any(not item.isidentifier() for item in normalized):
            raise ValueError("oracle input_names must be restricted-expression identifiers")
        if not normalized or len(normalized) != len(set(normalized)):
            raise ValueError(f"{info.field_name} must be non-empty and unique")
        return normalized

    @model_validator(mode="after")
    def _oracle_consistent(self) -> "FmiOracleDefinition":
        result_names = [item.result_name for item in self.expressions]
        if len(result_names) != len(set(result_names)):
            raise ValueError("oracle expression result names must be unique")
        if set(result_names) & set(self.input_names):
            raise ValueError("oracle expression results cannot replace frozen inputs")
        return self


class FmiBehaviorCase(_StrictModel):
    case_id: str
    operation: FmiCaseOperation
    independent_oracle_id: str
    oracle_input_bindings: dict[str, str] = Field(default_factory=dict)
    oracle_output_bindings: dict[str, str] = Field(default_factory=dict)
    purpose: str
    start_time: float = 0.0
    assignments: list[FmiFloat64Assignment]
    read_variable_names: list[str]
    expected_values: list[FmiExpectedFloat64]
    expected_terminal_status: FmiTerminalStatus

    @field_validator("case_id", "independent_oracle_id")
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("purpose")
    @classmethod
    def _purpose_valid(cls, value: str) -> str:
        return _required_text(value, "purpose")

    @field_validator("oracle_input_bindings", "oracle_output_bindings")
    @classmethod
    def _oracle_bindings_valid(cls, value: dict[str, str], info) -> dict[str, str]:
        output: dict[str, str] = {}
        for expression_name, variable_name in value.items():
            normalized_name = _required_text(expression_name, info.field_name)
            normalized_value = _required_text(variable_name, info.field_name)
            if info.field_name == "oracle_input_bindings":
                if not normalized_name.isidentifier():
                    raise ValueError("oracle_input_bindings keys must be restricted-expression identifiers")
            elif not normalized_value.isidentifier():
                raise ValueError("oracle_output_bindings values must be restricted-expression identifiers")
            output[normalized_name] = normalized_value
        return output

    @field_validator("start_time")
    @classmethod
    def _time_valid(cls, value: float) -> float:
        return _finite(value, "start_time")

    @field_validator("read_variable_names")
    @classmethod
    def _reads_valid(cls, value: list[str]) -> list[str]:
        normalized = [_required_text(item, "read_variable_names") for item in value]
        if len(normalized) != len(set(normalized)):
            raise ValueError("read_variable_names must be unique")
        return normalized

    @model_validator(mode="after")
    def _case_consistent(self) -> "FmiBehaviorCase":
        assignment_names = [item.variable_name for item in self.assignments]
        expected_names = [item.variable_name for item in self.expected_values]
        if len(assignment_names) != len(set(assignment_names)):
            raise ValueError("assignments must use unique variable names")
        if len(expected_names) != len(set(expected_names)):
            raise ValueError("expected_values must use unique variable names")
        if not set(expected_names).issubset(self.read_variable_names):
            raise ValueError("every expected value must be included in read_variable_names")
        if self.operation == "rejected_set" and self.expected_terminal_status not in {"error", "fatal"}:
            raise ValueError("rejected_set must expect an error or fatal FMI status")
        if self.operation != "rejected_set" and self.expected_terminal_status not in {"ok", "warning"}:
            raise ValueError("successful read/event cases must expect ok or warning")
        return self


class FmiObservationRequest(_StrictModel):
    schema_version: Literal["physicsguard.fmi-observation-request.v1"] = FMI_OBSERVATION_REQUEST_SCHEMA
    observation_id: str
    target_system_id: str
    subject_revision: str
    source: FmiSourceIdentity
    fmi_version: str
    interface_kind: Literal["model_exchange"]
    expected_model_name: str
    expected_model_identifier: str
    artifacts: list[FmiArtifactExpectation]
    fmu_artifact_id: str
    expected_members: list[FmiMemberExpectation]
    expected_variables: list[FmiVariableExpectation]
    semantic_selectors: list[FmiSemanticSelectorExpectation] = Field(default_factory=list)
    oracles: list[FmiOracleDefinition] = Field(default_factory=list)
    behavior_cases: list[FmiBehaviorCase]
    request_fingerprint: str

    @field_validator(
        "observation_id",
        "target_system_id",
        "subject_revision",
        "fmi_version",
        "expected_model_identifier",
        "fmu_artifact_id",
    )
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("expected_model_name")
    @classmethod
    def _model_name_valid(cls, value: str) -> str:
        return _required_text(value, "expected_model_name")

    @field_validator("request_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "request_fingerprint")

    @model_validator(mode="after")
    def _request_consistent(self) -> "FmiObservationRequest":
        artifact_ids = [item.artifact_id for item in self.artifacts]
        member_ids = [item.member_id for item in self.expected_members]
        member_paths = [item.member_path for item in self.expected_members]
        variable_names = [item.variable_name for item in self.expected_variables]
        variable_references = [item.value_reference for item in self.expected_variables]
        case_ids = [item.case_id for item in self.behavior_cases]
        oracle_ids = [item.oracle_id for item in self.oracles]
        selector_ids = [item.selector_id for item in self.semantic_selectors]
        for values, label in (
            (artifact_ids, "artifact ids"),
            (member_ids, "member ids"),
            (member_paths, "member paths"),
            (variable_names, "variable names"),
            (variable_references, "variable value references"),
            (case_ids, "behavior case ids"),
            (oracle_ids, "oracle ids"),
            (selector_ids, "semantic selector ids"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must be unique")
        artifacts_by_id = {item.artifact_id: item for item in self.artifacts}
        fmu_artifact = artifacts_by_id.get(self.fmu_artifact_id)
        if fmu_artifact is None or fmu_artifact.role != "fmu":
            raise ValueError("fmu_artifact_id must identify one declared FMI artifact")
        for artifact in self.artifacts:
            if artifact.container_artifact_id is not None:
                container = artifacts_by_id.get(artifact.container_artifact_id)
                if container is None or container.role != "release_archive":
                    raise ValueError("container_artifact_id must identify a declared release archive")
        declared_variables = set(variable_names)
        declared_members = set(member_ids)
        foreign_selector_members = sorted(
            {item.source_member_id for item in self.semantic_selectors} - declared_members
        )
        if foreign_selector_members:
            raise ValueError(f"semantic selectors reference undeclared members: {foreign_selector_members}")
        oracles_by_id = {item.oracle_id: item for item in self.oracles}
        for oracle in self.oracles:
            foreign_members = sorted(set(oracle.source_member_ids) - declared_members)
            if foreign_members:
                raise ValueError(f"oracle {oracle.oracle_id!r} references undeclared members: {foreign_members}")
        for case in self.behavior_cases:
            used = {
                *(item.variable_name for item in case.assignments),
                *case.read_variable_names,
                *(item.variable_name for item in case.expected_values),
            }
            foreign = sorted(used - declared_variables)
            if foreign:
                raise ValueError(f"behavior case {case.case_id!r} uses undeclared variables: {foreign}")
            oracle = oracles_by_id.get(case.independent_oracle_id)
            if oracle is None:
                raise ValueError(f"behavior case {case.case_id!r} references an undeclared oracle")
            if set(case.oracle_input_bindings) != set(oracle.input_names):
                raise ValueError(f"behavior case {case.case_id!r} must bind every oracle input exactly")
            foreign_oracle_variables = sorted(
                (
                    set(case.oracle_input_bindings.values())
                    | set(case.oracle_output_bindings)
                )
                - declared_variables
            )
            if foreign_oracle_variables:
                raise ValueError(
                    f"behavior case {case.case_id!r} has foreign oracle variable bindings: {foreign_oracle_variables}"
                )
            oracle_results = {item.result_name for item in oracle.expressions}
            foreign_results = sorted(set(case.oracle_output_bindings.values()) - oracle_results)
            if foreign_results:
                raise ValueError(f"behavior case {case.case_id!r} references unknown oracle results: {foreign_results}")
            expected_names = {item.variable_name for item in case.expected_values}
            if expected_names != set(case.oracle_output_bindings):
                raise ValueError(
                    f"behavior case {case.case_id!r} must bind every expected value to one oracle result"
                )
        if self.request_fingerprint != fingerprint_fmi_observation_request(self):
            raise ValueError("request_fingerprint is stale or invalid")
        return self


class FmiArtifactObservation(_StrictModel):
    artifact_id: str
    role: str
    relative_path: str
    expected_sha256: str
    actual_sha256: str | None
    expected_size_bytes: int = Field(ge=0)
    actual_size_bytes: int | None = Field(default=None, ge=0)
    container_artifact_id: str | None = None
    container_member_path: str | None = None
    status: FmiObservationStatus
    findings: list[str]

    @field_validator("relative_path", "container_member_path")
    @classmethod
    def _path_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _relative_path(value, info.field_name)


class FmiMemberObservation(_StrictModel):
    member_id: str
    role: str
    member_path: str
    expected_sha256: str
    actual_sha256: str | None
    expected_size_bytes: int = Field(ge=0)
    actual_size_bytes: int | None = Field(default=None, ge=0)
    status: FmiObservationStatus
    findings: list[str]

    @field_validator("member_path")
    @classmethod
    def _path_valid(cls, value: str) -> str:
        return _relative_path(value, "member_path")


class FmiVariableObservation(_StrictModel):
    variable_name: str
    value_reference: int = Field(ge=0)
    variable_type: str
    causality: str
    variability: str
    unit: str | None = None
    start: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    derivative_of_value_reference: int | None = Field(default=None, ge=0)
    reinit: bool | None = None
    status: FmiObservationStatus
    findings: list[str]


class FmiBehaviorCaseResult(_StrictModel):
    case_id: str
    operation: FmiCaseOperation
    independent_oracle_id: str
    terminal_status: FmiTerminalStatus
    oracle_values: dict[str, float]
    observed_values: dict[str, float]
    status: FmiObservationStatus
    findings: list[str]

    @field_validator("oracle_values", "observed_values")
    @classmethod
    def _observed_values_valid(cls, value: dict[str, float]) -> dict[str, float]:
        return {key: _finite(item, f"observed_values.{key}") for key, item in value.items()}


class FmiSourceCensusMember(_StrictModel):
    """One source fact observed from governed bytes or a replayed native contract."""

    source_member_id: str
    source_kind: FmiSourceCensusKind
    locator: str
    role: str
    member_fingerprint: str
    semantic_expression: str | None = None
    fmi_variable_contract: FmiVariableSemanticContract | None = None
    semantic_selectors: list[ObservedSemanticSelector] = Field(default_factory=list)

    @field_validator("source_member_id")
    @classmethod
    def _id_valid(cls, value: str) -> str:
        return _stable_id(value, "source_member_id")

    @field_validator("locator", "role", "semantic_expression")
    @classmethod
    def _text_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _required_text(value, info.field_name)

    @field_validator("member_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "member_fingerprint")

    @model_validator(mode="after")
    def _selectors_unique(self) -> "FmiSourceCensusMember":
        selector_ids = [item.selector_id for item in self.semantic_selectors]
        if len(selector_ids) != len(set(selector_ids)):
            raise ValueError("semantic selector ids must be unique within one source member")
        return self


class FmiObservationResult(_StrictModel):
    schema_version: Literal["physicsguard.fmi-observation-result.v1"] = FMI_OBSERVATION_RESULT_SCHEMA
    observation_id: str
    target_system_id: str
    subject_revision: str
    request_fingerprint: str
    source: FmiSourceIdentity
    fmi_version: str | None
    model_name: str | None
    model_identifier: str | None
    instantiation_token: str | None
    supported_interface_kinds: list[str]
    artifact_observations: list[FmiArtifactObservation]
    member_observations: list[FmiMemberObservation]
    variable_observations: list[FmiVariableObservation]
    behavior_case_results: list[FmiBehaviorCaseResult]
    behavior_case_universe: list[ObservedNativeBehaviorCase] = Field(default_factory=list)
    behavior_case_universe_fingerprint: str | None = None
    source_census: list[FmiSourceCensusMember]
    source_census_fingerprint: str
    status: FmiObservationStatus
    first_gap_code: str | None
    findings: list[str]
    safe_claim: str
    claim_boundary: str
    result_fingerprint: str

    @field_validator(
        "request_fingerprint",
        "source_census_fingerprint",
        "behavior_case_universe_fingerprint",
        "result_fingerprint",
    )
    @classmethod
    def _fingerprint_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _sha256(value, info.field_name)

    @model_validator(mode="after")
    def _result_consistent(self) -> "FmiObservationResult":
        source_ids = [item.source_member_id for item in self.source_census]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("FMI source census member ids must be unique")
        if self.source_census_fingerprint != fingerprint_fmi_source_census(self.source_census):
            raise ValueError("source_census_fingerprint is stale or invalid")
        native_case_ids = [item.native_case_id for item in self.behavior_case_universe]
        if len(native_case_ids) != len(set(native_case_ids)):
            raise ValueError("FMI native behavior case universe ids must be unique")
        if self.behavior_case_universe:
            if self.behavior_case_universe_fingerprint != fingerprint_fmi_behavior_case_universe(
                self.behavior_case_universe
            ):
                raise ValueError("behavior_case_universe_fingerprint is stale or invalid")
        elif self.behavior_case_universe_fingerprint is not None:
            raise ValueError("empty behavior case universe cannot carry a fingerprint")
        if self.status == "pass" and self.first_gap_code is not None:
            raise ValueError("passing FMI observation cannot contain a first gap")
        if self.status != "pass" and self.first_gap_code is None:
            raise ValueError("non-passing FMI observation requires first_gap_code")
        if self.result_fingerprint != fingerprint_fmi_observation_result(self):
            raise ValueError("result_fingerprint is stale or invalid")
        return self


def build_fmi_observation_request(payload: Mapping[str, Any]) -> FmiObservationRequest:
    value = dict(payload)
    value.setdefault("oracles", [])
    value.setdefault("semantic_selectors", [])
    value["request_fingerprint"] = fingerprint_fmi_observation_request(value)
    return FmiObservationRequest.model_validate(value)


__all__ = [
    "FMI_OBSERVATION_REQUEST_SCHEMA",
    "FMI_OBSERVATION_RESULT_SCHEMA",
    "FmiArtifactExpectation",
    "FmiArtifactObservation",
    "FmiBehaviorCase",
    "FmiBehaviorCaseResult",
    "FmiExpectedFloat64",
    "FmiFloat64Assignment",
    "FmiMemberExpectation",
    "FmiMemberObservation",
    "FmiObservationRequest",
    "FmiObservationResult",
    "FmiSourceIdentity",
    "FmiSourceCensusMember",
    "FmiSemanticSelectorExpectation",
    "FmiOracleDefinition",
    "FmiOracleExpression",
    "FmiVariableExpectation",
    "FmiVariableObservation",
    "build_fmi_observation_request",
    "fingerprint_fmi_observation_request",
    "fingerprint_fmi_observation_result",
    "fingerprint_fmi_source_census",
    "fingerprint_fmi_behavior_case_universe",
    "normalize_fmi_source_fragment",
]
