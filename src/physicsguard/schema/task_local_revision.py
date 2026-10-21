"""Strict current task-local hypothesis and candidate-revision contracts.

The module intentionally has no compatibility reader for the retired optional
task-local shape.  A non-trivial plan is executable evidence only when its
purpose, independently owned coverage universe, predecessor, and native depth
receipt are explicit and current.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator



SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

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
NativeGapFamily = Literal[
    "execution_depth",
    "mapping",
    "residual",
    "uncertainty",
    "diagnosability",
    "predictive_rollout",
]
ResolutionClass = Literal[
    "model_edit",
    "evidence_acquisition",
    "external_input_required",
    "scope_excluded",
]
TerminalReason = Literal[
    "continue_iteration",
    "model_closed_for_task",
    "model_miss",
    "external_input_required",
    "scope_excluded",
    "progress_stalled",
    "iteration_limit",
]

NATIVE_GAP_FAMILIES: frozenset[str] = frozenset(
    {
        "execution_depth",
        "mapping",
        "residual",
        "uncertainty",
        "diagnosability",
        "predictive_rollout",
    }
)


def _non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    return normalized


def _sha256(value: str, field_name: str) -> str:
    normalized = value.strip().lower()
    if not SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must contain exactly 64 lowercase hexadecimal characters")
    return normalized


def _canonical_fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fingerprint_native_depth_receipt(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("receipt_fingerprint", None)
    return _canonical_fingerprint(payload)


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
    sha256: str

    @field_validator("model_id", "model_version", "path")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _non_empty(value, info.field_name)

    @field_validator("sha256")
    @classmethod
    def _hash_valid(cls, value: str) -> str:
        return _sha256(value, "sha256")


class CoverageUniverseSpec(BaseModel):
    """Independently owned finite task-coverage authority."""

    model_config = ConfigDict(extra="forbid")

    coverage_universe_id: str
    coverage_universe_fingerprint: str
    owner_id: str
    discovery_evidence_id: str
    member_ids: list[str]

    @field_validator(
        "coverage_universe_id", "owner_id", "discovery_evidence_id"
    )
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _non_empty(value, info.field_name)

    @field_validator("coverage_universe_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "coverage_universe_fingerprint")

    @field_validator("member_ids")
    @classmethod
    def _members_valid(cls, values: list[str]) -> list[str]:
        return _unique_text(values, "coverage member id", non_empty=True)


class TaskBlueprintBindingSpec(BaseModel):
    """Exact current blueprint review consumed by one task-local iteration."""

    model_config = ConfigDict(extra="forbid")

    blueprint_id: str
    target_system_id: str
    subject_revision: str
    blueprint_fingerprint: str
    blueprint_review_fingerprint: str
    scope: Literal["whole", "affected"]
    affected_slice_fingerprint: str | None
    affected_element_ids: list[str]
    deepest_licensed_layer: BlueprintLayerName | None
    first_gap_id: str | None
    review_status: Literal["pass", "incomplete", "stale", "blocked"]

    @field_validator("blueprint_id", "target_system_id", "subject_revision", "first_gap_id")
    @classmethod
    def _identity_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _non_empty(value, info.field_name)

    @field_validator(
        "blueprint_fingerprint",
        "blueprint_review_fingerprint",
        "affected_slice_fingerprint",
    )
    @classmethod
    def _fingerprint_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _sha256(value, info.field_name)

    @field_validator("affected_element_ids")
    @classmethod
    def _affected_ids_valid(cls, values: list[str]) -> list[str]:
        return _unique_text(values, "affected_element_id")

    @model_validator(mode="after")
    def _scope_and_gap_current(self) -> "TaskBlueprintBindingSpec":
        if self.scope == "affected":
            if self.affected_slice_fingerprint is None or not self.affected_element_ids:
                raise ValueError("affected blueprint binding requires slice fingerprint and element ids")
        elif self.affected_slice_fingerprint is not None or self.affected_element_ids:
            raise ValueError("whole blueprint binding cannot carry an affected slice")
        if self.review_status == "pass" and self.first_gap_id is not None:
            raise ValueError("passing blueprint binding cannot carry first_gap_id")
        if self.review_status != "pass" and self.first_gap_id is None:
            raise ValueError("non-passing blueprint binding requires first_gap_id")
        return self


class NativeDepthGapSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gap_id: str
    family: NativeGapFamily
    resolution_class: ResolutionClass
    next_action: str
    external_input_id: str | None = None

    @field_validator("gap_id", "next_action")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _non_empty(value, info.field_name)

    @field_validator("external_input_id")
    @classmethod
    def _external_text_valid(cls, value: str | None) -> str | None:
        return None if value is None else _non_empty(value, "external_input_id")

    @model_validator(mode="after")
    def _resolution_valid(self) -> "NativeDepthGapSpec":
        if self.resolution_class == "external_input_required":
            if self.external_input_id is None:
                raise ValueError("external-input gaps require external_input_id")
        elif self.external_input_id is not None:
            raise ValueError("external_input_id is valid only for external-input gaps")
        return self


class NativeDepthReceiptSpec(BaseModel):
    """Target-owned six-family depth result consumed without reinterpretation."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["physicsguard_task_native_depth_receipt"]
    receipt_version: Literal["1.0"] = "1.0"
    producer_id: Literal["physicsguard.native-task-depth"]
    status: Literal["pass", "blocked"]
    task_id: str
    plan_id: str
    iteration: int = Field(ge=0)
    model_sha256: str
    coverage_universe_fingerprint: str
    blueprint: TaskBlueprintBindingSpec
    source_receipt_ids: dict[NativeGapFamily, str]
    source_receipt_fingerprints: dict[NativeGapFamily, str]
    gaps: list[NativeDepthGapSpec]
    receipt_fingerprint: str

    @field_validator("task_id", "plan_id")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _non_empty(value, info.field_name)

    @field_validator(
        "model_sha256", "coverage_universe_fingerprint", "receipt_fingerprint"
    )
    @classmethod
    def _hash_valid(cls, value: str, info) -> str:
        return _sha256(value, info.field_name)

    @field_validator("source_receipt_ids")
    @classmethod
    def _source_ids_valid(
        cls, values: dict[NativeGapFamily, str]
    ) -> dict[NativeGapFamily, str]:
        if set(values) != NATIVE_GAP_FAMILIES:
            raise ValueError("source_receipt_ids must exactly cover all six native gap families")
        return {key: _non_empty(value, f"source_receipt_ids.{key}") for key, value in values.items()}

    @field_validator("source_receipt_fingerprints")
    @classmethod
    def _source_fingerprints_valid(
        cls, values: dict[NativeGapFamily, str]
    ) -> dict[NativeGapFamily, str]:
        if set(values) != NATIVE_GAP_FAMILIES:
            raise ValueError(
                "source_receipt_fingerprints must exactly cover all six native gap families"
            )
        return {key: _sha256(value, f"source_receipt_fingerprints.{key}") for key, value in values.items()}

    @model_validator(mode="after")
    def _receipt_valid(self) -> "NativeDepthReceiptSpec":
        gap_ids = [gap.gap_id for gap in self.gaps]
        if len(gap_ids) != len(set(gap_ids)):
            raise ValueError("native gap ids must be unique")
        if self.status == "pass" and self.gaps:
            raise ValueError("passing native depth receipts cannot contain open gaps")
        if self.status == "blocked" and not self.gaps:
            raise ValueError("blocked native depth receipts require at least one open gap")
        expected = fingerprint_native_depth_receipt(self.model_dump(mode="json"))
        if self.receipt_fingerprint != expected:
            raise ValueError("native depth receipt fingerprint is stale or invalid")
        return self


class PredecessorIterationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    plan_id: str
    iteration: int = Field(ge=0)
    terminal_reason: TerminalReason
    receipt_fingerprint: str
    model_sha256: str
    blueprint_fingerprint: str
    open_gap_ids: list[str]

    @field_validator("task_id", "plan_id")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _non_empty(value, info.field_name)

    @field_validator("receipt_fingerprint", "model_sha256", "blueprint_fingerprint")
    @classmethod
    def _hash_valid(cls, value: str, info) -> str:
        return _sha256(value, info.field_name)

    @field_validator("open_gap_ids")
    @classmethod
    def _gaps_valid(cls, values: list[str]) -> list[str]:
        return _unique_text(values, "predecessor open gap id")


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
        kinds = {item.kind for item in self.expectations}
        if kinds != {"signal", "residual", "timing"}:
            raise ValueError("each hypothesis requires signal, residual, and timing expectations")
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
    coverage: CoverageUniverseSpec
    blueprint: TaskBlueprintBindingSpec
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
    predecessor: PredecessorIterationSpec | None
    native_depth_receipt: NativeDepthReceiptSpec

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
        receipt = self.native_depth_receipt
        if receipt.task_id != self.task_id or receipt.plan_id != self.plan_id:
            raise ValueError("native depth receipt task/plan identity mismatch")
        if receipt.iteration != self.iteration:
            raise ValueError("native depth receipt iteration mismatch")
        if receipt.model_sha256 != self.model.sha256:
            raise ValueError("native depth receipt is not bound to the plan model")
        if receipt.coverage_universe_fingerprint != self.coverage.coverage_universe_fingerprint:
            raise ValueError("native depth receipt coverage universe mismatch")
        if receipt.blueprint != self.blueprint:
            raise ValueError("native depth receipt blueprint identity or depth mismatch")
        if self.iteration == 0:
            if self.predecessor is not None:
                raise ValueError("initial plan must declare predecessor as null")
        else:
            if self.predecessor is None:
                raise ValueError("later plan iterations require an exact predecessor receipt")
            if self.predecessor.task_id != self.task_id:
                raise ValueError("predecessor task identity mismatch")
            if self.predecessor.iteration != self.iteration - 1:
                raise ValueError("predecessor iteration must be exactly one less than the plan")
            if self.predecessor.blueprint_fingerprint != self.blueprint.blueprint_fingerprint:
                raise ValueError("predecessor blueprint fingerprint is stale or foreign")
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
    evidence_fingerprint: str
    producer_id: str
    source_ref: str
    independence_group: str
    evidence_kind: ModelMissEvidenceKind

    @field_validator("evidence_id", "producer_id", "source_ref", "independence_group")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return _non_empty(value, info.field_name)

    @field_validator("evidence_fingerprint")
    @classmethod
    def _fingerprint_valid(cls, value: str) -> str:
        return _sha256(value, "evidence_fingerprint")


class DiagnosticObservationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str
    task_id: str
    plan_id: str
    frozen_plan_fingerprint: str
    blueprint_fingerprint: str
    affected_slice_fingerprint: str | None
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

    @field_validator("frozen_plan_fingerprint", "blueprint_fingerprint", "affected_slice_fingerprint")
    @classmethod
    def _plan_fingerprint_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else _sha256(value, info.field_name)

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
    "CoverageUniverseSpec",
    "DiagnosticHypothesisSpec",
    "DiagnosticObservationSpec",
    "EvidenceIdentitySpec",
    "HypothesisExpectationSpec",
    "HypothesisPlanSpec",
    "ModelMissEvidenceKind",
    "NATIVE_GAP_FAMILIES",
    "NativeDepthGapSpec",
    "NativeDepthReceiptSpec",
    "ObservationCandidateSpec",
    "ObservationSelectionWeightsSpec",
    "ObservedSignalSpec",
    "PredecessorIterationSpec",
    "ResolutionClass",
    "TaskModelIdentitySpec",
    "TaskBlueprintBindingSpec",
    "TerminalReason",
    "fingerprint_native_depth_receipt",
]
