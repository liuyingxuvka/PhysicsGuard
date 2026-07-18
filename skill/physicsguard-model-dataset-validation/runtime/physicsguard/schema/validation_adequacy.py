"""Typed contracts for target-owned validation sampling adequacy."""

from __future__ import annotations

import math
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_non_empty


SamplingMode = Literal["full", "stratified", "event_aware", "adaptive", "project_declared"]
AdequacyStatus = Literal["pass", "partial", "blocked", "not_applicable"]
FamilyMemberKind = Literal["signal", "parameter", "mixed"]
ParameterTemporalBehavior = Literal["static", "time_varying"]
ParameterContributionExpectation = Literal["sensitive", "verified_non_sensitive"]
ANTI_DEGENERACY_FLOOR_ALGORITHM = "sqrt_n_stage_v1"


class ParameterTimeStratumSpec(BaseModel):
    """One project-declared row-position stratum for a time-varying parameter."""

    model_config = ConfigDict(extra="forbid")

    stratum_id: str
    start_fraction: float
    end_fraction: float
    minimum_valid_points: int = 1

    @field_validator("stratum_id")
    @classmethod
    def _stratum_id_valid(cls, value: str) -> str:
        return ensure_non_empty(value, "stratum_id")

    @field_validator("start_fraction", "end_fraction")
    @classmethod
    def _fraction_valid(cls, value: float, info) -> float:
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{info.field_name} must be between 0 and 1")
        return value

    @field_validator("minimum_valid_points")
    @classmethod
    def _minimum_valid_points_valid(cls, value: int) -> int:
        if value < 1:
            raise ValueError("minimum_valid_points must be positive")
        return value

    @model_validator(mode="after")
    def _bounds_valid(self) -> "ParameterTimeStratumSpec":
        if self.start_fraction >= self.end_fraction:
            raise ValueError("parameter stratum start_fraction must be less than end_fraction")
        return self


