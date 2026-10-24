"""Typed contracts for target-owned validation sampling adequacy."""

from __future__ import annotations

import math
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_non_empty


def unit_ratio_or_none(value: Optional[float], field_name: str) -> Optional[float]:
    """An optional ratio must be finite and in (0, 1]."""
    if value is not None and (not math.isfinite(value) or not 0 < value <= 1):
        raise ValueError(f"{field_name} must be in (0, 1]")
    return value


def unique_non_empty_texts(values: list[str], field_name: str) -> list[str]:
    """Each text must be non-empty and the list must have no repeats."""
    normalized = [ensure_non_empty(value, field_name) for value in values]
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must be unique")
    return normalized


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
        return unit_ratio_or_none(value, info.field_name)

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
        missing = [name for name, value in temporal_fields.items() if name == "availability_source_id" and value is None]
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
        if self.required_strata and len(self.required_strata) < 3:
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
    threshold_source: str = "current contract manifest"
    selection_policy_id: str = "full_manifest_rows"
    selection_rationale: str = "Evaluate every usable source row from the manifest."
    minimum_selected_points: int = 3
    minimum_selected_ratio: float = 0.1
    minimum_distinct_timestamps: int = 3
    minimum_time_span: float = 1.0e-12
    maximum_time_gap: float = 1.0e300
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
        return unique_non_empty_texts(values, info.field_name)

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
        return unit_ratio_or_none(value, info.field_name)

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
            if policy.minimum_valid_points is not None and "minimum_per_parameter_valid_points" in self.model_fields_set and int(policy.minimum_valid_points or 0) < self.minimum_per_parameter_valid_points:
                raise ValueError("per-parameter valid-point floor cannot lower the plan floor")
            if policy.minimum_valid_ratio is not None and "minimum_per_parameter_valid_ratio" in self.model_fields_set and float(policy.minimum_valid_ratio or 0.0) < self.minimum_per_parameter_valid_ratio:
                raise ValueError("per-parameter valid-ratio floor cannot lower the plan floor")
            if policy.minimum_distinct_timestamps is not None and "minimum_distinct_timestamps" in self.model_fields_set and int(policy.minimum_distinct_timestamps or 0) < self.minimum_distinct_timestamps:
                raise ValueError("per-parameter distinct-time floor cannot lower the plan floor")
            if policy.minimum_time_span is not None and "minimum_time_span" in self.model_fields_set and float(policy.minimum_time_span or 0.0) < self.minimum_time_span:
                raise ValueError("per-parameter time-span floor cannot lower the plan floor")
            if policy.maximum_time_gap is not None and "maximum_time_gap" in self.model_fields_set and float(policy.maximum_time_gap or math.inf) > self.maximum_time_gap:
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


__all__ = [
    "AdequacyStatus",
    "ANTI_DEGENERACY_FLOOR_ALGORITHM",
    "FamilyMemberKind",
    "FamilyQuotaPlanSpec",
    "ParameterTemporalBehavior",
    "ParameterContributionExpectation",
    "ParameterTemporalPolicySpec",
    "ParameterTimeStratumSpec",
    "SamplingMode",
    "ValidationAdequacyPlanSpec",
]
