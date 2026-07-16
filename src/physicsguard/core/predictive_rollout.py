"""Native comparison of externally produced stateful future trajectories."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Any

from physicsguard.io.observation_loader import load_observed_series
from physicsguard.schema.predictive_rollout import (
    ModelSemantics,
    PredictiveRolloutPlanSpec,
    PredictiveRolloutReceiptSpec,
    RolloutArtifactIdentitySpec,
)
from physicsguard.schema.validation_depth import ObservedSeriesSpec


@dataclass(frozen=True)
class PredictiveRolloutEvaluation:
    receipt: dict[str, Any]
    findings: list[dict[str, Any]]


def evaluate_predictive_rollout(
    model_semantics: ModelSemantics,
    rollout: PredictiveRolloutPlanSpec | None,
    *,
    base_dir: Path,
) -> PredictiveRolloutEvaluation:
    """Validate exact identity, future alignment, and trajectory metrics."""

    if rollout is None:
        status = "not_authorized" if model_semantics == "pointwise" else "not_declared"
        return PredictiveRolloutEvaluation(
            receipt=_empty_receipt(model_semantics, status),
            findings=[],
        )
    if model_semantics != "stateful_dynamic":
        finding = _finding(
            "error",
            "pointwise_prediction_forbidden",
            "pointwise residual evidence cannot authorize trajectory prediction",
        )
        return PredictiveRolloutEvaluation(
            receipt=_empty_receipt(model_semantics, "blocked", [finding["type"]]),
            findings=[finding],
        )

    findings: list[dict[str, Any]] = []
    model_identity = _identity_receipt(rollout.model_identity, base_dir)
    training = [_identity_receipt(item, base_dir) for item in rollout.training]
    prediction_identity = _identity_receipt(rollout.prediction_series, base_dir)
    holdout_identity = _identity_receipt(rollout.future_holdout_series, base_dir)
    identities = [model_identity, *training, prediction_identity, holdout_identity]
    if any(item["status"] != "current" for item in identities):
        findings.append(_finding("error", "predictive_identity_stale", "one or more predictive artifacts are missing or stale"))

    train_paths = {_normalized_path(base_dir, item.path) for item in rollout.training}
    train_hashes = {item.sha256 for item in rollout.training}
    train_cases = {case for item in rollout.training for case in item.case_ids}
    holdout_path = _normalized_path(base_dir, rollout.future_holdout_series.path)
    overlap_paths = sorted(train_paths & {holdout_path})
    overlap_hashes = sorted(train_hashes & {rollout.future_holdout_series.sha256})
    overlap_cases = sorted(train_cases & set(rollout.future_holdout_series.case_ids))
    if overlap_paths or overlap_hashes or overlap_cases:
        findings.append(
            _finding(
                "error",
                "predictive_training_future_overlap",
                "training and future holdout overlap by path, content hash, or case id",
                details={
                    "paths": overlap_paths,
                    "hashes": overlap_hashes,
                    "case_ids": overlap_cases,
                },
            )
        )

    predicted = _load_series(rollout.prediction_series, base_dir, findings, "prediction_series_unreadable")
    holdout = _load_series(rollout.future_holdout_series, base_dir, findings, "future_holdout_series_unreadable")
    metrics, alignment_gaps, metric_findings = evaluate_predictive_rollout_artifacts(
        rollout,
        predicted,
        holdout,
    )
    findings.extend(metric_findings)
    status = "blocked" if any(item["severity"] == "error" for item in findings) else "pass"
    receipt = {
        "artifact_kind": "physicsguard_predictive_rollout_receipt",
        "receipt_version": "1.0",
        "status": status,
        "model_semantics": model_semantics,
        "rollout_id": rollout.rollout_id,
        "producer_receipt_id": rollout.producer_receipt_id,
        "model_identity": model_identity,
        "training": training,
        "prediction_series": prediction_identity,
        "future_holdout_series": holdout_identity,
        "overlapping_paths": overlap_paths,
        "overlapping_hashes": overlap_hashes,
        "overlapping_case_ids": overlap_cases,
        "alignment_gaps": alignment_gaps,
        "metrics": metrics,
        "finding_codes": sorted({item["type"] for item in findings}),
        "covered_horizon": {
            "training_end_time": rollout.training_end_time,
            "step_size": rollout.step_size,
            "step_unit": rollout.step_unit,
            "horizon_steps": rollout.horizon_steps,
            "target_signals": list(rollout.target_signals),
            "initial_state": dict(rollout.initial_state),
            "threshold_source": rollout.threshold_source,
        },
        "claim_boundary": (
            "prediction is authorized only for the exact model, producer receipt, initial state, "
            "step, future holdout, targets, horizon, scales, and thresholds in this receipt"
        ),
    }
    validated = PredictiveRolloutReceiptSpec.model_validate(receipt).model_dump(mode="json")
    return PredictiveRolloutEvaluation(receipt=validated, findings=findings)


def evaluate_predictive_rollout_artifacts(
    rollout: PredictiveRolloutPlanSpec,
    predicted: ObservedSeriesSpec | None,
    holdout: ObservedSeriesSpec | None,
) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    """Compare already loaded trajectory artifacts; no model state is mutated."""

    findings: list[dict[str, Any]] = []
    gaps: list[str] = []
    if predicted is None or holdout is None:
        gaps.append("trajectory_missing")
        return _empty_metrics(), gaps, findings
    pred_points = [item for item in predicted.points if item.valid]
    hold_points = [item for item in holdout.points if item.valid]
    if len(pred_points) != rollout.horizon_steps or len(hold_points) != rollout.horizon_steps:
        gaps.append("horizon_step_count_mismatch")
    if predicted.time_unit != rollout.step_unit or holdout.time_unit != rollout.step_unit:
        gaps.append("step_unit_mismatch")
    pred_times = [item.timestamp for item in pred_points]
    hold_times = [item.timestamp for item in hold_points]
    if any(value is None for value in [*pred_times, *hold_times]):
        gaps.append("timestamp_missing")
    elif pred_times != hold_times:
        gaps.append("timestamp_alignment_mismatch")
    if hold_times and hold_times[0] is not None and hold_times[0] <= rollout.training_end_time:
        gaps.append("holdout_not_strictly_future")
    if hold_times and all(value is not None for value in hold_times):
        gaps.extend(_step_alignment_gaps([float(value) for value in hold_times], rollout.step_size))
    for target in rollout.target_signals:
        if any(target not in point.variables for point in pred_points):
            gaps.append(f"prediction_target_missing:{target}")
        if any(target not in point.variables for point in hold_points):
            gaps.append(f"holdout_target_missing:{target}")
        if not any(target not in point.variables for point in [*pred_points, *hold_points]):
            pred_units = {point.variables[target].unit for point in pred_points}
            hold_units = {point.variables[target].unit for point in hold_points}
            if len(pred_units) != 1 or pred_units != hold_units:
                gaps.append(f"target_unit_mismatch:{target}")
    if gaps:
        findings.append(_finding("error", "predictive_alignment_failed", "prediction and future holdout are not exactly aligned", details={"gaps": sorted(set(gaps))}))
        return _empty_metrics(), sorted(set(gaps)), findings

    step_errors: list[float] = []
    signal_errors: dict[str, list[float]] = {target: [] for target in rollout.target_signals}
    for pred, obs in zip(pred_points, hold_points):
        current = []
        for target in rollout.target_signals:
            error = (pred.variables[target].value - obs.variables[target].value) / rollout.signal_scales[target]
            signal_errors[target].append(float(error))
            current.append(abs(float(error)))
        step_errors.append(max(current))
    worst = max(step_errors)
    accumulated = sum(step_errors)
    drift = max(abs(values[-1] - values[0]) for values in signal_errors.values())
    growth = max(0.0, step_errors[-1] - step_errors[0])
    lag = max(
        (_best_lag_steps(pred_points, hold_points, target, rollout.thresholds.maximum_absolute_lag_steps + 3) for target in rollout.target_signals),
        key=abs,
    )
    phase = abs(lag) * rollout.step_size
    thresholds = rollout.thresholds
    threshold_results = {
        "worst_step": worst <= thresholds.maximum_worst_step_normalized_error,
        "accumulated_error": accumulated <= thresholds.maximum_accumulated_normalized_error,
        "lag": abs(lag) <= thresholds.maximum_absolute_lag_steps,
        "phase": phase <= thresholds.maximum_phase_error,
        "drift": drift <= thresholds.maximum_drift,
        "error_growth": growth <= thresholds.maximum_error_growth,
    }
    stability = all(math.isfinite(value) for value in step_errors) and threshold_results["error_growth"] and threshold_results["drift"]
    threshold_results["stability"] = stability
    for name, passed in threshold_results.items():
        if not passed:
            findings.append(_finding("error", f"predictive_{name}_threshold_failed", "predictive rollout metric exceeds its declared threshold"))
    metrics = {
        "aligned_step_count": len(step_errors),
        "worst_step_normalized_error": worst,
        "accumulated_normalized_error": accumulated,
        "lag_steps": lag,
        "phase_error": phase,
        "drift": drift,
        "error_growth": growth,
        "stability_pass": stability,
        "threshold_results": threshold_results,
    }
    return metrics, [], findings


def _best_lag_steps(predicted, holdout, target: str, max_shift: int) -> int:
    pred_values = [item.variables[target].value for item in predicted]
    hold_values = [item.variables[target].value for item in holdout]
    best_shift = 0
    best_error = math.inf
    limit = min(max_shift, max(0, len(pred_values) - 2))
    for shift in range(-limit, limit + 1):
        if shift < 0:
            left = pred_values[-shift:]
            right = hold_values[: len(left)]
        elif shift > 0:
            left = pred_values[:-shift]
            right = hold_values[shift:]
        else:
            left = pred_values
            right = hold_values
        if len(left) < 2:
            continue
        error = sum((a - b) ** 2 for a, b in zip(left, right)) / len(left)
        if error < best_error:
            best_error = error
            best_shift = shift
    return best_shift


def _step_alignment_gaps(times: list[float], step_size: float) -> list[str]:
    if len(times) < 2:
        return ["horizon_too_short"]
    if any(right <= left for left, right in zip(times, times[1:])):
        return ["timestamps_not_strictly_increasing"]
    if any(not math.isclose(right - left, step_size, rel_tol=1e-9, abs_tol=1e-12) for left, right in zip(times, times[1:])):
        return ["step_size_mismatch"]
    return []


def _identity_receipt(reference: RolloutArtifactIdentitySpec, base_dir: Path) -> dict[str, Any]:
    path = _resolve_path(base_dir, reference.path)
    actual = _sha256(path) if path.exists() and path.is_file() else None
    return {
        "identity_id": reference.identity_id,
        "path": reference.path,
        "expected_sha256": reference.sha256,
        "actual_sha256": actual,
        "status": "missing" if actual is None else "current" if actual == reference.sha256 else "stale",
        "case_ids": list(reference.case_ids),
    }


def _load_series(reference, base_dir, findings, code):
    try:
        return load_observed_series(_resolve_path(base_dir, reference.path))
    except Exception as exc:
        findings.append(_finding("error", code, "predictive series could not be loaded", reference.path, {"error": str(exc)}))
        return None


def _empty_receipt(model_semantics: ModelSemantics, status: str, codes=None) -> dict[str, Any]:
    return PredictiveRolloutReceiptSpec.model_validate(
        {
            "artifact_kind": "physicsguard_predictive_rollout_receipt",
            "status": status,
            "model_semantics": model_semantics,
            "metrics": _empty_metrics(),
            "finding_codes": codes or [],
            "claim_boundary": "no predictive trajectory is authorized by this receipt",
        }
    ).model_dump(mode="json")


def _empty_metrics() -> dict[str, Any]:
    return {
        "aligned_step_count": 0,
        "worst_step_normalized_error": None,
        "accumulated_normalized_error": None,
        "lag_steps": None,
        "phase_error": None,
        "drift": None,
        "error_growth": None,
        "stability_pass": False,
        "threshold_results": {},
    }


def _finding(severity, code, message, target=None, details=None):
    return {"severity": severity, "type": code, "message": message, "target": target, "details": details or {}}


def _resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def _normalized_path(base_dir: Path, value: str) -> str:
    return str(_resolve_path(base_dir, value).resolve()).casefold()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "PredictiveRolloutEvaluation",
    "evaluate_predictive_rollout",
    "evaluate_predictive_rollout_artifacts",
]
