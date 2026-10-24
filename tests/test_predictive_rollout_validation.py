from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from physicsguard.core.model_dataset_validation import validate_model_dataset
from physicsguard.core.predictive_rollout import (
    evaluate_predictive_rollout,
    evaluate_predictive_rollout_artifacts,
)
from physicsguard.io.observation_loader import load_observed_series
from physicsguard.schema.predictive_rollout import PredictiveRolloutPlanSpec


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"


def _ref(identity_id: str, relative: str, case_ids=()):
    return {
        "identity_id": identity_id,
        "path": relative,
        "case_ids": list(case_ids),
    }


def _plan() -> PredictiveRolloutPlanSpec:
    return PredictiveRolloutPlanSpec.model_validate(
        {
            "rollout_id": "pump_loop_future_rollout_v1",
            "producer_id": "fixture-stateful-producer-result-v1",
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
    assert result.result["status"] == "pass"
    assert "producer identity" in result.result["claim_boundary"]
    assert result.result["metrics"] == {
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
    assert result.result["status"] == "blocked"
    assert "pointwise_prediction_forbidden" in result.result["finding_codes"]


def test_training_future_identity_overlap_is_blocked() -> None:
    plan = _plan()
    overlap = plan.model_copy(update={"future_holdout_series": plan.training[0]})
    result = evaluate_predictive_rollout("stateful_dynamic", overlap, base_dir=PUMP)
    assert result.result["status"] == "blocked"
    assert result.result["overlapping_paths"]
    assert result.result["overlapping_contents"] == ["training_series"]
    assert result.result["overlapping_case_ids"]


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


def test_same_stat_training_rewrite_is_rejected_as_content_overlap(tmp_path: Path) -> None:
    import os

    plan = _plan()
    holdout = PUMP / plan.future_holdout_series.path
    content = holdout.read_bytes()
    training = tmp_path / "independent_training.yaml"
    training.write_bytes(bytes([content[0] ^ 1]) + content[1:])
    stat = training.stat()
    plan = plan.model_copy(update={
        "training": [plan.training[0].model_copy(update={"path": str(training)})],
    })
    separate = evaluate_predictive_rollout("stateful_dynamic", plan, base_dir=PUMP)
    assert separate.result["status"] == "pass"
    assert separate.result["overlapping_contents"] == []
    assert "predictive_training_future_overlap" not in separate.result["finding_codes"]

    training.write_bytes(content)
    os.utime(training, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert (training.stat().st_size, training.stat().st_mtime_ns) == (stat.st_size, stat.st_mtime_ns)
    overlap = evaluate_predictive_rollout("stateful_dynamic", plan, base_dir=PUMP)
    assert overlap.result["overlapping_paths"] == []
    assert overlap.result["overlapping_case_ids"] == []
    assert overlap.result["overlapping_contents"] == ["training_series"]
    assert "predictive_training_future_overlap" in overlap.result["finding_codes"]
    assert overlap.result["status"] == "blocked"


def test_rollout_plan_without_producer_id_still_passes() -> None:
    payload = _plan().model_dump(mode="json")
    del payload["producer_id"]
    plan = PredictiveRolloutPlanSpec.model_validate(payload)
    result = evaluate_predictive_rollout("stateful_dynamic", plan, base_dir=PUMP)
    assert result.result["status"] == "pass"
    assert result.result["producer_id"] is None
    assert "producer identity" not in result.result["claim_boundary"]


def test_legacy_producer_identifier_requires_the_current_name():
    payload = _plan().model_dump(mode='json')
    payload['producer_receipt_id'] = payload.pop('producer_id')
    with pytest.raises(ValueError, match='producer_id'):
        PredictiveRolloutPlanSpec.model_validate(payload)


def test_native_results_have_no_output_version():
    result = evaluate_predictive_rollout('stateful_dynamic', _plan(), base_dir=PUMP).result
    assert result['artifact_kind'] == 'physicsguard_predictive_rollout_result'
    assert 'output_version' not in result