class ParameterTemporalPolicySpec(BaseModel):
    """Project-owned classification that prevents one-point time-varying parameters."""

    model_config = ConfigDict(extra="forbid")

    parameter_id: str
    temporal_behavior: ParameterTemporalBehavior
    classification_source: str
    availability_source_id: Optional[str] = None
    minimum_valid_points: Optional[int] = None
    minimum_valid_ratio: Optional[float] = None
    minimum_distinct_timestamps: Optional[int] = None
    minimum_time_span: Optional[float] = None
    maximum_time_gap: Optional[float] = None
    required_strata: list[ParameterTimeStratumSpec] = Field(default_factory=list)
    convergence_evidence_id: Optional[str] = None
    convergence_minimum_valid_points: Optional[int] = None
    convergence_minimum_valid_ratio: Optional[float] = None
    contribution_expectation: Optional[ParameterContributionExpectation] = None
    minimum_normalized_contribution_effect: Optional[float] = None
    maximum_non_sensitive_contribution_effect: Optional[float] = None
    non_sensitive_reason: Optional[str] = None
    non_sensitive_claim_boundary: Optional[str] = None

    @field_validator("parameter_id", "classification_source")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator(
        "availability_source_id",
        "convergence_evidence_id",
        "non_sensitive_reason",
        "non_sensitive_claim_boundary",
    )
    @classmethod
    def _availability_source_valid(cls, value: Optional[str], info) -> Optional[str]:
        if value is None:
            return None
        return ensure_non_empty(value, info.field_name)

    @field_validator(
        "minimum_valid_points",
        "minimum_distinct_timestamps",
        "convergence_minimum_valid_points",
    )
    @classmethod
    def _temporal_count_valid(cls, value: Optional[int], info) -> Optional[int]:
        if value is not None and value < 1:
            raise ValueError(f"{info.field_name} must be positive")
        return value

    @field_validator("minimum_valid_ratio", "convergence_minimum_valid_ratio")
    @classmethod
    def _temporal_ratio_valid(cls, value: Optional[float], info) -> Optional[float]:
        if value is not None and (not math.isfinite(value) or not 0 < value <= 1):
            raise ValueError(f"{info.field_name} must be in (0, 1]")
        return value

    @field_validator(
        "minimum_normalized_contribution_effect",
        "maximum_non_sensitive_contribution_effect",
    )
    @classmethod
    def _contribution_effect_valid(cls, value: Optional[float], info) -> Optional[float]:
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError(f"{info.field_name} must be finite and nonnegative")
        return value

    @field_validator("minimum_time_span", "maximum_time_gap")
    @classmethod
    def _temporal_duration_valid(cls, value: Optional[float], info) -> Optional[float]:
        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ValueError(f"{info.field_name} must be positive and finite")
        return value

    @model_validator(mode="after")
    def _behavior_contract_valid(self) -> "ParameterTemporalPolicySpec":
        temporal_fields = {
            "availability_source_id": self.availability_source_id,
            "minimum_valid_points": self.minimum_valid_points,
            "minimum_valid_ratio": self.minimum_valid_ratio,
            "minimum_distinct_timestamps": self.minimum_distinct_timestamps,
            "minimum_time_span": self.minimum_time_span,
            "maximum_time_gap": self.maximum_time_gap,
        }
        if self.temporal_behavior == "static":
            additional_fields = {
                "convergence_evidence_id": self.convergence_evidence_id,
                "convergence_minimum_valid_points": self.convergence_minimum_valid_points,
                "convergence_minimum_valid_ratio": self.convergence_minimum_valid_ratio,
                "contribution_expectation": self.contribution_expectation,
                "minimum_normalized_contribution_effect": self.minimum_normalized_contribution_effect,
                "maximum_non_sensitive_contribution_effect": self.maximum_non_sensitive_contribution_effect,
                "non_sensitive_reason": self.non_sensitive_reason,
                "non_sensitive_claim_boundary": self.non_sensitive_claim_boundary,
            }
            if (
                any(value is not None for value in temporal_fields.values())
                or any(value is not None for value in additional_fields.values())
                or self.required_strata
            ):
                raise ValueError("static parameters must not declare time-series coverage requirements")
            return self
        missing = [name for name, value in temporal_fields.items() if value is None]
        if missing:
            raise ValueError(
                "time-varying parameters require explicit target-owned coverage fields: "
                + ", ".join(missing)
            )
        if self.minimum_valid_points is not None and self.minimum_valid_points < 3:
            raise ValueError("time-varying parameter minimum_valid_points cannot be lower than three")
        if self.minimum_distinct_timestamps is not None and self.minimum_distinct_timestamps < 3:
            raise ValueError(
                "time-varying parameter minimum_distinct_timestamps cannot be lower than three"
            )
        if len(self.required_strata) < 3:
            raise ValueError("time-varying parameters require at least three target-declared strata")
        stratum_ids = [item.stratum_id for item in self.required_strata]
        if len(stratum_ids) != len(set(stratum_ids)):
            raise ValueError("parameter required_strata ids must be unique")
        convergence_fields = (
            self.convergence_evidence_id,
            self.convergence_minimum_valid_points,
            self.convergence_minimum_valid_ratio,
        )
        if any(value is not None for value in convergence_fields) and not all(
            value is not None for value in convergence_fields
        ):
            raise ValueError(
                "parameter convergence evidence id, minimum points, and minimum ratio must be declared together"
            )
        if self.contribution_expectation is None:
            raise ValueError(
                "time-varying parameters require an explicit model contribution expectation"
            )
        if self.contribution_expectation == "sensitive":
            if (
                self.minimum_normalized_contribution_effect is None
                or self.minimum_normalized_contribution_effect <= 0
            ):
                raise ValueError(
                    "sensitive parameters require a positive minimum_normalized_contribution_effect"
                )
            if any(
                value is not None
                for value in (
                    self.maximum_non_sensitive_contribution_effect,
                    self.non_sensitive_reason,
                    self.non_sensitive_claim_boundary,
                )
            ):
                raise ValueError(
                    "sensitive parameters must not declare a non-sensitive disposition"
                )
        else:
            if self.maximum_non_sensitive_contribution_effect is None:
                raise ValueError(
                    "verified non-sensitive parameters require maximum_non_sensitive_contribution_effect"
                )
            if not self.non_sensitive_reason or not self.non_sensitive_claim_boundary:
                raise ValueError(
                    "verified non-sensitive parameters require a reason and bounded claim disposition"
                )
            if self.minimum_normalized_contribution_effect is not None:
                raise ValueError(
                    "verified non-sensitive parameters must not declare a minimum sensitive effect"
                )
        return self


