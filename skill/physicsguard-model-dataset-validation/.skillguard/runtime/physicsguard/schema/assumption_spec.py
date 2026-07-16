"""Explicit assumption card schemas for PhysicsGuard audits."""

from __future__ import annotations

import json
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_non_empty, is_qualified_variable_name


AssumptionTargetType = Literal["variable", "parameter", "context"]
AssumptionImpact = Literal["low", "medium", "high"]
AssumptionStatus = Literal["active", "rejected", "proposed"]
AssumptionValue = float | int | str | bool


DEFAULT_CONFIDENCE_PENALTIES = {
    "low": 0.02,
    "medium": 0.10,
    "high": 0.25,
}


class AssumptionSpec(BaseModel):
    """Explicit assumption card.

    Assumptions are not solver variables. They can fill parameters or create
    visible fixed-value residuals only when explicitly active.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    target_type: AssumptionTargetType
    target: str
    value: AssumptionValue
    unit: str | None = None
    reason: str
    source: str = "unspecified"
    impact: AssumptionImpact = "medium"
    confidence_penalty: float | None = None
    review_required: bool = True
    status: AssumptionStatus = "active"
    allow_override: bool = False
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _id_valid(cls, value: str) -> str:
        ensure_non_empty(value, "assumption id")
        if any(character.isspace() for character in value):
            raise ValueError("assumption id cannot contain whitespace")
        return value

    @field_validator("target")
    @classmethod
    def _target_nonempty(cls, value: str) -> str:
        return ensure_non_empty(value, "assumption target")

    @field_validator("reason")
    @classmethod
    def _reason_nonempty(cls, value: str) -> str:
        return ensure_non_empty(value, "assumption reason")

    @field_validator("tags")
    @classmethod
    def _tags_valid(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in values:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("assumption tags must be non-empty strings")
            normalized.append(item.strip().lower())
        return normalized

    @model_validator(mode="after")
    def _validate_card(self) -> "AssumptionSpec":
        if self.target_type in {"variable", "parameter"} and not is_qualified_variable_name(self.target):
            raise ValueError("variable and parameter assumption targets must use component.name format")
        if self.confidence_penalty is not None:
            if not math.isfinite(self.confidence_penalty) or self.confidence_penalty < 0:
                raise ValueError("confidence_penalty must be finite and nonnegative")
        _ensure_json_serializable(self.value, "assumption value")
        _ensure_json_serializable(self.metadata, "assumption metadata")
        return self

    @property
    def effective_confidence_penalty(self) -> float:
        if self.confidence_penalty is not None:
            return float(self.confidence_penalty)
        return DEFAULT_CONFIDENCE_PENALTIES[self.impact]


class AssumptionDeckSpec(BaseModel):
    """Collection of explicit assumption cards."""

    model_config = ConfigDict(extra="forbid")

    assumptions: list[AssumptionSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_deck(self) -> "AssumptionDeckSpec":
        ids = [assumption.id for assumption in self.assumptions]
        if len(ids) != len(set(ids)):
            raise ValueError("assumption ids must be unique")
        _ensure_json_serializable(self.metadata, "assumption deck metadata")
        return self


def _ensure_json_serializable(value: Any, label: str) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be JSON-serializable") from exc


__all__ = [
    "AssumptionDeckSpec",
    "AssumptionImpact",
    "AssumptionSpec",
    "AssumptionStatus",
    "AssumptionTargetType",
    "AssumptionValue",
    "DEFAULT_CONFIDENCE_PENALTIES",
]
