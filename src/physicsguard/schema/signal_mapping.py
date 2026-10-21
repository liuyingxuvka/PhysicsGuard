"""Stable native signal-mapping ledger authority."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_non_empty


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SignalMappingStatus = Literal["pass", "review_required", "blocked"]


def _sha256(value: str, field_name: str) -> str:
    normalized = ensure_non_empty(value, field_name).lower()
    if not SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized


class SignalMappingEntrySpec(BaseModel):
    """One exact source-to-PhysicsGuard mapping row."""

    model_config = ConfigDict(extra="forbid")

    mapping_id: str
    physics_variable: str
    block_id: str | None = None
    external_signal: str
    expected_unit: str
    observed_unit: str
    conversion_factor: float | None = None
    conversion_note: str | None = None
    mapping_confidence: float | str | None = None
    mapping_status: str
    mapped_at: str | None = None
    source_revision: str
    temporal_boundary: str
    issue_codes: list[str] = Field(default_factory=list)

    @field_validator(
        "mapping_id",
        "physics_variable",
        "block_id",
        "external_signal",
        "expected_unit",
        "observed_unit",
        "conversion_note",
        "mapping_status",
        "mapped_at",
        "source_revision",
        "temporal_boundary",
    )
    @classmethod
    def _text_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else ensure_non_empty(value, info.field_name)

    @field_validator("issue_codes")
    @classmethod
    def _issues_valid(cls, values: list[str]) -> list[str]:
        normalized = [ensure_non_empty(value, "issue_code") for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("issue_codes must be unique")
        return normalized


class SignalMappingLedgerSpec(BaseModel):
    """First-class signal-mapping authority with one stable primary identity."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["physicsguard_signal_mapping_ledger"]
    ledger_version: Literal["1.0"] = "1.0"
    ledger_id: str
    target_system_id: str
    subject_revision: str
    source_artifact_sha256: str
    entries: list[SignalMappingEntrySpec]
    status: SignalMappingStatus
    safe_mapping_claim: str

    @model_validator(mode="before")
    @classmethod
    def _ignore_retired_fingerprint(cls, data: Any) -> Any:
        # Ledgers written before 0.15.16 carry a self-hash of the ledger; it is ignored.
        if isinstance(data, dict) and "ledger_fingerprint" in data:
            data = {key: value for key, value in data.items() if key != "ledger_fingerprint"}
        return data

    @field_validator("ledger_id", "target_system_id", "subject_revision", "safe_mapping_claim")
    @classmethod
    def _identity_valid(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("source_artifact_sha256")
    @classmethod
    def _source_digest_valid(cls, value: str, info) -> str:
        return _sha256(value, info.field_name)

    @model_validator(mode="after")
    def _entries_consistent(self) -> "SignalMappingLedgerSpec":
        if not self.entries:
            raise ValueError("signal mapping ledger requires at least one entry")
        mapping_ids = [entry.mapping_id for entry in self.entries]
        if len(mapping_ids) != len(set(mapping_ids)):
            raise ValueError("signal mapping ids must be unique")
        has_issues = any(entry.issue_codes for entry in self.entries)
        if self.status == "pass" and has_issues:
            raise ValueError("passing signal mapping ledgers cannot contain issue codes")
        if self.status != "pass" and not has_issues:
            raise ValueError("non-passing signal mapping ledgers require at least one issue code")
        return self


__all__ = [
    "SignalMappingEntrySpec",
    "SignalMappingLedgerSpec",
    "SignalMappingStatus",
]