class FamilyQuotaPlanSpec(BaseModel):
    """Minimum target coverage for one declared signal/parameter family."""

    model_config = ConfigDict(extra="forbid")

    family_id: str
    member_kind: FamilyMemberKind = "mixed"
    member_ids: list[str]
    minimum_covered_count: int = 1
    minimum_covered_ratio: float = 1.0

    @field_validator("family_id")
    @classmethod
    def _family_id_valid(cls, value: str) -> str:
        return ensure_non_empty(value, "family_id")

    @field_validator("member_ids")
    @classmethod
    def _members_valid(cls, values: list[str]) -> list[str]:
        normalized = [ensure_non_empty(value, "member_id") for value in values]
        if not normalized:
            raise ValueError("family quota requires at least one member")
        if len(normalized) != len(set(normalized)):
            raise ValueError("family quota member_ids must be unique")
        return normalized

    @field_validator("minimum_covered_count")
    @classmethod
    def _count_valid(cls, value: int) -> int:
        if value < 1:
            raise ValueError("minimum_covered_count must be positive")
        return value

    @field_validator("minimum_covered_ratio")
    @classmethod
    def _ratio_valid(cls, value: float) -> float:
        if not math.isfinite(value) or not 0 < value <= 1:
            raise ValueError("minimum_covered_ratio must be in (0, 1]")
        return value


