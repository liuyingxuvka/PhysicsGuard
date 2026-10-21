from __future__ import annotations

import hashlib
from pathlib import Path
import shutil

import yaml

from physicsguard.core.model_dataset_validation import validate_model_dataset
from physicsguard.schema.model_dataset_validation import ModelDatasetValidationReportSpec
from physicsguard.schema.validation_depth import ValidationDepthReceiptSpec


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"


def _copy_pump(tmp_path: Path) -> Path:
    target = tmp_path / "pump_loop"
    shutil.copytree(PUMP, target)
    return target


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _clean_plan(pump: Path) -> Path:
    return pump / "validation" / "clean_validation_plan.yaml"


def test_passing_depth_receipt_preserves_exact_pointwise_scope_and_report_identity() -> None:
    report = validate_model_dataset(_clean_plan(PUMP))
    receipt = report.depth_receipt

    assert report.ok
    assert receipt["artifact_kind"] == "physicsguard_validation_depth_receipt"
    assert receipt["status"] == "pass"
    assert receipt["dataset"]["status"] == "current"
    assert {item["identity_id"] for item in receipt["dataset"]["files"]} == {
        "clean_csv",
        "clean_observed_series",
    }
    assert receipt["mapping"]["status"] == "pass"
    assert receipt["time"]["declared_scope"] == "scenario_set"
    assert receipt["time"]["observed_scope"] == "scenario_set"
    assert receipt["time"]["point_count"] == 3
    assert receipt["scenarios"]["perturbation_count"] == 1
    assert receipt["split"]["status"] == "not_applicable"
    assert len(receipt["residual_series"]["points"]) == 3
    assert receipt["residual_series"]["aggregate"]["evaluated_point_count"] == 3
    assert receipt["envelopes"]["aggregate"]["violation_count"] == 0
    assert len(receipt["report_identity"]["report_sha256"]) == 64
    assert "commercial" in receipt["unsafe_claim_boundary"]
    assert ValidationDepthReceiptSpec.model_validate(receipt).ok
    assert ModelDatasetValidationReportSpec.model_validate(report.to_dict()).status == "pass"


def test_changed_dataset_content_makes_receipt_stale(tmp_path: Path) -> None:
    pump = _copy_pump(tmp_path)
    data_file = pump / "data" / "clean.csv"
    data_file.write_text(data_file.read_text(encoding="utf-8") + "0.3,12.0,24.0,true\n", encoding="utf-8")

    report = validate_model_dataset(_clean_plan(pump))

    assert report.status == "fail"
    assert report.depth_receipt["status"] == "blocked"
    assert report.depth_receipt["dataset"]["status"] == "stale"
    assert any(item["type"] == "dataset_identity_stale" for item in report.findings)


def test_changed_field_schema_makes_receipt_stale_even_when_data_is_unchanged(tmp_path: Path) -> None:
    pump = _copy_pump(tmp_path)
    manifest_path = pump / "data" / "clean_manifest.yaml"
    manifest = _load(manifest_path)
    manifest["metadata"]["unexpected_revision"] = "changed_after_receipt"
    _write(manifest_path, manifest)

    report = validate_model_dataset(_clean_plan(pump))

    assert report.status == "fail"
    assert report.depth_receipt["dataset"]["field_schema"]["status"] == "stale"
    assert any(
        item["type"] == "dataset_identity_stale" and item["target"] == "clean_manifest_schema"
        for item in report.findings
    )


def test_uncertain_required_mapping_blocks_broad_validation(tmp_path: Path) -> None:
    pump = _copy_pump(tmp_path)
    edges_path = pump / "coverage" / "pump_loop_mapping_edges.yaml"
    edges = _load(edges_path)
    edge = next(item for item in edges["edges"] if item["target"] == "pump_signal_map.y")
    edge.pop("unit_evidence")
    edge["confidence"] = 0.4
    edge["review_required"] = True
    _write(edges_path, edges)
    plan_path = _clean_plan(pump)

    report = validate_model_dataset(plan_path)
    mapping = report.depth_receipt["mapping"]

    assert report.status == "fail"
    assert mapping["status"] == "blocked"
    assert "pump_signal_map.y" in mapping["unresolved_targets"]
    signal = next(item for item in mapping["signals"] if item["target"] == "pump_signal_map.y")
    assert "unit_evidence_missing" in signal["issue_codes"]
    assert "confidence_below_threshold" in signal["issue_codes"]
    assert "human_review_required" in signal["issue_codes"]
    assert any(item["type"] == "mapping_required_signal_uncertain" for item in report.findings)


