"""Schemas for model-dataset validation plans and reports."""

from __future__ import annotations

import json
import math
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.parameter_coverage import UsePolicy, ValidationRole
from physicsguard.schema.validation_depth import ValidationDepthPlanSpec, ValidationDepthReceiptSpec
from physicsguard.schema.variable import ensure_non_empty, is_qualified_variable_name


CalibrationMethod = Literal["none", "bounded_least_squares", "coarse_grid_then_least_squares"]
ValidationStatus = Literal["pass", "partial", "fail", "blocked"]


class ContractValidationReferenceSpec(BaseModel):
    """Contract referenced by a validation plan."""

    model_config = ConfigDict(extra="forbid")

    contract: str
    required_status: Literal["pass", "partial_allowed"] = "pass"

    @field_validator("contract")
    @classmethod
    def _contract_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "contract")


class ValidationVariableRoleSpec(BaseModel):
    """How one source field or model variable participates in validation."""

    model_config = ConfigDict(extra="forbid")

    source_id: Optional[str] = None
    target: str
    validation_role: ValidationRole
    use_policy: UsePolicy = "unspecified"
    mapping_confidence: Optional[float] = None
    measurement_confidence: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("target")
    @classmethod
    def _target_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "target")

    @field_validator("mapping_confidence", "measurement_confidence")
    @classmethod
    def _confidence_valid(cls, value: Optional[float], info) -> Optional[float]:
        if value is not None and not 0 <= value <= 1:
            raise ValueError(f"{info.field_name} must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "ValidationVariableRoleSpec":
        _ensure_json_serializable(self.metadata, "validation variable role metadata")
        return self


class PhysicalEnvelopeSpec(BaseModel):
    """Allowed range for observed or modeled physical variables."""

    model_config = ConfigDict(extra="forbid")

    target: str
    lower: Optional[float] = None
    upper: Optional[float] = None
    unit: Optional[str] = None
    severity: Literal["error", "warning"] = "warning"
    reason: Optional[str] = None

    @field_validator("target")
    @classmethod
    def _target_valid(cls, value: str) -> str:
        return ensure_non_empty(value, "target")

    @model_validator(mode="after")
    def _bounds_valid(self) -> "PhysicalEnvelopeSpec":
        if self.lower is None and self.upper is None:
            raise ValueError("physical envelope requires lower or upper bound")
        if self.lower is not None and not math.isfinite(self.lower):
            raise ValueError("lower must be finite")
        if self.upper is not None and not math.isfinite(self.upper):
            raise ValueError("upper must be finite")
        if self.lower is not None and self.upper is not None and self.lower >= self.upper:
            raise ValueError("lower must be less than upper")
        return self


class RedundantSensorCheckSpec(BaseModel):
    """Consistency check for distinct sources measuring the same target."""

    model_config = ConfigDict(extra="forbid")

    check_id: str
    left: str
    right: str
    target: str
    tolerance_abs: Optional[float] = None
    tolerance_normalized: Optional[float] = None
    scale: Optional[float] = None
    severity: Literal["error", "warning"] = "warning"

    @field_validator("check_id", "left", "right", "target")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _check_valid(self) -> "RedundantSensorCheckSpec":
        if self.left == self.right:
            raise ValueError("redundant sensor check needs two distinct variables")
        if self.tolerance_abs is None and self.tolerance_normalized is None:
            raise ValueError("redundant sensor check requires absolute or normalized tolerance")
        for field_name in ("tolerance_abs", "tolerance_normalized", "scale"):
            value = getattr(self, field_name)
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError(f"{field_name} must be finite and nonnegative")
        if self.tolerance_normalized is not None and self.scale is None:
            raise ValueError("normalized tolerance requires scale")
        if self.scale is not None and self.scale <= 0:
            raise ValueError("scale must be positive")
        return self


class CalibrationParameterSpec(BaseModel):
    """Explicit bounded parameter allowed to move during calibration."""

    model_config = ConfigDict(extra="forbid")

    name: str
    lower: float
    upper: float
    initial: float
    scale: float
    unit: Optional[str] = None
    reason: str

    @field_validator("name", "reason")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _parameter_valid(self) -> "CalibrationParameterSpec":
        for field_name in ("lower", "upper", "initial", "scale"):
            value = getattr(self, field_name)
            if not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite")
        if self.lower >= self.upper:
            raise ValueError("lower must be less than upper")
        if not self.lower <= self.initial <= self.upper:
            raise ValueError("initial must be inside bounds")
        if self.scale <= 0:
            raise ValueError("scale must be positive")
        return self


class CalibrationPlanSpec(BaseModel):
    """Conservative calibration configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    method: CalibrationMethod = "none"
    train_observed: Optional[str] = None
    holdout_observed: Optional[str] = None
    max_parameters_without_review: int = 5
    parameters: list[CalibrationParameterSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _calibration_valid(self) -> "CalibrationPlanSpec":
        if not self.enabled and self.method != "none":
            raise ValueError("disabled calibration must use method none")
        if self.enabled:
            if self.method == "none":
                raise ValueError("enabled calibration requires a calibration method")
            if not self.parameters:
                raise ValueError("enabled calibration requires parameters")
            if len(self.parameters) > self.max_parameters_without_review:
                raise ValueError("too many calibration parameters without review")
            names = [item.name for item in self.parameters]
            if len(names) != len(set(names)):
                raise ValueError("calibration parameter names must be unique")
        return self


class ModelValidationPlanSpec(BaseModel):
    """Plan for validating a PhysicsGuard model against contracted data."""

    model_config = ConfigDict(extra="forbid")

    validation_id: str
    audit_file: str
    observed_file: str
    evidence_registry: Optional[str] = None
    evidence_bundle_id: Optional[str] = None
    contracts: list[ContractValidationReferenceSpec] = Field(default_factory=list)
    variable_roles: list[ValidationVariableRoleSpec] = Field(default_factory=list)
    physical_envelopes: list[PhysicalEnvelopeSpec] = Field(default_factory=list)
    redundant_sensor_checks: list[RedundantSensorCheckSpec] = Field(default_factory=list)
    calibration: CalibrationPlanSpec = Field(default_factory=CalibrationPlanSpec)
    depth: Optional[ValidationDepthPlanSpec] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("validation_id", "audit_file", "observed_file")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("evidence_registry", "evidence_bundle_id")
    @classmethod
    def _optional_strings_not_empty(cls, value: Optional[str], info) -> Optional[str]:
        if value is not None:
            return ensure_non_empty(value, info.field_name)
        return value

    @model_validator(mode="after")
    def _plan_valid(self) -> "ModelValidationPlanSpec":
        targets = [role.target for role in self.variable_roles]
        for target in targets:
            if "." in target and not is_qualified_variable_name(target):
                raise ValueError("qualified model targets must use component.variable format")
        if self.depth is not None and self.depth.time_scope.claim_scope != "snapshot" and not self.variable_roles:
            raise ValueError("non-snapshot validation requires non-empty variable_roles")
        _ensure_json_serializable(self.metadata, "validation plan metadata")
        return self


class ConfidenceUpdateSpec(BaseModel):
    """Post-validation confidence feedback for a source/target mapping."""

    model_config = ConfigDict(extra="forbid")

    source_id: Optional[str] = None
    target: str
    validation_confidence: float
    reason: str
    action: Literal["none", "prefer", "fallback", "review_required", "exclude_from_fit"]

    @field_validator("target", "reason")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @field_validator("validation_confidence")
    @classmethod
    def _confidence_valid(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("validation_confidence must be between 0 and 1")
        return value


class ValidationFindingReportSpec(BaseModel):
    """Machine-readable validation finding."""

    model_config = ConfigDict(extra="forbid")

    severity: str
    type: str
    message: str
    source_id: Optional[str] = None
    field_name: Optional[str] = None
    target: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("severity", "type", "message")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _details_json_serializable(self) -> "ValidationFindingReportSpec":
        _ensure_json_serializable(self.details, "validation finding details")
        return self


class CalibrationReportSpec(BaseModel):
    """Calibration result fields kept separate from validation pass/fail."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    method: CalibrationMethod
    optimization_success: Optional[bool] = None
    message: Optional[str] = None
    initial_parameters: dict[str, float] = Field(default_factory=dict)
    calibrated_parameters: dict[str, float] = Field(default_factory=dict)
    parameters_at_bounds: list[str] = Field(default_factory=list)
    train_max_abs_normalized_residual_after: Optional[float] = None
    holdout_audit_pass: Optional[bool] = None
    holdout_max_abs_normalized_residual: Optional[float] = None


class ModelDatasetValidationReportSpec(BaseModel):
    """Stable outer schema for model-dataset validation reports."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["model_dataset_validation"]
    validation_id: str
    status: ValidationStatus
    ok: bool
    direct_validation: dict[str, Any]
    envelope_findings: list[ValidationFindingReportSpec] = Field(default_factory=list)
    redundant_sensor_findings: list[ValidationFindingReportSpec] = Field(default_factory=list)
    calibration: CalibrationReportSpec
    depth_receipt: ValidationDepthReceiptSpec
    confidence_updates: list[ConfidenceUpdateSpec] = Field(default_factory=list)
    findings: list[ValidationFindingReportSpec] = Field(default_factory=list)
    safe_claim: str
    unsafe_claim_boundary: str
    next_actions: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)

    @field_validator("validation_id", "safe_claim", "unsafe_claim_boundary")
    @classmethod
    def _required_strings(cls, value: str, info) -> str:
        return ensure_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _report_json_serializable(self) -> "ModelDatasetValidationReportSpec":
        _ensure_json_serializable(self.direct_validation, "direct validation report")
        _ensure_json_serializable(self.summary, "validation report summary")
        return self


def _ensure_json_serializable(value: Any, field_name: str) -> None:
    try:
        json.dumps(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be JSON-serializable") from exc


__all__ = [
    "CalibrationMethod",
    "CalibrationParameterSpec",
    "CalibrationPlanSpec",
    "CalibrationReportSpec",
    "ConfidenceUpdateSpec",
    "ContractValidationReferenceSpec",
    "ModelDatasetValidationReportSpec",
    "ModelValidationPlanSpec",
    "PhysicalEnvelopeSpec",
    "RedundantSensorCheckSpec",
    "ValidationStatus",
    "ValidationFindingReportSpec",
    "ValidationVariableRoleSpec",
    "ValidationDepthPlanSpec",
    "ValidationDepthReceiptSpec",
]
