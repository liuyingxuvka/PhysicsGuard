from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from physicsguard.core.model_dataset_validation import validate_model_dataset
from physicsguard.schema.model_dataset_validation import CalibrationPlanSpec, ModelDatasetValidationReportSpec


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"


def test_clean_model_dataset_validation_passes() -> None:
    report = validate_model_dataset(PUMP / "validation" / "clean_validation_plan.yaml")

    assert report.ok
    assert report.status == "pass"
    assert report.direct_validation["audit_pass"]
    assert report.confidence_updates
    assert ModelDatasetValidationReportSpec.model_validate(report.to_dict()).status == "pass"


def test_conservative_calibration_does_not_turn_direct_failure_into_pass() -> None:
    report = validate_model_dataset(PUMP / "validation" / "calibration_validation_plan.yaml")

    assert not report.ok
    assert report.status == "partial"
    assert report.calibration["optimization_success"] is True
    assert report.calibration["holdout_audit_pass"] is True
    assert any(finding["type"] == "direct_validation_audit_failed" for finding in report.findings)


def test_enabled_calibration_requires_bounded_parameters() -> None:
    data = yaml.safe_load((PUMP / "validation" / "calibration_validation_plan.yaml").read_text(encoding="utf-8"))
    del data["calibration"]["parameters"][0]["upper"]

    with pytest.raises(ValueError):
        CalibrationPlanSpec.model_validate(data["calibration"])


def test_coarse_grid_calibration_method_runs_with_same_claim_boundary(tmp_path: Path) -> None:
    data = yaml.safe_load((PUMP / "validation" / "calibration_validation_plan.yaml").read_text(encoding="utf-8"))
    data["audit_file"] = str(PUMP / "model" / "pump_loop_hierarchy.yaml")
    data["observed_file"] = str(PUMP / "observed" / "calibration_train.yaml")
    data["contracts"][0]["contract"] = str(PUMP / "contracts" / "clean_contract.yaml")
    data["calibration"]["method"] = "coarse_grid_then_least_squares"
    data["calibration"]["train_observed"] = str(PUMP / "observed" / "calibration_train.yaml")
    data["calibration"]["holdout_observed"] = str(PUMP / "observed" / "calibration_holdout.yaml")
    plan = tmp_path / "coarse_validation_plan.yaml"
    plan.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    report = validate_model_dataset(plan)

    assert report.status == "partial"
    assert report.calibration["method"] == "coarse_grid_then_least_squares"
    assert report.calibration["optimization_success"] is True


def test_calibration_parameter_must_exist_in_model(tmp_path: Path) -> None:
    data = yaml.safe_load((PUMP / "validation" / "calibration_validation_plan.yaml").read_text(encoding="utf-8"))
    data["audit_file"] = str(PUMP / "model" / "pump_loop_hierarchy.yaml")
    data["observed_file"] = str(PUMP / "observed" / "calibration_train.yaml")
    data["contracts"][0]["contract"] = str(PUMP / "contracts" / "clean_contract.yaml")
    data["calibration"]["train_observed"] = str(PUMP / "observed" / "calibration_train.yaml")
    data["calibration"]["holdout_observed"] = str(PUMP / "observed" / "calibration_holdout.yaml")
    data["calibration"]["parameters"][0]["name"] = "pump_signal_map.missing_slope"
    plan = tmp_path / "bad_parameter_validation_plan.yaml"
    plan.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="calibration parameters not found"):
        validate_model_dataset(plan)