def test_single_point_cannot_claim_time_window(tmp_path: Path) -> None:
    pump = _copy_pump(tmp_path)
    series_path = pump / "observed" / "clean_observed_series.yaml"
    series = _load(series_path)
    series["points"] = series["points"][:1]
    _write(series_path, series)
    plan_path = _clean_plan(pump)
    plan = _load(plan_path)
    plan["depth"]["observed_series"]["sha256"] = _sha256(series_path)
    plan["depth"]["time_scope"] = {
        "claim_scope": "time_window",
        "start_time": 0.0,
        "end_time": 0.0,
        "time_unit": "s",
        "expected_point_count": 1,
    }
    plan["depth"]["scenarios"] = plan["depth"]["scenarios"][:1]
    _write(plan_path, plan)

    report = validate_model_dataset(plan_path)

    assert report.status == "fail"
    assert report.depth_receipt["time"]["observed_scope"] == "snapshot"
    assert report.depth_receipt["time"]["snapshot_only"] is True
    assert any(item["type"] == "snapshot_scope_overclaim" for item in report.findings)


def test_identical_content_under_different_holdout_label_is_overlap(tmp_path: Path) -> None:
    pump = _copy_pump(tmp_path)
    train = pump / "observed" / "calibration_train.yaml"
    holdout_clone = pump / "observed" / "renamed_holdout.yaml"
    shutil.copyfile(train, holdout_clone)
    plan_path = pump / "validation" / "calibration_validation_plan.yaml"
    plan = _load(plan_path)
    plan["calibration"]["holdout_observed"] = "../observed/renamed_holdout.yaml"
    plan["depth"] = _load(_clean_plan(pump))["depth"]
    digest = _sha256(train)
    plan["depth"]["split"] = {
        "training": [
            {
                "identity_id": "calibration_training",
                "path": "../observed/calibration_train.yaml",
                "sha256": digest,
                "case_ids": ["training_case"],
            }
        ],
        "holdout": [
            {
                "identity_id": "renamed_holdout",
                "path": "../observed/renamed_holdout.yaml",
                "sha256": digest,
                "case_ids": ["holdout_case"],
            }
        ],
    }
    _write(plan_path, plan)

    report = validate_model_dataset(plan_path)
    split = report.depth_receipt["split"]

    assert report.status == "fail"
    assert split["status"] == "blocked"
    assert split["overlapping_paths"] == []
    assert split["overlapping_hashes"] == [digest]
    assert any(item["type"] == "calibration_holdout_identity_overlap" for item in report.findings)


def test_short_hard_envelope_violation_cannot_hide_behind_series_aggregate(tmp_path: Path) -> None:
    pump = _copy_pump(tmp_path)
    series_path = pump / "observed" / "clean_observed_series.yaml"
    series = _load(series_path)
    series["points"][1]["variables"]["pump_signal_map.y"]["value"] = 301.0
    _write(series_path, series)
    plan_path = _clean_plan(pump)
    plan = _load(plan_path)
    plan["depth"]["observed_series"]["sha256"] = _sha256(series_path)
    envelope = next(item for item in plan["physical_envelopes"] if item["target"] == "pump_signal_map.y")
    envelope["severity"] = "error"
    _write(plan_path, plan)

    report = validate_model_dataset(plan_path)
    receipt = report.depth_receipt

    assert report.status == "fail"
    assert receipt["envelopes"]["status"] == "blocked"
    assert receipt["envelopes"]["aggregate"]["hard_violation_count"] == 1
    assert receipt["envelopes"]["violations"][0]["point_id"] == "speed_ramp_t1"
    assert receipt["residual_series"]["audit_pass"] is False
    assert receipt["envelopes"]["violation_intervals"]
    assert any(item["type"] == "physical_envelope_interval_violation" for item in report.findings)


def test_invalid_series_interval_is_preserved_and_blocks_depth(tmp_path: Path) -> None:
    pump = _copy_pump(tmp_path)
    series_path = pump / "observed" / "clean_observed_series.yaml"
    series = _load(series_path)
    series["points"][1]["valid"] = False
    series["points"][1]["invalid_reason"] = "sensor export gap"
    series["points"][1]["variables"] = {}
    _write(series_path, series)
    plan_path = _clean_plan(pump)
    plan = _load(plan_path)
    plan["depth"]["observed_series"]["sha256"] = _sha256(series_path)
    _write(plan_path, plan)

    report = validate_model_dataset(plan_path)
    residual = report.depth_receipt["residual_series"]

    assert report.status == "fail"
    assert residual["status"] == "blocked"
    assert residual["aggregate"]["invalid_point_count"] == 1
    assert residual["invalid_intervals"][0]["reason"] == "sensor export gap"
