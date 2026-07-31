"""Strict interval and fault-signature contracts for task-local diagnosis."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class IntervalValueSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lower: float
    upper: float

    @model_validator(mode="after")
    def _ordered_finite(self) -> "IntervalValueSpec":
        if (
            not math.isfinite(self.lower)
            or not math.isfinite(self.upper)
            or self.lower > self.upper
        ):
            raise ValueError("interval bounds must be finite and ordered")
        return self


class IntervalResidualSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    residual_id: str
    observed: IntervalValueSpec | None = None
    acceptable: IntervalValueSpec
    source_ref: str

    @field_validator("residual_id", "source_ref")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("identifier and source_ref must be non-empty")
        return value


class FaultSignatureSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str
    predicted_intervals: dict[str, IntervalValueSpec]

    @field_validator("hypothesis_id")
    @classmethod
    def _hypothesis_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("hypothesis_id must be non-empty")
        return value

    @field_validator("predicted_intervals")
    @classmethod
    def _predictions(cls, value: dict[str, IntervalValueSpec]):
        if not value or any(not key.strip() for key in value):
            raise ValueError("predicted_intervals require non-empty signal ids")
        return value


class DiagnosabilityRequestSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnosis_id: str
    fault_signatures: list[FaultSignatureSpec]
    available_signal_ids: list[str]
    observed_signals: dict[str, IntervalValueSpec] = Field(default_factory=dict)

    @field_validator("diagnosis_id")
    @classmethod
    def _diagnosis_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("diagnosis_id must be non-empty")
        return value

    @model_validator(mode="after")
    def _inventory(self) -> "DiagnosabilityRequestSpec":
        hypotheses = [item.hypothesis_id for item in self.fault_signatures]
        if len(hypotheses) < 2 or len(hypotheses) != len(set(hypotheses)):
            raise ValueError(
                "diagnosability requires at least two unique hypotheses"
            )
        if (
            not self.available_signal_ids
            or len(self.available_signal_ids)
            != len(set(self.available_signal_ids))
            or any(not item.strip() for item in self.available_signal_ids)
        ):
            raise ValueError(
                "available_signal_ids must be non-empty and unique"
            )
        return self


__all__ = [
    "DiagnosabilityRequestSpec",
    "FaultSignatureSpec",
    "IntervalResidualSpec",
    "IntervalValueSpec",
]
