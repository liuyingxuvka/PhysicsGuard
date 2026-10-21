"""Typed plans and observed series for dataset/time/scenario validation depth."""

from __future__ import annotations

import json
import math
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.observation_spec import ObservedValueSpec
from physicsguard.schema.predictive_rollout import ModelSemantics, PredictiveRolloutPlanSpec
from physicsguard.schema.validation_adequacy import ValidationAdequacyPlanSpec
from physicsguard.schema.variable import ensure_non_empty, is_qualified_variable_name


ValidationClaimScope = Literal["snapshot", "time_window", "scenario_set", "bounded_dataset"]


def _json_serializable(value: Any, field_name: str) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be JSON-serializable") from exc


class ValidationIdentityReferenceSpec(BaseModel):
    """One validation input file, named by an id and a path."""

    model_config = ConfigDict(extra="forbid")

    identity_id: str
    path: str
    case_ids: list[str] = Field(default_factory=list)

    @field_validator("identity_id", "path")
    @classmethod
    def _required_text(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)


    @field_validator("case_ids")
    @classmethod
    def _case_ids_valid(cls, values: list[str]) -> list[str]:
        normalized = [ensure_non_empty(value, "case_id") for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("case_ids must be unique")
        return normalized


class DatasetIdentityPlanSpec(BaseModel):
    """Exact data, schema, testbench, and parameter-role identity."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    files: list[ValidationIdentityReferenceSpec]
    field_schema: ValidationIdentityReferenceSpec
    parameter_roles: ValidationIdentityReferenceSpec
    testbench: ValidationIdentityReferenceSpec
    testbench_version: str

    @field_validator("dataset_id", "testbench_version")
    @classmethod
    def _required_text(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _files_valid(self) -> "DatasetIdentityPlanSpec":
        if not self.files:
            raise ValueError("dataset identity requires at least one data file")
        ids = [item.identity_id for item in self.files]
        if len(ids) != len(set(ids)):
            raise ValueError("dataset file identity_ids must be unique")
        return self


class MappingReviewPlanSpec(BaseModel):
    """Review of the referenced contracts' mapping edges consumed by validation."""

    model_config = ConfigDict(extra="forbid")

    minimum_confidence: float = 0.75

    @field_validator("minimum_confidence")
    @classmethod
    def _minimum_confidence_valid(cls, value: float) -> float:
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("minimum_confidence must be between 0 and 1")
        return value


class TimeScopePlanSpec(BaseModel):
    """Declared time/scenario claim boundary."""

    model_config = ConfigDict(extra="forbid")

    claim_scope: ValidationClaimScope
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    time_unit: str = "s"
    expected_point_count: Optional[int] = None

    @field_validator("start_time", "end_time")
    @classmethod
    def _times_finite(cls, value: Optional[float], info) -> Optional[float]:
        if value is not None and not math.isfinite(value):
            raise ValueError(f"{info.field_name} must be finite")
        return value

    @field_validator("time_unit")
    @classmethod
    def _unit_valid(cls, value: str) -> str:
        return ensure_non_empty(value, "time_unit")

    @field_validator("expected_point_count")
    @classmethod
    def _point_count_valid(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 1:
            raise ValueError("expected_point_count must be positive")
        return value

    @model_validator(mode="after")
    def _window_valid(self) -> "TimeScopePlanSpec":
        if self.start_time is not None and self.end_time is not None and self.start_time > self.end_time:
            raise ValueError("start_time must be less than or equal to end_time")
        return self


class ScenarioPerturbationSpec(BaseModel):
    """Declared scenario change; metadata only, never a hidden simulator."""

    model_config = ConfigDict(extra="forbid")

    target: str
    change: Literal["set", "add", "multiply", "toggle", "profile", "other"]
    value: Any
    unit: Optional[str] = None
    reason: str

    @field_validator("target", "reason")
    @classmethod
    def _required_text(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _value_serializable(self) -> "ScenarioPerturbationSpec":
        _json_serializable(self.value, "scenario perturbation value")
        return self


class ScenarioDefinitionSpec(BaseModel):
    """One declared scenario and its relationship to a baseline."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    case_ids: list[str] = Field(default_factory=list)
    baseline_scenario_id: Optional[str] = None
    perturbations: list[ScenarioPerturbationSpec] = Field(default_factory=list)
    description: Optional[str] = None

    @field_validator("scenario_id", "baseline_scenario_id")
    @classmethod
    def _ids_valid(cls, value: Optional[str], info) -> Optional[str]:
        if value is None:
            return value
        return ensure_non_empty(value, info.field_name)

    @field_validator("case_ids")
    @classmethod
    def _case_ids_valid(cls, values: list[str]) -> list[str]:
        normalized = [ensure_non_empty(value, "case_id") for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("scenario case_ids must be unique")
        return normalized


class CalibrationSplitPlanSpec(BaseModel):
    """Explicit train/holdout file and case identities."""

    model_config = ConfigDict(extra="forbid")

    training: list[ValidationIdentityReferenceSpec]
    holdout: list[ValidationIdentityReferenceSpec]

    @model_validator(mode="after")
    def _split_nonempty(self) -> "CalibrationSplitPlanSpec":
        if not self.training or not self.holdout:
            raise ValueError("calibration split requires training and holdout identities")
        return self


class ValidationDepthPlanSpec(BaseModel):
    """Depth extension attached to the existing model-validation plan."""

    model_config = ConfigDict(extra="forbid")

    dataset: DatasetIdentityPlanSpec
    mapping_review: MappingReviewPlanSpec
    observed_series: ValidationIdentityReferenceSpec
    time_scope: TimeScopePlanSpec
    model_semantics: ModelSemantics = "pointwise"
    adequacy: Optional[ValidationAdequacyPlanSpec] = None
    predictive_rollout: Optional[PredictiveRolloutPlanSpec] = None
    scenarios: list[ScenarioDefinitionSpec] = Field(default_factory=list)
    split: Optional[CalibrationSplitPlanSpec] = None
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("assumptions")
    @classmethod
    def _assumptions_valid(cls, values: list[str]) -> list[str]:
        return [ensure_non_empty(value, "assumption") for value in values]

    @model_validator(mode="after")
    def _scenario_ids_unique(self) -> "ValidationDepthPlanSpec":
        ids = [item.scenario_id for item in self.scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError("scenario ids must be unique")
        known = set(ids)
        for scenario in self.scenarios:
            if scenario.baseline_scenario_id and scenario.baseline_scenario_id not in known:
                raise ValueError(
                    f"scenario {scenario.scenario_id!r} references unknown baseline "
                    f"{scenario.baseline_scenario_id!r}"
                )
        if self.model_semantics == "pointwise" and self.predictive_rollout is not None:
            raise ValueError("pointwise_prediction_forbidden")
        return self


class ObservedSeriesPointSpec(BaseModel):
    """One point/case in a bounded observed series."""

    model_config = ConfigDict(extra="forbid")

    point_id: str
    timestamp: Optional[float] = None
    scenario_id: str = "default"
    case_id: Optional[str] = None
    source_identity_id: Optional[str] = None
    source_row_index: Optional[int] = None
    event_tags: list[str] = Field(default_factory=list)
    peak_tags: list[str] = Field(default_factory=list)
    boundary_tags: list[str] = Field(default_factory=list)
    mode_id: Optional[str] = None
    valid: bool = True
    invalid_reason: Optional[str] = None
    variables: dict[str, ObservedValueSpec] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "point_id",
        "scenario_id",
        "case_id",
        "source_identity_id",
        "mode_id",
        "invalid_reason",
    )
    @classmethod
    def _text_valid(cls, value: Optional[str], info) -> Optional[str]:
        if value is None:
            return value
        return ensure_non_empty(value, info.field_name)

    @field_validator("timestamp")
    @classmethod
    def _timestamp_finite(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not math.isfinite(value):
            raise ValueError("timestamp must be finite")
        return value

    @field_validator("source_row_index")
    @classmethod
    def _source_row_valid(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("source_row_index must be nonnegative")
        return value

    @field_validator("event_tags", "peak_tags", "boundary_tags")
    @classmethod
    def _tags_valid(cls, values: list[str], info) -> list[str]:
        normalized = [ensure_non_empty(value, info.field_name) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError(f"{info.field_name} must be unique")
        return normalized

    @model_validator(mode="after")
    def _point_valid(self) -> "ObservedSeriesPointSpec":
        if self.valid and not self.variables:
            raise ValueError("valid observed-series point requires variables")
        if not self.valid and not self.invalid_reason:
            raise ValueError("invalid observed-series point requires invalid_reason")
        for name in self.variables:
            if not is_qualified_variable_name(name):
                raise ValueError(f"observed variable {name!r} must use component.variable format")
        _json_serializable(self.metadata, "observed-series point metadata")
        return self


class ObservedSeriesSpec(BaseModel):
    """Bounded scalar/time/scenario observations evaluated pointwise."""

    model_config = ConfigDict(extra="forbid")

    series_id: str
    time_unit: str = "s"
    points: list[ObservedSeriesPointSpec]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("series_id", "time_unit")
    @classmethod
    def _required_text(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _series_valid(self) -> "ObservedSeriesSpec":
        if not self.points:
            raise ValueError("observed series requires at least one point")
        ids = [item.point_id for item in self.points]
        if len(ids) != len(set(ids)):
            raise ValueError("observed-series point_ids must be unique")
        _json_serializable(self.metadata, "observed-series metadata")
        return self


__all__ = [
    "CalibrationSplitPlanSpec",
    "DatasetIdentityPlanSpec",
    "MappingReviewPlanSpec",
    "ObservedSeriesPointSpec",
    "ObservedSeriesSpec",
    "ScenarioDefinitionSpec",
    "ScenarioPerturbationSpec",
    "TimeScopePlanSpec",
    "ValidationClaimScope",
    "ValidationDepthPlanSpec",
    "ValidationIdentityReferenceSpec",
]
