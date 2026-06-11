"""Model-versus-dataset validation with conservative calibration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import least_squares

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.core.parameter_coverage import ContractFinding, ContractReview
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.test_file_contract import check_test_file_contract
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values
from physicsguard.io.test_file_contract_loader import load_model_validation_plan
from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
from physicsguard.schema.model_dataset_validation import (
    CalibrationParameterSpec,
    ConfidenceUpdateSpec,
    ModelValidationPlanSpec,
)
from physicsguard.schema.observation_spec import ObservedValuesSpec
from physicsguard.schema.system_spec import ComponentInstanceSpec, SystemSpec


BOUND_HIT_TOLERANCE = 1e-6


@dataclass(frozen=True)
class CalibrationSummary:
    enabled: bool
    method: str
    optimization_success: bool | None = None
    message: str | None = None
    initial_parameters: dict[str, float] = field(default_factory=dict)
    calibrated_parameters: dict[str, float] = field(default_factory=dict)
    parameters_at_bounds: list[str] = field(default_factory=list)
    train_max_abs_normalized_residual_after: float | None = None
    holdout_audit_pass: bool | None = None
    holdout_max_abs_normalized_residual: float | None = None


@dataclass(frozen=True)
class ModelDatasetValidationReport:
    artifact_kind: str
    validation_id: str
    status: str
    ok: bool
    direct_validation: dict[str, Any]
    envelope_findings: list[dict[str, Any]]
    redundant_sensor_findings: list[dict[str, Any]]
    calibration: dict[str, Any]
    confidence_updates: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    safe_claim: str
    unsafe_claim_boundary: str
    next_actions: list[str]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_model_dataset(path: str | Path) -> ModelDatasetValidationReport:
    plan_path = Path(path)
    plan = load_model_validation_plan(plan_path)
    base_dir = plan_path.parent
    findings: list[ContractFinding] = []
    findings.extend(_contract_findings(plan, base_dir))

    audit_path = _resolve_path(base_dir, plan.audit_file)
    observed_path = _resolve_path(base_dir, plan.observed_file)
    spec = load_hierarchical_audit_spec(audit_path)
    observed = load_observed_values(observed_path)
    direct = _evaluate(spec, observed)
    if not direct["audit_pass"]:
        findings.append(
            ContractFinding(
                severity="warning",
                type="direct_validation_audit_failed",
                message="direct no-fit observed validation did not pass",
                details={"max_abs_normalized_residual": direct["max_abs_normalized_residual"]},
            )
        )

    envelope_findings = _envelope_findings(plan, observed)
    redundant_findings = _redundant_sensor_findings(plan, observed)
    findings.extend(_finding_from_dict(item) for item in envelope_findings + redundant_findings)

    calibration = _calibration_summary(plan, base_dir, spec, observed)
    if calibration.optimization_success is True and calibration.holdout_audit_pass is False:
        findings.append(
            ContractFinding(
                severity="warning",
                type="calibration_holdout_failed",
                message="calibration optimizer succeeded but holdout validation did not pass",
                details={
                    "holdout_max_abs_normalized_residual": calibration.holdout_max_abs_normalized_residual,
                },
            )
        )
    for parameter in calibration.parameters_at_bounds:
        findings.append(
            ContractFinding(
                severity="warning",
                type="calibration_parameter_at_bound",
                message="calibrated parameter ended near a finite bound",
                target=parameter,
            )
        )

    confidence_updates = _confidence_updates(plan, envelope_findings, redundant_findings, direct)
    status = _status(findings, direct, calibration)
    return ModelDatasetValidationReport(
        artifact_kind="model_dataset_validation",
        validation_id=plan.validation_id,
        status=status,
        ok=status == "pass",
        direct_validation=direct,
        envelope_findings=envelope_findings,
        redundant_sensor_findings=redundant_findings,
        calibration=asdict(calibration),
        confidence_updates=[item.model_dump(mode="json") for item in confidence_updates],
        findings=[asdict(item) for item in findings],
        safe_claim=_safe_claim(status),
        unsafe_claim_boundary=(
            "validation does not prove high-fidelity correctness, commercial-model "
            "equivalence, or validity outside the checked contract/model/data boundary"
        ),
        next_actions=_next_actions(findings),
        summary={
            "contract_count": len(plan.contracts),
            "envelope_count": len(plan.physical_envelopes),
            "redundant_sensor_check_count": len(plan.redundant_sensor_checks),
            "calibration_enabled": plan.calibration.enabled,
            "semantics": (
                "optimizer convergence is reported separately from validation pass; "
                "observed values are not mutated"
            ),
        },
    )


def _contract_findings(plan: ModelValidationPlanSpec, base_dir: Path) -> list[ContractFinding]:
    findings: list[ContractFinding] = []
    for reference in plan.contracts:
        contract_path = _resolve_path(base_dir, reference.contract)
        try:
            review = check_test_file_contract(contract_path)
        except Exception as exc:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="validation_contract_check_failed",
                    message=f"failed to check referenced contract: {exc}",
                    target=str(contract_path),
                )
            )
            continue
        if reference.required_status == "pass" and review.status != "pass":
            findings.append(
                ContractFinding(
                    severity="error",
                    type="validation_contract_not_passed",
                    message="validation requires a passing test-file contract",
                    target=str(contract_path),
                    details={"status": review.status},
                )
            )
        elif review.status == "fail":
            findings.append(
                ContractFinding(
                    severity="error",
                    type="validation_contract_failed",
                    message="referenced contract failed",
                    target=str(contract_path),
                )
            )
    return findings


def _evaluate(spec: HierarchicalAuditSpec, observed: ObservedValuesSpec) -> dict[str, Any]:
    report = HierarchicalAuditRunner(spec).evaluate_observed(observed)
    return {
        "audit_pass": report.audit_pass,
        "max_abs_normalized_residual": report.max_abs_normalized_residual,
        "residual_norm": report.residual_norm,
        "top_residuals": [asdict(item) for item in report.top_residuals],
        "top_blocks": [asdict(item) for item in report.top_blocks],
        "warnings": report.warnings,
    }


def _envelope_findings(
    plan: ModelValidationPlanSpec,
    observed: ObservedValuesSpec,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for envelope in plan.physical_envelopes:
        if envelope.target not in observed.variables:
            continue
        value = observed.variables[envelope.target].value
        failed = False
        if envelope.lower is not None and value < envelope.lower:
            failed = True
        if envelope.upper is not None and value > envelope.upper:
            failed = True
        if failed:
            findings.append(
                {
                    "severity": envelope.severity,
                    "type": "physical_envelope_violation",
                    "message": "observed value is outside declared physical envelope",
                    "target": envelope.target,
                    "details": {
                        "value": value,
                        "lower": envelope.lower,
                        "upper": envelope.upper,
                        "unit": envelope.unit,
                        "reason": envelope.reason,
                    },
                }
            )
    return findings


def _redundant_sensor_findings(
    plan: ModelValidationPlanSpec,
    observed: ObservedValuesSpec,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for check in plan.redundant_sensor_checks:
        if check.left not in observed.variables or check.right not in observed.variables:
            findings.append(
                {
                    "severity": check.severity,
                    "type": "redundant_sensor_value_missing",
                    "message": "redundant sensor check references missing observed values",
                    "target": check.check_id,
                    "details": {"left": check.left, "right": check.right},
                }
            )
            continue
        left = observed.variables[check.left].value
        right = observed.variables[check.right].value
        delta = abs(left - right)
        normalized = delta / check.scale if check.scale else None
        failed = False
        if check.tolerance_abs is not None and delta > check.tolerance_abs:
            failed = True
        if (
            check.tolerance_normalized is not None
            and normalized is not None
            and normalized > check.tolerance_normalized
        ):
            failed = True
        if failed:
            findings.append(
                {
                    "severity": check.severity,
                    "type": "redundant_sensor_mismatch",
                    "message": "redundant sensor values differ beyond tolerance",
                    "target": check.check_id,
                    "details": {
                        "left": check.left,
                        "right": check.right,
                        "delta": delta,
                        "normalized_delta": normalized,
                        "target": check.target,
                    },
                }
            )
    return findings


def _calibration_summary(
    plan: ModelValidationPlanSpec,
    base_dir: Path,
    spec: HierarchicalAuditSpec,
    observed: ObservedValuesSpec,
) -> CalibrationSummary:
    calibration = plan.calibration
    if not calibration.enabled:
        return CalibrationSummary(enabled=False, method="none")
    parameters = calibration.parameters
    _validate_calibration_parameter_targets(spec.system, parameters)
    initial = np.array([item.initial for item in parameters], dtype=float)
    lower = np.array([item.lower for item in parameters], dtype=float)
    upper = np.array([item.upper for item in parameters], dtype=float)
    train_observed = (
        load_observed_values(_resolve_path(base_dir, calibration.train_observed))
        if calibration.train_observed
        else observed
    )

    def residual_vector(values: np.ndarray) -> np.ndarray:
        calibrated = _with_parameters(spec.system, parameters, values)
        return _normalized_residuals(calibrated, train_observed)

    start = (
        _coarse_grid_start(residual_vector, initial, lower, upper)
        if calibration.method == "coarse_grid_then_least_squares"
        else initial
    )
    result = least_squares(residual_vector, start, bounds=(lower, upper), x_scale=[item.scale for item in parameters])
    calibrated_values = {item.name: float(value) for item, value in zip(parameters, result.x)}
    parameters_at_bounds = [
        item.name
        for item, value in zip(parameters, result.x)
        if abs(value - item.lower) <= BOUND_HIT_TOLERANCE or abs(value - item.upper) <= BOUND_HIT_TOLERANCE
    ]
    calibrated_spec = spec.model_copy(update={"system": _with_parameters(spec.system, parameters, result.x)})
    train_after = _evaluate(calibrated_spec, train_observed)
    holdout_pass = None
    holdout_max = None
    if calibration.holdout_observed:
        holdout = load_observed_values(_resolve_path(base_dir, calibration.holdout_observed))
        holdout_after = _evaluate(calibrated_spec, holdout)
        holdout_pass = bool(holdout_after["audit_pass"])
        holdout_max = float(holdout_after["max_abs_normalized_residual"])
    return CalibrationSummary(
        enabled=True,
        method=calibration.method,
        optimization_success=bool(result.success),
        message=str(result.message),
        initial_parameters={item.name: item.initial for item in parameters},
        calibrated_parameters=calibrated_values,
        parameters_at_bounds=parameters_at_bounds,
        train_max_abs_normalized_residual_after=float(train_after["max_abs_normalized_residual"]),
        holdout_audit_pass=holdout_pass,
        holdout_max_abs_normalized_residual=holdout_max,
    )


def _normalized_residuals(system: SystemSpec, observed: ObservedValuesSpec) -> np.ndarray:
    builder = ResidualBuilder(system)
    registry = builder.build_registry()
    values = {
        name: float(observed.variables[name].value)
        for name in registry.names()
        if name in observed.variables
    }
    missing = sorted(set(registry.names()) - set(values))
    if missing:
        raise ValueError("observed values missing variables for calibration: " + ", ".join(missing))
    x = registry.dict_to_vector(values)
    return np.array([record.normalized_value for record in builder.solver_residual_records(x)], dtype=float)


def _validate_calibration_parameter_targets(
    system: SystemSpec,
    parameters: list[CalibrationParameterSpec],
) -> None:
    component_parameters = {component.id: set(component.parameters) for component in system.components}
    missing: list[str] = []
    malformed: list[str] = []
    for parameter in parameters:
        if "." not in parameter.name:
            malformed.append(parameter.name)
            continue
        component_id, parameter_name = parameter.name.split(".", 1)
        if not component_id or not parameter_name:
            malformed.append(parameter.name)
            continue
        if component_id not in component_parameters or parameter_name not in component_parameters[component_id]:
            missing.append(parameter.name)
    if malformed:
        raise ValueError(
            "calibration parameters must use component.parameter names: " + ", ".join(sorted(malformed))
        )
    if missing:
        raise ValueError("calibration parameters not found in audit system: " + ", ".join(sorted(missing)))


def _coarse_grid_start(
    residual_vector,
    initial: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> np.ndarray:
    """Pick a conservative finite starting point before bounded least squares."""
    candidates = [initial]
    for index in range(len(initial)):
        for value in (lower[index], (lower[index] + upper[index]) / 2.0, upper[index]):
            candidate = np.array(initial, dtype=float)
            candidate[index] = value
            candidates.append(candidate)
    best = initial
    best_norm = math.inf
    for candidate in candidates:
        residuals = residual_vector(candidate)
        norm = float(np.linalg.norm(residuals))
        if norm < best_norm:
            best_norm = norm
            best = candidate
    return best


def _with_parameters(
    system: SystemSpec,
    parameters: list[CalibrationParameterSpec],
    values: np.ndarray,
) -> SystemSpec:
    replacements = {item.name: float(value) for item, value in zip(parameters, values)}
    components: list[ComponentInstanceSpec] = []
    for component in system.components:
        data = component.model_dump(mode="python")
        params = dict(data.get("parameters", {}))
        prefix = f"{component.id}."
        for name, value in replacements.items():
            if name.startswith(prefix):
                params[name[len(prefix) :]] = value
        data["parameters"] = params
        components.append(ComponentInstanceSpec.model_validate(data))
    return system.model_copy(update={"components": components})


def _confidence_updates(
    plan: ModelValidationPlanSpec,
    envelope_findings: list[dict[str, Any]],
    redundant_findings: list[dict[str, Any]],
    direct: dict[str, Any],
) -> list[ConfidenceUpdateSpec]:
    updates: list[ConfidenceUpdateSpec] = []
    bad_targets = {item.get("target") for item in envelope_findings if item.get("severity") in {"error", "warning"}}
    bad_targets.update(
        item.get("details", {}).get("target")
        for item in redundant_findings
        if item.get("severity") in {"error", "warning"}
    )
    for role in plan.variable_roles:
        if role.target in bad_targets:
            updates.append(
                ConfidenceUpdateSpec(
                    source_id=role.source_id,
                    target=role.target,
                    validation_confidence=0.35,
                    reason="validation finding affected this target",
                    action="review_required",
                )
            )
        elif direct["audit_pass"] and role.validation_role in {"model_input", "validation_output", "redundant_measurement"}:
            updates.append(
                ConfidenceUpdateSpec(
                    source_id=role.source_id,
                    target=role.target,
                    validation_confidence=max(role.measurement_confidence or 0.7, 0.7),
                    reason="direct validation passed inside declared boundary",
                    action="none",
                )
            )
    return updates


def _finding_from_dict(value: dict[str, Any]) -> ContractFinding:
    return ContractFinding(
        severity=str(value.get("severity", "warning")),
        type=str(value.get("type", "validation_finding")),
        message=str(value.get("message", "")),
        target=value.get("target"),
        details=dict(value.get("details", {})),
    )


def _status(
    findings: list[ContractFinding],
    direct: dict[str, Any],
    calibration: CalibrationSummary,
) -> str:
    if any(finding.severity == "error" for finding in findings):
        return "fail"
    if calibration.optimization_success is True and calibration.holdout_audit_pass is False:
        return "partial"
    if not direct["audit_pass"] and not calibration.holdout_audit_pass:
        return "partial"
    if any(finding.severity == "warning" for finding in findings):
        return "partial"
    return "pass"


def _safe_claim(status: str) -> str:
    if status == "pass":
        return "model-dataset validation passed inside the checked low-fidelity boundary"
    if status == "partial":
        return "validation evidence is partial; review findings before broad analysis claims"
    if status == "fail":
        return "validation failed; broad model-data consistency claims are blocked"
    return "validation is blocked"


def _next_actions(findings: list[ContractFinding]) -> list[str]:
    actions: list[str] = []
    for finding in findings:
        if finding.type.startswith("validation_contract"):
            actions.append("fix referenced test-file contracts before model-dataset validation")
        elif finding.type == "direct_validation_audit_failed":
            actions.append("inspect top residuals before enabling or trusting calibration")
        elif finding.type == "physical_envelope_violation":
            actions.append("review sensor mapping, unit, physical envelope, or model boundary")
        elif finding.type == "redundant_sensor_mismatch":
            actions.append("review redundant sensor quality and source selection policy")
        elif finding.type == "calibration_holdout_failed":
            actions.append("do not treat optimizer convergence as validation pass; inspect holdout residuals")
        elif finding.type == "calibration_parameter_at_bound":
            actions.append("review calibration parameter bounds, model structure, and source mapping")
    return sorted(set(actions))


def _resolve_path(base: Path, value: str | None) -> Path:
    if value is None:
        raise ValueError("path value is required")
    path = Path(value)
    return path if path.is_absolute() else base / path


__all__ = ["ModelDatasetValidationReport", "validate_model_dataset"]
