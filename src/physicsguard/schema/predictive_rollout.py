"""Typed future-holdout predictive rollout contracts."""

from __future__ import annotations

import json
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.variable import ensure_non_empty


ModelSemantics = Literal["pointwise", "stateful_dynamic"]
PredictiveStatus = Literal["pass", "blocked", "not_authorized", "not_declared"]


class RolloutArtifactIdentitySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity_id: str
    path: str
    case_ids: list[str] = Field(default_factory=list)

    @field_validator("identity_id", "path")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)


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
    producer_id: str | None = None
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

    @model_validator(mode="before")
    @classmethod
    def _producer_name(cls, value: Any) -> Any:
        if isinstance(value, dict) and "producer_receipt_id" in value:
            raise ValueError("use producer_id for the trajectory producer identity")
        return value

    @field_validator("rollout_id", "step_unit", "threshold_source")
    @classmethod
    def _text_valid(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("producer_id")
    @classmethod
    def _optional_text_valid(cls, value: str | None, info) -> str | None:
        return None if value is None else ensure_non_empty(value, info.field_name)

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


__all__ = [
    "ModelSemantics",
    "PredictiveRolloutPlanSpec",
    "PredictiveStatus",
    "PredictiveThresholdsSpec",
    "RolloutArtifactIdentitySpec",
]
