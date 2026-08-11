"""Provider-neutral native object-DNA observation contracts.

The physical blueprint reviewer must not know whether an observed object came
from FMI, a structured document, an experiment, or another tool.  This module
is the narrow interchange boundary between those adapters and the reviewer.
Adapters own observation and replay; the reviewer only consumes the frozen,
content-addressed result below.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.physical_model_blueprint import (
    ObservedNativeBehaviorCase,
    ObservedSourceMember,
    canonical_blueprint_fingerprint,
)


NATIVE_OBJECT_DNA_OBSERVATION_SCHEMA = "physicsguard.native-object-dna-observation.v1"
NATIVE_OBJECT_DNA_RESULT_SCHEMA = NATIVE_OBJECT_DNA_OBSERVATION_SCHEMA
NATIVE_OBJECT_DNA_PROFILES = ("fmi.v1", "structured-object.v1")

ObjectDnaProfile = Literal["fmi.v1", "structured-object.v1"]
NativeObjectDnaStatus = Literal["pass", "incomplete", "stale", "blocked"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    normalized = value.strip()
    if any(character.isspace() for character in normalized):
        raise ValueError(f"{field_name} cannot contain whitespace")
    return normalized


def _description(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return " ".join(value.strip().split())


def _sha256(value: str, field_name: str) -> str:
    normalized = _text(value, field_name).lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError(f"{field_name} must be a lowercase 64-character sha256 digest")
    return normalized


def _finite_tree(value: Any, field_name: str = "value") -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise ValueError(f"{field_name} must contain only finite numbers")
        return value
    if isinstance(value, list):
        return [_finite_tree(item, field_name) for item in value]
    if isinstance(value, dict):
        return {str(key): _finite_tree(item, f"{field_name}.{key}") for key, item in value.items()}
    if value is None or isinstance(value, str):
        return value
    raise ValueError(f"{field_name} contains an unsupported value type")


def _without_none(value: Any) -> Any:
    """Canonicalize nested mappings exactly like strict model dumps."""

    if isinstance(value, BaseModel):
        return _without_none(value.model_dump(mode="json", exclude_none=True))
    if isinstance(value, Mapping):
        return {
            str(key): _without_none(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [_without_none(item) for item in value]
    if isinstance(value, tuple):
        return [_without_none(item) for item in value]
    return value


def fingerprint_native_object_dna_source_census(value: Any) -> str:
    rows = [
        _without_none(item)
        for item in value
    ]
    return canonical_blueprint_fingerprint(rows)


def fingerprint_native_object_dna_case_universe(value: Any) -> str:
    rows = [
        _without_none(item)
        for item in value
    ]
    return canonical_blueprint_fingerprint(rows)


def fingerprint_native_object_dna_case_result(value: Any) -> str:
    payload = _without_none(value)
    payload.pop("result_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


def fingerprint_native_object_dna_observation(value: Any) -> str:
    payload = _without_none(value)
    payload.pop("observation_fingerprint", None)
    return canonical_blueprint_fingerprint(payload)


class NativeObjectDnaCaseResult(_StrictModel):
    """One adapter-owned terminal result for a native behavior case."""

    native_case_id: str
    status: NativeObjectDnaStatus
    terminal_status: str
    observed_values: dict[str, float] = Field(default_factory=dict)
    result_fingerprint: str

    @field_validator("native_case_id", "terminal_status")
    @classmethod
    def _ids(cls, value: str, info) -> str:
        return _text(value, info.field_name)

    @field_validator("observed_values")
    @classmethod
    def _values(cls, value: dict[str, float]) -> dict[str, float]:
        for key, item in value.items():
            if not isinstance(key, str) or not key.strip() or not math.isfinite(float(item)):
                raise ValueError("observed_values must map names to finite numbers")
        return value

    @field_validator("result_fingerprint")
    @classmethod
    def _fingerprint(cls, value: str) -> str:
        return _sha256(value, "result_fingerprint")

    @model_validator(mode="after")
    def _consistent(self) -> "NativeObjectDnaCaseResult":
        if self.result_fingerprint != fingerprint_native_object_dna_case_result(self):
            raise ValueError("result_fingerprint is stale or invalid")
        return self


class NativeObjectDnaObservation(_StrictModel):
    """The single provider-neutral object-DNA result consumed by review."""

    schema_version: Literal["physicsguard.native-object-dna-observation.v1"] = NATIVE_OBJECT_DNA_OBSERVATION_SCHEMA
    observation_id: str
    provider_id: str
    provider_kind: str
    provider_version: str
    profile: ObjectDnaProfile
    target_system_id: str
    subject_revision: str
    object_id: str
    boundary_fingerprint: str
    source_census: list[ObservedSourceMember] = Field(default_factory=list)
    source_census_fingerprint: str
    behavior_case_universe: list[ObservedNativeBehaviorCase] = Field(default_factory=list)
    behavior_case_universe_fingerprint: str | None = None
    behavior_case_results: list[NativeObjectDnaCaseResult] = Field(default_factory=list)
    status: NativeObjectDnaStatus
    first_gap_code: str | None = None
    findings: list[str] = Field(default_factory=list)
    safe_claim: str
    claim_boundary: str
    observation_fingerprint: str

    @field_validator(
        "observation_id",
        "provider_id",
        "provider_kind",
        "provider_version",
        "target_system_id",
        "subject_revision",
        "object_id",
    )
    @classmethod
    def _ids(cls, value: str, info) -> str:
        return _text(value, info.field_name)

    @field_validator("boundary_fingerprint", "source_census_fingerprint", "behavior_case_universe_fingerprint", "observation_fingerprint")
    @classmethod
    def _fingerprints(cls, value: str | None, info) -> str | None:
        return None if value is None else _sha256(value, info.field_name)

    @field_validator("first_gap_code")
    @classmethod
    def _gap_code(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, "first_gap_code")

    @field_validator("safe_claim", "claim_boundary")
    @classmethod
    def _claims(cls, value: str, info) -> str:
        return _description(value, info.field_name)

    @field_validator("findings")
    @classmethod
    def _findings(cls, value: list[str]) -> list[str]:
        return [_description(item, "finding") for item in value]

    @model_validator(mode="after")
    def _consistent(self) -> "NativeObjectDnaObservation":
        source_ids = [item.source_member_id for item in self.source_census]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source census member ids must be unique")
        if self.source_census_fingerprint != fingerprint_native_object_dna_source_census(self.source_census):
            raise ValueError("source_census_fingerprint is stale or invalid")
        case_ids = [item.native_case_id for item in self.behavior_case_universe]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("native behavior case ids must be unique")
        if self.behavior_case_universe:
            expected = fingerprint_native_object_dna_case_universe(self.behavior_case_universe)
            if self.behavior_case_universe_fingerprint != expected:
                raise ValueError("behavior_case_universe_fingerprint is stale or invalid")
        elif self.behavior_case_universe_fingerprint is not None:
            raise ValueError("empty behavior case universe cannot carry a fingerprint")
        result_ids = [item.native_case_id for item in self.behavior_case_results]
        if len(result_ids) != len(set(result_ids)):
            raise ValueError("native behavior case result ids must be unique")
        if not set(result_ids) <= set(case_ids):
            raise ValueError("native behavior case results must refer to the observed case universe")
        if self.status == "pass" and self.first_gap_code is not None:
            raise ValueError("passing native object-DNA observations cannot contain a first gap")
        if self.status != "pass" and self.first_gap_code is None:
            raise ValueError("non-passing native object-DNA observations require first_gap_code")
        if self.observation_fingerprint != fingerprint_native_object_dna_observation(self):
            raise ValueError("observation_fingerprint is stale or invalid")
        return self


def build_native_object_dna_observation(payload: Mapping[str, Any]) -> NativeObjectDnaObservation:
    """Validate and fingerprint one neutral observation payload."""

    value = dict(payload)
    value.setdefault("schema_version", NATIVE_OBJECT_DNA_OBSERVATION_SCHEMA)
    value.setdefault("source_census", [])
    value.setdefault("behavior_case_universe", [])
    value.setdefault("behavior_case_results", [])
    value.setdefault("findings", [])
    if "source_census_fingerprint" not in value:
        value["source_census_fingerprint"] = fingerprint_native_object_dna_source_census(value["source_census"])
    if value.get("behavior_case_universe") and "behavior_case_universe_fingerprint" not in value:
        value["behavior_case_universe_fingerprint"] = fingerprint_native_object_dna_case_universe(value["behavior_case_universe"])
    if "observation_fingerprint" not in value:
        value["observation_fingerprint"] = fingerprint_native_object_dna_observation(value)
    return NativeObjectDnaObservation.model_validate(value)


def native_object_dna_from_fmi_result(payload: Mapping[str, Any]) -> NativeObjectDnaObservation:
    """Project an FMI result into the neutral contract without reviewer branching."""

    source_census: list[dict[str, Any]] = []
    for item in payload.get("source_census", []):
        row = dict(item)
        # Preserve the first adapter's typed FMI contract while also exposing
        # a provider-neutral interface field for the common reviewer path.
        fmi_contract = row.get("fmi_variable_contract")
        if isinstance(fmi_contract, dict) and "interface_contract" not in row:
            row["interface_contract"] = {
                "source_name": fmi_contract.get("variable_name"),
                "source_type": fmi_contract.get("variable_type"),
                "unit": fmi_contract.get("unit"),
                "physical_quantity_id": fmi_contract.get("physical_quantity_id"),
                "state_role": fmi_contract.get("source_state_role"),
                "value_reference": fmi_contract.get("value_reference"),
                "derivative_reference": fmi_contract.get("derivative_of_value_reference"),
                "reinit": fmi_contract.get("reinit"),
            }
        source_census.append(row)
    results = []
    for item in payload.get("behavior_case_results", []):
        row = dict(item)
        row.setdefault("native_case_id", row.get("case_id"))
        row.setdefault("terminal_status", row.get("terminal_status", "unknown"))
        row.setdefault("observed_values", row.get("observed_values", {}))
        row.setdefault("result_fingerprint", fingerprint_native_object_dna_case_result(row))
        results.append(row)
    value = {
        "schema_version": NATIVE_OBJECT_DNA_OBSERVATION_SCHEMA,
        "observation_id": payload.get("observation_id"),
        "provider_id": payload.get("provider_id", "physicsguard.fmi-observation"),
        "provider_kind": payload.get("provider_kind", "fmi"),
        "provider_version": payload.get("provider_version")
        or payload.get("fmi_version")
        or "1",
        "profile": "fmi.v1",
        "target_system_id": payload.get("target_system_id"),
        "subject_revision": payload.get("subject_revision"),
        "object_id": payload.get("model_identifier") or payload.get("observation_id"),
        "boundary_fingerprint": payload.get("request_fingerprint"),
        "source_census": source_census,
        "source_census_fingerprint": fingerprint_native_object_dna_source_census(source_census),
        "behavior_case_universe": payload.get("behavior_case_universe", []),
        "behavior_case_universe_fingerprint": payload.get("behavior_case_universe_fingerprint"),
        "behavior_case_results": results,
        "status": payload.get("status"),
        "first_gap_code": payload.get("first_gap_code"),
        "findings": payload.get("findings", []),
        "safe_claim": payload.get("safe_claim"),
        "claim_boundary": payload.get("claim_boundary"),
    }
    value["observation_fingerprint"] = fingerprint_native_object_dna_observation(value)
    return build_native_object_dna_observation(value)


def load_native_object_dna_observation(path: str | Path) -> NativeObjectDnaObservation:
    """Load one exact YAML/JSON neutral observation document."""

    from physicsguard.io.test_file_contract_loader import load_spec

    return load_spec(Path(path), NativeObjectDnaObservation)


__all__ = [
    "NATIVE_OBJECT_DNA_OBSERVATION_SCHEMA",
    "NATIVE_OBJECT_DNA_RESULT_SCHEMA",
    "NATIVE_OBJECT_DNA_PROFILES",
    "NativeObjectDnaCaseResult",
    "NativeObjectDnaObservation",
    "build_native_object_dna_observation",
    "fingerprint_native_object_dna_case_result",
    "fingerprint_native_object_dna_case_universe",
    "fingerprint_native_object_dna_observation",
    "fingerprint_native_object_dna_source_census",
    "load_native_object_dna_observation",
    "native_object_dna_from_fmi_result",
]
