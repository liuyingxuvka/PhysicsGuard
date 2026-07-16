from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from physicsguard.core.model_dataset_validation import validate_model_dataset
from physicsguard.core.project_closure import _consume_validation_depth_receipt
from physicsguard.core.predictive_rollout import (
    evaluate_predictive_rollout,
    evaluate_predictive_rollout_artifacts,
)
from physicsguard.io.observation_loader import load_observed_series
from physicsguard.schema.predictive_rollout import PredictiveRolloutPlanSpec


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref(identity_id: str, relative: str, case_ids=()):
    path = PUMP / relative
    return {
        "identity_id": identity_id,
        "path": relative,
        "sha256": _sha(path),
        "case_ids": list(case_ids),
    }


def _plan() -> PredictiveRolloutPlanSpec:
    return PredictiveRolloutPlanSpec.model_validate(
        {
            "rollout_id": "pump_loop_future_rollout_v1",
            "producer_receipt_id": "fixture-stateful-producer-receipt-v1",
            "model_identity": _ref("pump_model", "model/pump_loop_hierarchy.yaml"),
            "training": [
                _ref(
                    "training_series",
                    "observed/clean_observed_series.yaml",
                    ["baseline_case", "speed_ramp_case_01", "speed_ramp_case_02"],
                )
            ],
            "prediction_series": _ref("prediction", "observed/predicted_future_series.yaml"),
            "future_holdout_series": _ref(
                "future_holdout",
                "observed/future_holdout_series.yaml",
                ["future_case_1", "future_case_2", "future_case_3"],
            ),
            "training_end_time": 0.2,
            "initial_state": {"pump_signal_map.x": 11.0, "pump_signal_map.y": 22.0},
            "step_size": 1.0,
            "step_unit": "s",
            "horizon_steps": 3,
            "target_signals": ["pump_signal_map.x", "pump_signal_map.y"],
            "signal_scales": {"pump_signal_map.x": 1.0, "pump_signal_map.y": 2.0},
            "threshold_source": "pump_loop_predictive_fixture_thresholds_v1",
            "thresholds": {
                "maximum_worst_step_normalized_error": 0.0,
                "maximum_accumulated_normalized_error": 0.0,
                "maximum_absolute_lag_steps": 0,
                "maximum_phase_error": 0.0,
                "maximum_drift": 0.0,
                "maximum_error_growth": 0.0,
            },
        }
    )


def test_passing_future_holdout_rollout_has_all_metrics() -> None:
    result = evaluate_predictive_rollout("stateful_dynamic", _plan(), base_dir=PUMP)
    assert result.receipt["status"] == "pass"
    assert result.receipt["metrics"] == {
        "aligned_step_count": 3,
        "worst_step_normalized_error": 0.0,
        "accumulated_normalized_error": 0.0,
        "lag_steps": 0,
        "phase_error": 0.0,
        "drift": 0.0,
        "error_growth": 0.0,
        "stability_pass": True,
        "threshold_results": {
            "worst_step": True,
            "accumulated_error": True,
            "lag": True,
            "phase": True,
            "drift": True,
            "error_growth": True,
            "stability": True,
        },
    }


def test_pointwise_prediction_is_forbidden() -> None:
    result = evaluate_predictive_rollout("pointwise", _plan(), base_dir=PUMP)
    assert result.receipt["status"] == "blocked"
    assert "pointwise_prediction_forbidden" in result.receipt["finding_codes"]


def test_training_future_identity_overlap_is_blocked() -> None:
    plan = _plan()
    overlap = plan.model_copy(update={"future_holdout_series": plan.training[0]})
    result = evaluate_predictive_rollout("stateful_dynamic", overlap, base_dir=PUMP)
    assert result.receipt["status"] == "blocked"
    assert result.receipt["overlapping_paths"]
    assert result.receipt["overlapping_hashes"]
    assert result.receipt["overlapping_case_ids"]


