"""Typed future-holdout predictive rollout contracts."""

from __future__ import annotations

import json
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_non_empty


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ModelSemantics = Literal["pointwise", "stateful_dynamic"]
PredictiveStatus = Literal["pass", "blocked", "not_authorized", "not_declared"]


class RolloutArtifactIdentitySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity_id: str
    path: str
    sha256: str
    case_ids: list[str] = Field(default_factory=list)

    @field_validator("identity_id", "path")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("sha256")
    @classmethod
    def _hash_valid(cls, value: str) -> str:
        normalized = ensure_non_empty(value, "sha256").lower()
        if not SHA256_PATTERN.fullmatch(normalized):
            raise ValueError("sha256 must be a lowercase 64-character digest")
        return normalized

    @field_validator("case_ids")
    @classmethod
    def _cases_valid(cls, values: list[str]) -> list[str]:
        normalized = [ensure_non_empty(value, "case_id") for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("case_ids must be unique")
        return normalized


class PredictiveThresholdsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maximum_worst_step_normalized_error: float
    maximum_accumulated_normalized_error: float
    maximum_absolute_lag_steps: int = 0
    maximum_phase_error: float = 0.0
    maximum_drift: float
    maximum_error_growth: float

    @field_validator(
        "maximum_worst_step_normalized_error",
        "maximum_accumulated_normalized_error",
        "maximum_phase_error",
        "maximum_drift",
        "maximum_error_growth",
    )
    @classmethod
    def _nonnegative_finite(cls, value: float, info) -> float:
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{info.field_name} must be nonnegative and finite")
        return value

    @field_validator("maximum_absolute_lag_steps")
    @classmethod
    def _lag_valid(cls, value: int) -> int:
        if value < 0:
            raise ValueError("maximum_absolute_lag_steps must be nonnegative")
        return value


class PredictiveRolloutPlanSpec(BaseModel):
    """Exact externally produced trajectory and future-holdout comparison plan."""

    model_config = ConfigDict(extra="forbid")

    rollout_id: str
    producer_receipt_id: str
    model_identity: RolloutArtifactIdentitySpec
    training: list[RolloutArtifactIdentitySpec]
    prediction_series: RolloutArtifactIdentitySpec
    future_holdout_series: RolloutArtifactIdentitySpec
    training_end_time: float
    initial_state: dict[str, float]
    step_size: float
    step_unit: str = "s"
    horizon_steps: int
    target_signals: list[str]
    signal_scales: dict[str, float]
    threshold_source: str
    thresholds: PredictiveThresholdsSpec

    @field_validator("rollout_id", "producer_receipt_id", "step_unit", "threshold_source")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("training_end_time", "step_size")
    @classmethod
    def _time_valid(cls, value: float, info) -> float:
        if not math.isfinite(value) or (info.field_name == "step_size" and value <= 0):
            raise ValueError(f"{info.field_name} must be finite and step_size must be positive")
        return value

    @field_validator("horizon_steps")
    @classmethod
    def _horizon_valid(cls, value: int) -> int:
        if value < 2:
            raise ValueError("horizon_steps must be at least two")
        return value

    @field_validator("target_signals")
    @classmethod
    def _targets_valid(cls, values: list[str]) -> list[str]:
        normalized = [ensure_non_empty(value, "target_signal") for value in values]
        if not normalized or len(normalized) != len(set(normalized)):
            raise ValueError("target_signals must be non-empty and unique")
        return normalized

    @model_validator(mode="after")
    def _plan_valid(self) -> "PredictiveRolloutPlanSpec":
        if not self.training:
            raise ValueError("predictive rollout requires training identities")
        if not self.initial_state:
            raise ValueError("predictive rollout requires an explicit initial_state")
        for key, value in self.initial_state.items():
            ensure_non_empty(key, "initial_state key")
            if not math.isfinite(value):
                raise ValueError("initial_state values must be finite")
        if set(self.signal_scales) != set(self.target_signals):
            raise ValueError("signal_scales must exactly cover target_signals")
        if any(not math.isfinite(value) or value <= 0 for value in self.signal_scales.values()):
            raise ValueError("signal scales must be positive and finite")
        try:
            json.dumps(self.initial_state)
        except (TypeError, ValueError) as exc:
            raise ValueError("initial_state must be JSON-serializable") from exc
        return self


class PredictiveIdentityReceiptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity_id: str
    path: str
    expected_sha256: str
    actual_sha256: str | None = None
    status: Literal["current", "stale", "missing"]
    case_ids: list[str] = Field(default_factory=list)


class PredictiveMetricsReceiptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aligned_step_count: int
    worst_step_normalized_error: float | None = None
    accumulated_normalized_error: float | None = None
    lag_steps: int | None = None
    phase_error: float | None = None
    drift: float | None = None
    error_growth: float | None = None
    stability_pass: bool
    threshold_results: dict[str, bool] = Field(default_factory=dict)


class PredictiveRolloutReceiptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["physicsguard_predictive_rollout_receipt"]
    receipt_version: Literal["1.0"] = "1.0"
    status: PredictiveStatus
    model_semantics: ModelSemantics
    rollout_id: str | None = None
    producer_receipt_id: str | None = None
    model_identity: PredictiveIdentityReceiptSpec | None = None
    training: list[PredictiveIdentityReceiptSpec] = Field(default_factory=list)
    prediction_series: PredictiveIdentityReceiptSpec | None = None
    future_holdout_series: PredictiveIdentityReceiptSpec | None = None
    overlapping_paths: list[str] = Field(default_factory=list)
    overlapping_hashes: list[str] = Field(default_factory=list)
    overlapping_case_ids: list[str] = Field(default_factory=list)
    alignment_gaps: list[str] = Field(default_factory=list)
    metrics: PredictiveMetricsReceiptSpec
    finding_codes: list[str] = Field(default_factory=list)
    covered_horizon: dict[str, Any] = Field(default_factory=dict)
    claim_boundary: str


__all__ = [
    "ModelSemantics",
    "PredictiveIdentityReceiptSpec",
    "PredictiveMetricsReceiptSpec",
    "PredictiveRolloutPlanSpec",
    "PredictiveRolloutReceiptSpec",
    "PredictiveStatus",
    "PredictiveThresholdsSpec",
    "RolloutArtifactIdentitySpec",
]