class ValidationAdequacyPlanSpec(BaseModel):
    """Project-provenanced quantitative floors for a non-snapshot claim."""

    model_config = ConfigDict(extra="forbid")

    sampling_mode: SamplingMode = "full"
    threshold_source: str
    selection_policy_id: str
    selection_rationale: str
    minimum_selected_points: int = 3
    minimum_selected_ratio: float = 0.1
    minimum_distinct_timestamps: int = 3
    minimum_time_span: float = 1.0e-12
    maximum_time_gap: float
    require_start_middle_end: bool = True
    minimum_signal_coverage_ratio: float = 0.8
    minimum_per_signal_valid_points: int = 3
    minimum_per_signal_valid_ratio: float = 1.0
    minimum_per_parameter_valid_points: int = 3
    minimum_per_parameter_valid_ratio: float = 1.0
    minimum_parameter_coverage_ratio: float = 1.0
    maximum_exclusion_ratio: float = 0.2
    critical_signals: list[str] = Field(default_factory=list)
    critical_parameters: list[str] = Field(default_factory=list)
    parameter_temporal_policies: list[ParameterTemporalPolicySpec] = Field(default_factory=list)
    required_event_tags: list[str] = Field(default_factory=list)
    required_peak_tags: list[str] = Field(default_factory=list)
    required_boundary_tags: list[str] = Field(default_factory=list)
    required_mode_ids: list[str] = Field(default_factory=list)
    family_quotas: list[FamilyQuotaPlanSpec] = Field(default_factory=list)
    reject_repeated_exclusion_reasons: bool = True
    maximum_repeated_exclusion_reason_count: int = 1
    adaptive_converged: Optional[bool] = None
    adaptive_evidence_id: Optional[str] = None
    adaptive_minimum_selected_points: Optional[int] = None
    adaptive_minimum_selected_ratio: Optional[float] = None

    @field_validator("threshold_source", "selection_policy_id", "selection_rationale")
    @classmethod
    def _source_valid(cls, value: str) -> str:
        return ensure_non_empty(value, "sampling policy text")

    @field_validator(
        "critical_signals",
        "critical_parameters",
        "required_event_tags",
        "required_peak_tags",
        "required_boundary_tags",
        "required_mode_ids",
    )
    @classmethod
    def _unique_text_lists(cls, values: list[str], info) -> list[str]:
        normalized = [ensure_non_empty(value, info.field_name) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError(f"{info.field_name} must be unique")
        return normalized

    @field_validator(
        "minimum_selected_points",
        "minimum_distinct_timestamps",
        "minimum_per_signal_valid_points",
        "minimum_per_parameter_valid_points",
        "adaptive_minimum_selected_points",
    )
    @classmethod
    def _positive_counts(cls, value: Optional[int], info) -> Optional[int]:
        if value is not None and value < 1:
            raise ValueError(f"{info.field_name} must be positive")
        return value

    @field_validator("maximum_repeated_exclusion_reason_count")
    @classmethod
    def _repeat_count_valid(cls, value: int) -> int:
        if value < 1:
            raise ValueError("maximum_repeated_exclusion_reason_count must be positive")
        return value

    @field_validator(
        "minimum_selected_ratio",
        "minimum_signal_coverage_ratio",
        "minimum_per_signal_valid_ratio",
        "minimum_per_parameter_valid_ratio",
        "minimum_parameter_coverage_ratio",
        "adaptive_minimum_selected_ratio",
    )
    @classmethod
    def _positive_ratios(cls, value: Optional[float], info) -> Optional[float]:
        if value is not None and (not math.isfinite(value) or not 0 < value <= 1):
            raise ValueError(f"{info.field_name} must be in (0, 1]")
        return value

    @field_validator("maximum_exclusion_ratio")
    @classmethod
    def _bounded_ratio(cls, value: float) -> float:
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("maximum_exclusion_ratio must be between 0 and 1")
        return value

    @field_validator("minimum_time_span", "maximum_time_gap")
    @classmethod
    def _positive_time(cls, value: float, info) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{info.field_name} must be positive and finite")
        return value

    @model_validator(mode="after")
    def _mode_valid(self) -> "ValidationAdequacyPlanSpec":
        if self.minimum_selected_points < 3 or self.minimum_distinct_timestamps < 3:
            raise ValueError("non-snapshot adequacy floors cannot be lower than three points/timestamps")
        family_ids = [item.family_id for item in self.family_quotas]
        if len(family_ids) != len(set(family_ids)):
            raise ValueError("family quota ids must be unique")
        parameter_ids = [item.parameter_id for item in self.parameter_temporal_policies]
        if len(parameter_ids) != len(set(parameter_ids)):
            raise ValueError("parameter temporal policy ids must be unique")
        for policy in self.parameter_temporal_policies:
            if policy.temporal_behavior != "time_varying":
                continue
            if int(policy.minimum_valid_points or 0) < self.minimum_per_parameter_valid_points:
                raise ValueError("per-parameter valid-point floor cannot lower the plan floor")
            if float(policy.minimum_valid_ratio or 0.0) < self.minimum_per_parameter_valid_ratio:
                raise ValueError("per-parameter valid-ratio floor cannot lower the plan floor")
            if int(policy.minimum_distinct_timestamps or 0) < self.minimum_distinct_timestamps:
                raise ValueError("per-parameter distinct-time floor cannot lower the plan floor")
            if float(policy.minimum_time_span or 0.0) < self.minimum_time_span:
                raise ValueError("per-parameter time-span floor cannot lower the plan floor")
            if float(policy.maximum_time_gap or math.inf) > self.maximum_time_gap:
                raise ValueError("per-parameter maximum-gap floor cannot weaken the plan floor")
        if self.sampling_mode == "adaptive":
            if (
                self.adaptive_converged is not True
                or not self.adaptive_evidence_id
                or self.adaptive_minimum_selected_points is None
                or self.adaptive_minimum_selected_ratio is None
            ):
                raise ValueError(
                    "adaptive sampling requires current convergence evidence and count/ratio floors"
                )
            for policy in self.parameter_temporal_policies:
                if policy.temporal_behavior == "time_varying" and not policy.convergence_evidence_id:
                    raise ValueError(
                        "adaptive sampling requires per-time-varying-parameter convergence floors"
                    )
        elif any(
            value is not None
            for value in (
                self.adaptive_converged,
                self.adaptive_evidence_id,
                self.adaptive_minimum_selected_points,
                self.adaptive_minimum_selected_ratio,
            )
        ):
            raise ValueError("adaptive evidence fields are valid only for adaptive sampling")
        return self


class CoverageFloorReceiptSpec(BaseModel):
    """Resolved anti-degeneracy floor; callers cannot lower the universal term."""

    model_config = ConfigDict(extra="forbid")

    algorithm_id: Literal["sqrt_n_stage_v1"] = ANTI_DEGENERACY_FLOOR_ALGORITHM
    available_count: int
    universal_minimum_count: int
    universal_minimum_ratio: float
    plan_minimum_count: int
    plan_minimum_ratio: float
    project_minimum_count: Optional[int] = None
    project_minimum_ratio: Optional[float] = None
    convergence_minimum_count: Optional[int] = None
    convergence_minimum_ratio: Optional[float] = None
    full_sequence_required: bool = False
    effective_minimum_count: int
    effective_minimum_ratio: float


class ValidationUniverseReceiptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    universe_fingerprint: str
    available_point_count: int
    eligible_point_count: int
    selected_point_count: int
    unique_selected_row_count: int
    evaluated_point_count: int
    validated_point_count: int
    available_signal_ids: list[str] = Field(default_factory=list)
    eligible_signal_ids: list[str] = Field(default_factory=list)
    selected_signal_ids: list[str] = Field(default_factory=list)
    validated_signal_ids: list[str] = Field(default_factory=list)
    excluded_signal_ids: list[str] = Field(default_factory=list)
    available_parameter_ids: list[str] = Field(default_factory=list)
    eligible_parameter_ids: list[str] = Field(default_factory=list)
    selected_parameter_ids: list[str] = Field(default_factory=list)
    validated_parameter_ids: list[str] = Field(default_factory=list)
    required_parameter_ids: list[str] = Field(default_factory=list)
    covered_parameter_ids: list[str] = Field(default_factory=list)
    point_selection_ratio: float
    signal_selection_ratio: float
    parameter_selection_ratio: float
    exclusion_ratio: float
    selection_floor: CoverageFloorReceiptSpec


class TemporalAdequacyReceiptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AdequacyStatus
    distinct_timestamp_count: int
    duplicate_timestamps: list[float] = Field(default_factory=list)
    time_span: Optional[float] = None
    maximum_observed_gap: Optional[float] = None
    covered_strata: list[str] = Field(default_factory=list)
    missing_strata: list[str] = Field(default_factory=list)
    missing_event_tags: list[str] = Field(default_factory=list)
    missing_peak_tags: list[str] = Field(default_factory=list)
    missing_boundary_tags: list[str] = Field(default_factory=list)
    missing_mode_ids: list[str] = Field(default_factory=list)
    duplicate_source_rows: list[str] = Field(default_factory=list)
    out_of_range_source_rows: list[str] = Field(default_factory=list)
    missing_source_lineage: list[str] = Field(default_factory=list)
    strata_results: list[dict[str, Any]] = Field(default_factory=list)


class PerSignalCoverageReceiptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    source_ids: list[str] = Field(default_factory=list)
    valid_point_count: int
    evaluated_point_count: int
    validated_point_count: int
    missing_point_count: int
    valid_ratio: float
    validated_ratio: float
    required_minimum_valid_points: int
    required_minimum_valid_ratio: float
    distinct_timestamp_count: int
    time_span: Optional[float] = None
    maximum_observed_gap: Optional[float] = None
    status: AdequacyStatus


class PerParameterCoverageReceiptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter_id: str
    temporal_behavior: ParameterTemporalBehavior
    classification_source: str
    availability_source_id: Optional[str] = None
    source_ids: list[str] = Field(default_factory=list)
    available_point_count: int
    selected_point_count: int
    unique_selected_row_count: int
    valid_point_count: int
    evaluated_point_count: int
    validated_point_count: int
    missing_point_count: int
    valid_ratio: float
    validated_ratio: float
    required_minimum_valid_points: Optional[int] = None
    required_minimum_valid_ratio: Optional[float] = None
    required_minimum_distinct_timestamps: Optional[int] = None
    required_minimum_time_span: Optional[float] = None
    required_maximum_time_gap: Optional[float] = None
    coverage_floor: Optional[CoverageFloorReceiptSpec] = None
    distinct_timestamp_count: int
    time_span: Optional[float] = None
    maximum_observed_gap: Optional[float] = None
    maximum_observed_row_gap: Optional[int] = None
    universal_maximum_row_gap: Optional[int] = None
    covered_universal_strata: list[str] = Field(default_factory=list)
    missing_universal_strata: list[str] = Field(default_factory=list)
    required_strata_results: list[dict[str, Any]] = Field(default_factory=list)
    residual_evidence_point_ids: list[str] = Field(default_factory=list)
    direction_evidence_scenario_ids: list[str] = Field(default_factory=list)
    direction_distinct_value_count: int = 0
    physical_envelope_declared: bool = False
    representative_evidence_status: Literal["pass", "blocked", "not_applicable"] = "not_applicable"
    model_parameter_exists: bool = False
    contribution_expectation: Optional[ParameterContributionExpectation] = None
    contribution_evidence_point_ids: list[str] = Field(default_factory=list)
    contribution_distinct_value_count: int = 0
    contribution_max_normalized_residual_effect: Optional[float] = None
    contribution_affected_residual_ids: list[str] = Field(default_factory=list)
    contribution_status: Literal[
        "pass", "blocked", "verified_non_sensitive", "not_applicable"
    ] = "not_applicable"
    non_sensitive_reason: Optional[str] = None
    non_sensitive_claim_boundary: Optional[str] = None
    status: AdequacyStatus


class FamilyCoverageReceiptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family_id: str
    member_ids: list[str]
    covered_member_ids: list[str]
    covered_count: int
    covered_ratio: float
    minimum_covered_count: int
    minimum_covered_ratio: float
    status: AdequacyStatus


class ValidationAdequacyReceiptSpec(BaseModel):
    """Native quantitative receipt; supervisors consume but do not recompute it."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["physicsguard_validation_adequacy_receipt"]
    receipt_version: Literal["1.0"] = "1.0"
    status: AdequacyStatus
    sampling_mode: Optional[SamplingMode] = None
    threshold_source: Optional[str] = None
    selection_policy_id: Optional[str] = None
    selection_rationale: Optional[str] = None
    sampling_policy_fingerprint: Optional[str] = None
    universe: ValidationUniverseReceiptSpec
    temporal: TemporalAdequacyReceiptSpec
    per_signal: list[PerSignalCoverageReceiptSpec] = Field(default_factory=list)
    per_parameter: list[PerParameterCoverageReceiptSpec] = Field(default_factory=list)
    signal_time_matrix: list[dict[str, Any]] = Field(default_factory=list)
    families: list[FamilyCoverageReceiptSpec] = Field(default_factory=list)
    subsystem_families: list[FamilyCoverageReceiptSpec] = Field(default_factory=list)
    missing_critical_signals: list[str] = Field(default_factory=list)
    missing_critical_parameters: list[str] = Field(default_factory=list)
    missing_parameter_temporal_classifications: list[str] = Field(default_factory=list)
    critical_point_ids: list[str] = Field(default_factory=list)
    critical_signal_ids: list[str] = Field(default_factory=list)
    critical_parameter_ids: list[str] = Field(default_factory=list)
    repeated_exclusion_reasons: dict[str, int] = Field(default_factory=dict)
    templated_exclusion_reasons: list[str] = Field(default_factory=list)
    finding_codes: list[str] = Field(default_factory=list)
    claim_boundary: str


__all__ = [
    "AdequacyStatus",
    "ANTI_DEGENERACY_FLOOR_ALGORITHM",
    "CoverageFloorReceiptSpec",
    "FamilyCoverageReceiptSpec",
    "FamilyMemberKind",
    "FamilyQuotaPlanSpec",
    "ParameterTemporalBehavior",
    "ParameterContributionExpectation",
    "ParameterTemporalPolicySpec",
    "ParameterTimeStratumSpec",
    "PerParameterCoverageReceiptSpec",
    "PerSignalCoverageReceiptSpec",
    "SamplingMode",
    "TemporalAdequacyReceiptSpec",
    "ValidationAdequacyPlanSpec",
    "ValidationAdequacyReceiptSpec",
    "ValidationUniverseReceiptSpec",
]
