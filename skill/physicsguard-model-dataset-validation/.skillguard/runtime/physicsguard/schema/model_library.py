"""Schemas for reusable PhysicsGuard model library indexes."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_non_empty


ReuseStatus = Literal["draft", "validated", "partial", "failed", "stale", "review_required"]


class ModelLibraryEntrySpec(BaseModel):
    """Reusable model asset with validation evidence references."""

    model_config = ConfigDict(extra="forbid")

    model_id: str
    model_file: str
    model_hash: Optional[str] = None
    evidence_registry: Optional[str] = None
    model_context: Optional[str] = None
    evidence_bundle_id: Optional[str] = None
    compatible_testbench_profiles: list[str] = Field(default_factory=list)
    validation_reports: list[str] = Field(default_factory=list)
    reuse_status: ReuseStatus = "draft"
    known_limits: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("model_id", "model_file")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("evidence_registry", "model_context", "evidence_bundle_id")
    @classmethod
    def _optional_strings_not_empty(cls, value: Optional[str], info) -> Optional[str]:
        if value is not None:
            return ensure_non_empty(value, info.field_name)
        return value

    @field_validator("compatible_testbench_profiles", "validation_reports", "known_limits")
    @classmethod
    def _list_values_not_empty(cls, values: list[str], info) -> list[str]:
        for value in values:
            ensure_non_empty(value, info.field_name)
        return values

    @model_validator(mode="after")
    def _entry_valid(self) -> "ModelLibraryEntrySpec":
        if self.reuse_status in {"validated", "partial"} and not self.validation_reports:
            raise ValueError("validated or partial model library entries require validation reports")
        _ensure_json_serializable(self.metadata, "model library entry metadata")
        return self


class ModelLibraryIndexSpec(BaseModel):
    """Project-level reusable model library index."""

    model_config = ConfigDict(extra="forbid")

    library_id: str
    entries: list[ModelLibraryEntrySpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("library_id")
    @classmethod
    def _library_id_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "library_id")

    @model_validator(mode="after")
    def _index_valid(self) -> "ModelLibraryIndexSpec":
        ids = [entry.model_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("model library entry ids must be unique")
        _ensure_json_serializable(self.metadata, "model library metadata")
        return self


def _ensure_json_serializable(value: Any, field_name: str) -> None:
    try:
        json.dumps(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be JSON-serializable") from exc


__all__ = ["ModelLibraryEntrySpec", "ModelLibraryIndexSpec", "ReuseStatus"]
