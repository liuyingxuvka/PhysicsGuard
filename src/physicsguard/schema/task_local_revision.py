"""Task-local competing-hypothesis plan and observation contracts."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ExpectationKind = Literal["signal", "residual", "timing"]
ExpectationOperator = Literal[
    "between",
    "positive",
    "negative",
    "increase",
    "decrease",
    "stable",
    "before",
    "after",
    "simultaneous",
]
ModelMissEvidenceKind = Literal[
    "runtime",
    "test",
    "replay",
    "manual",
    "production",
    "experiment",
    "dataset",
    "observation",
]


def _non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    return normalized


def _unique_text(values: list[str], field_name: str, *, non_empty: bool = False) -> list[str]:
    normalized = [_non_empty(value, field_name) for value in values]
    if non_empty and not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must be unique")
    return normalized


class TaskModelIdentitySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str
    model_version: str
    path: str

    @field_validator("model_id", "model_version", "path")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _non_empty(value, info.field_name)


class HypothesisExpectationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectation_id: str
    kind: ExpectationKind
    target_id: str
    operator: ExpectationOperator
    lower: float | None = None
    upper: float | None = None
    compare_target_id: str | None = None
    tolerance: float = 0.0
    weakening_condition: str

    @field_validator("expectation_id", "target_id", "weakening_condition")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _non_empty(value, info.field_name)

    @field_validator("compare_target_id")
    @classmethod
    def _optional_text_valid(cls, value: str | None) -> str | None:
        return None if value is None else _non_empty(value, "compare_target_id")

    @model_validator(mode="after")
    def _operator_shape_valid(self) -> "HypothesisExpectationSpec":
        if not math.isfinite(self.tolerance) or self.tolerance < 0:
            raise ValueError("tolerance must be finite and non-negative")
        if self.operator == "between":
            if self.kind == "timing" or self.lower is None or self.upper is None:
                raise ValueError("between requires numeric lower and upper bounds")
            if not math.isfinite(self.lower) or not math.isfinite(self.upper) or self.lower > self.upper:
                raise ValueError("between bounds must be finite and ordered")
        elif self.lower is not None or self.upper is not None:
            raise ValueError("lower and upper are only valid for the between operator")
        if self.kind == "timing":
            if self.operator not in {"before", "after", "simultaneous"}:
                raise ValueError("timing expectations require before, after, or simultaneous")
            if self.compare_target_id is None:
                raise ValueError("timing expectations require compare_target_id")
        elif self.compare_target_id is not None:
            raise ValueError("compare_target_id is only valid for timing expectations")
        if self.operator in {"increase", "decrease", "stable"} and self.kind != "signal":
            raise ValueError("trend operators are only valid for signal expectations")
        if self.operator in {"positive", "negative"} and self.kind == "timing":
            raise ValueError("sign operators are not valid for timing expectations")
        return self


class DiagnosticHypothesisSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str
    explanation: str
    expectations: list[HypothesisExpectationSpec]

    @field_validator("hypothesis_id", "explanation")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _coverage_valid(self) -> "DiagnosticHypothesisSpec":
        ids = [item.expectation_id for item in self.expectations]
        if len(ids) != len(set(ids)):
            raise ValueError("expectation ids must be unique within one hypothesis")
        if not self.expectations:
            raise ValueError("each hypothesis requires at least one expectation")
        return self


class ObservationCandidateSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    target_id: str
    residual_relevance: float = Field(ge=0.0, le=1.0)
    predicted_outcomes: dict[str, str]

    @field_validator("candidate_id", "target_id")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _non_empty(value, info.field_name)

    @field_validator("predicted_outcomes")
    @classmethod
    def _outcomes_valid(cls, values: dict[str, str]) -> dict[str, str]:
        if not values:
            raise ValueError("predicted_outcomes must be non-empty")
        return {
            _non_empty(key, "predicted_outcome hypothesis id"): _non_empty(
                value, "predicted outcome"
            )
            for key, value in values.items()
        }


class ObservationSelectionWeightsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    residual_relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    hypothesis_discrimination: float = Field(default=0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _sum_valid(self) -> "ObservationSelectionWeightsSpec":
        if not math.isclose(
            self.residual_relevance + self.hypothesis_discrimination,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("observation selection weights must sum to one")
        return self


class HypothesisPlanSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str
    task_id: str
    purpose: str
    non_trivial: bool
    model: TaskModelIdentitySpec
    assumptions: list[str]
    unknowns: list[str]
    prediction_sequence: int = Field(ge=0)
    hypotheses: list[DiagnosticHypothesisSpec]
    observation_candidates: list[ObservationCandidateSpec]
    selection_weights: ObservationSelectionWeightsSpec = Field(
        default_factory=ObservationSelectionWeightsSpec
    )
    iteration: int = Field(ge=0)
    max_iterations: int = Field(ge=1)

    @field_validator("plan_id", "task_id", "purpose")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _non_empty(value, info.field_name)

    @field_validator("assumptions", "unknowns")
    @classmethod
    def _declared_lists_valid(cls, values: list[str], info) -> list[str]:
        return _unique_text(values, info.field_name)

    @model_validator(mode="after")
    def _plan_valid(self) -> "HypothesisPlanSpec":
        hypothesis_ids = [item.hypothesis_id for item in self.hypotheses]
        if len(hypothesis_ids) != len(set(hypothesis_ids)):
            raise ValueError("hypothesis ids must be unique")
        minimum = 2 if self.non_trivial else 1
        if len(self.hypotheses) < minimum:
            raise ValueError(
                f"{'non-trivial' if self.non_trivial else 'trivial'} plans require at least {minimum} hypothesis"
            )
        candidate_ids = [item.candidate_id for item in self.observation_candidates]
        if not candidate_ids or len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("observation candidates must be non-empty and uniquely identified")
        expected = set(hypothesis_ids)
        for candidate in self.observation_candidates:
            if set(candidate.predicted_outcomes) != expected:
                raise ValueError(
                    "every observation candidate must declare one outcome for every hypothesis"
                )
        return self


class ObservedSignalSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float | None = None
    trend: Literal["increase", "decrease", "stable"] | None = None

    @model_validator(mode="after")
    def _measurement_present(self) -> "ObservedSignalSpec":
        if self.value is None and self.trend is None:
            raise ValueError("observed signal requires a value or trend")
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("observed signal value must be finite")
        return self


class EvidenceIdentitySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    producer_id: str
    source_ref: str
    independence_group: str
    evidence_kind: ModelMissEvidenceKind

    @field_validator("evidence_id", "producer_id", "source_ref", "independence_group")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _non_empty(value, info.field_name)


class DiagnosticObservationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str
    task_id: str
    plan_id: str
    selected_candidate_id: str
    observation_sequence: int = Field(ge=0)
    evidence: EvidenceIdentitySpec
    signals: dict[str, ObservedSignalSpec]
    residuals: dict[str, float]
    timings: dict[str, float]
    external_input_ids: list[str]

    @field_validator("observation_id", "task_id", "plan_id", "selected_candidate_id")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _non_empty(value, info.field_name)


    @field_validator("residuals", "timings")
    @classmethod
    def _finite_values(cls, values: dict[str, float], info) -> dict[str, float]:
        normalized: dict[str, float] = {}
        for key, value in values.items():
            key = _non_empty(key, f"{info.field_name} key")
            if not math.isfinite(value):
                raise ValueError(f"{info.field_name} values must be finite")
            normalized[key] = float(value)
        return normalized

    @field_validator("external_input_ids")
    @classmethod
    def _external_ids_valid(cls, values: list[str]) -> list[str]:
        return _unique_text(values, "external_input_id")


__all__ = [
    "DiagnosticHypothesisSpec",
    "DiagnosticObservationSpec",
    "EvidenceIdentitySpec",
    "HypothesisExpectationSpec",
    "HypothesisPlanSpec",
    "ModelMissEvidenceKind",
    "ObservationCandidateSpec",
    "ObservationSelectionWeightsSpec",
    "ObservedSignalSpec",
    "TaskModelIdentitySpec",
]