def test_timestamp_alignment_failure_is_blocked() -> None:
    plan = _plan()
    predicted = load_observed_series(PUMP / "observed" / "predicted_future_series.yaml")
    holdout = load_observed_series(PUMP / "observed" / "future_holdout_series.yaml")
    shifted = holdout.model_copy(
        update={
            "points": [
                point.model_copy(update={"timestamp": point.timestamp + 0.1})
                for point in holdout.points
            ]
        }
    )
    _, gaps, findings = evaluate_predictive_rollout_artifacts(plan, predicted, shifted)
    assert "timestamp_alignment_mismatch" in gaps
    assert any(item["type"] == "predictive_alignment_failed" for item in findings)


def test_drift_and_stability_fail_even_when_early_steps_are_good() -> None:
    plan = _plan().model_copy(
        update={
            "thresholds": _plan().thresholds.model_copy(
                update={
                    "maximum_worst_step_normalized_error": 10.0,
                    "maximum_accumulated_normalized_error": 10.0,
                }
            )
        }
    )
    predicted = load_observed_series(PUMP / "observed" / "predicted_future_series.yaml")
    holdout = load_observed_series(PUMP / "observed" / "future_holdout_series.yaml")
    last = predicted.points[-1]
    variables = dict(last.variables)
    variables["pump_signal_map.y"] = variables["pump_signal_map.y"].model_copy(update={"value": 38.0})
    drifting = predicted.model_copy(
        update={"points": [*predicted.points[:-1], last.model_copy(update={"variables": variables})]}
    )
    metrics, gaps, findings = evaluate_predictive_rollout_artifacts(plan, drifting, holdout)
    assert gaps == []
    assert metrics["drift"] > 0
    assert metrics["stability_pass"] is False
    codes = {item["type"] for item in findings}
    assert "predictive_drift_threshold_failed" in codes
    assert "predictive_stability_threshold_failed" in codes


def test_stateful_prediction_receipt_integrates_with_prediction_ready_closure(tmp_path: Path) -> None:
    source_plan = PUMP / "validation" / "clean_validation_plan.yaml"
    data = yaml.safe_load(source_plan.read_text(encoding="utf-8"))
    source_base = source_plan.parent

    def absolute(value: str) -> str:
        path = Path(value)
        return str(path if path.is_absolute() else (source_base / path).resolve())

    data["evidence_registry"] = absolute(data["evidence_registry"])
    data["audit_file"] = absolute(data["audit_file"])
    data["observed_file"] = absolute(data["observed_file"])
    for item in data["contracts"]:
        item["contract"] = absolute(item["contract"])
    depth = data["depth"]
    for item in depth["dataset"]["files"]:
        item["path"] = absolute(item["path"])
    for key in ("field_schema", "parameter_roles", "testbench"):
        depth["dataset"][key]["path"] = absolute(depth["dataset"][key]["path"])
    depth["mapping_review"]["registry"]["path"] = absolute(depth["mapping_review"]["registry"]["path"])
    depth["observed_series"]["path"] = absolute(depth["observed_series"]["path"])
    rollout = _plan().model_dump(mode="json")
    for key in ("model_identity", "prediction_series", "future_holdout_series"):
        rollout[key]["path"] = str((PUMP / rollout[key]["path"]).resolve())
    for item in rollout["training"]:
        item["path"] = str((PUMP / item["path"]).resolve())
    depth["model_semantics"] = "stateful_dynamic"
    depth["predictive_rollout"] = rollout
    plan_path = tmp_path / "stateful_validation_plan.yaml"
    plan_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    report = validate_model_dataset(plan_path)
    assert report.ok
    assert report.depth_receipt["model_semantics"] == "stateful_dynamic"
    assert report.depth_receipt["predictive"]["status"] == "pass"

    checked, findings = [], []
    _consume_validation_depth_receipt(
        plan_path,
        report.to_dict(),
        checked,
        findings,
        requested_claim_scope="prediction_ready",
    )
    assert findings == []
