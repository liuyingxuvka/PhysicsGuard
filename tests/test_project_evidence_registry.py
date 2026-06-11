from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from physicsguard.core.model_dataset_validation import validate_model_dataset
from physicsguard.core.project_evidence import (
    build_project_evidence_map,
    check_evidence_bundle,
    check_evidence_gaps,
    check_project_evidence_registry,
    scan_project_evidence_candidates,
)
from physicsguard.schema.project_evidence import (
    BindingExpectationSpec,
    EvidenceGapReportSpec,
    ProjectEvidenceMapReportSpec,
)


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"
REGISTRY = PUMP / "evidence" / "project_evidence_registry.yaml"


def test_project_evidence_registry_gap_bundle_and_map_pass() -> None:
    registry_review = check_project_evidence_registry(REGISTRY)
    gap_report = check_evidence_gaps(REGISTRY)
    bundle_report = check_evidence_bundle(REGISTRY, "pump_loop_validation_bundle_001")
    project_map = build_project_evidence_map(REGISTRY)

    assert registry_review.ok
    assert gap_report.ok
    assert bundle_report.ok
    assert project_map.ok
    assert project_map.coverage_summary["unresolved_binding_gap_count"] == 0
    assert project_map.coverage_summary["exempt_binding_expectation_count"] == 1
    assert project_map.project_profile["project_name"] == "Pump loop fixture project"
    assert project_map.project_profile["source_count"] >= 1
    assert "pump_signal_map.x" in project_map.coverage_summary["tested_model_targets"]
    assert ProjectEvidenceMapReportSpec.model_validate(project_map.to_dict()).status == "pass"
    assert EvidenceGapReportSpec.model_validate(gap_report.to_dict()).status == "pass"


def test_project_evidence_scan_marks_registered_candidates(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    data_file = data_dir / "run.csv"
    data_file.write_text("time_s,x\n0.0,1.0\n", encoding="utf-8")
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        yaml.safe_dump(
            {
                "registry_id": "scan_fixture",
                "project_profile": {
                    "project_name_unknown_reason": "not needed for scanner fixture",
                    "run_period": {"unknown_reason": "not needed for scanner fixture"},
                    "location_unknown_reason": "not needed for scanner fixture",
                },
                "artifacts": [
                    {
                        "artifact_id": "run_csv",
                        "artifact_kind": "raw_test_data",
                        "path": "data/run.csv",
                        "registered_at": "2026-06-11",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    report = scan_project_evidence_candidates(data_dir, registry)

    assert report.ok
    assert report.summary["candidate_count"] == 1
    assert report.candidates[0]["registered"] is True
    assert report.candidates[0]["matched_artifact_id"] == "run_csv"


def test_binding_expectation_missing_reports_blocking_gap(tmp_path: Path) -> None:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    data["evidence_bindings"] = [
        item for item in data["evidence_bindings"] if item["binding_id"] != "clean_flow_readback_to_model_y"
    ]
    data["evidence_bundles"][0]["bindings"] = [
        item for item in data["evidence_bundles"][0]["bindings"] if item != "clean_flow_readback_to_model_y"
    ]
    registry = tmp_path / "missing_flow_binding.yaml"
    registry.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    report = check_evidence_gaps(registry, bundle_id="pump_loop_validation_bundle_001")

    assert not report.ok
    assert any(gap["gap_type"] == "binding_expectation_unmet" for gap in report.blocking_gaps)
    assert any(gap["target"] == "field:flow_readback_kg_s" for gap in report.blocking_gaps)


def test_project_profile_missing_basic_info_reports_review_gaps(tmp_path: Path) -> None:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    data["project_profile"] = {
        "project_name_unknown_reason": "not found in available fixture sources",
        "run_period": {"unknown_reason": "test period not found yet"},
        "location_unknown_reason": "test location not found yet",
    }
    registry = tmp_path / "missing_project_profile.yaml"
    registry.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    report = check_evidence_gaps(registry)

    assert not report.ok
    gap_types = {gap["gap_type"] for gap in report.review_gaps}
    assert "project_profile_project_name_unknown" in gap_types
    assert "project_profile_run_period_unknown" in gap_types
    assert "project_profile_location_unknown" in gap_types


def test_physical_parameter_without_binding_or_exemption_reports_review_gap(tmp_path: Path) -> None:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    data["evidence_bindings"] = [
        item for item in data["evidence_bindings"] if item["binding_id"] != "slope_fact_to_model_parameter"
    ]
    data["binding_expectations"] = [
        item for item in data["binding_expectations"] if item["expectation_id"] != "expect_slope_fact_bound"
    ]
    data["evidence_bundles"][0]["bindings"] = [
        item for item in data["evidence_bundles"][0]["bindings"] if item != "slope_fact_to_model_parameter"
    ]
    for fact in data["facts"]:
        if fact["fact_id"] == "pump_signal_map.a":
            fact.pop("bindings", None)
    registry = tmp_path / "unreviewed_physical_parameter.yaml"
    registry.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    report = check_evidence_gaps(registry)

    assert not report.ok
    assert any(gap["gap_type"] == "physical_parameter_binding_unreviewed" for gap in report.review_gaps)


def test_exempt_binding_expectation_requires_reason() -> None:
    with pytest.raises(ValueError, match="exemption_reason"):
        BindingExpectationSpec.model_validate(
            {
                "expectation_id": "bad_exemption",
                "subject_kind": "test_field",
                "subject_id": "field:serial_number",
                "policy": "exempt",
            }
        )


def test_blocking_evidence_gap_prevents_validation_pass(tmp_path: Path) -> None:
    registry_data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    registry_data["evidence_bindings"] = [
        item for item in registry_data["evidence_bindings"] if item["binding_id"] != "clean_flow_readback_to_model_y"
    ]
    registry_data["evidence_bundles"][0]["bindings"] = [
        item for item in registry_data["evidence_bundles"][0]["bindings"] if item != "clean_flow_readback_to_model_y"
    ]
    registry = tmp_path / "missing_validation_binding.yaml"
    registry.write_text(yaml.safe_dump(registry_data, sort_keys=False), encoding="utf-8")

    plan_data = yaml.safe_load((PUMP / "validation" / "clean_validation_plan.yaml").read_text(encoding="utf-8"))
    plan_data["audit_file"] = str(PUMP / "model" / "pump_loop_hierarchy.yaml")
    plan_data["observed_file"] = str(PUMP / "observed" / "clean_observed.yaml")
    plan_data["evidence_registry"] = str(registry)
    plan_data["contracts"][0]["contract"] = str(PUMP / "contracts" / "clean_contract.yaml")
    plan = tmp_path / "validation_with_missing_binding.yaml"
    plan.write_text(yaml.safe_dump(plan_data, sort_keys=False), encoding="utf-8")

    report = validate_model_dataset(plan)

    assert not report.ok
    assert report.status == "fail"
    assert any(finding["type"] == "validation_blocking_evidence_gap" for finding in report.findings)
