from __future__ import annotations

from pathlib import Path

import yaml

from physicsguard.core.project_closure import run_project_closure
from physicsguard.schema.project_closure import ProjectClosureReportSpec


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"
REGISTRY = PUMP / "evidence" / "project_evidence_registry.yaml"


def _write_plan(tmp_path: Path, **overrides) -> Path:
    data = {
        "closure_id": "closure_fixture",
        "claim_scope": "project_ready",
        "project_root": str(ROOT),
        "evidence_registry": str(REGISTRY),
        "evidence_bundle_ids": ["pump_loop_validation_bundle_001"],
        "test_contracts": [],
        "validation_plans": [],
        "model_library_indexes": [],
        "audit_pairs": [],
        "required_checks": {
            "project_audit": True,
            "evidence_check": True,
            "evidence_gap_check": True,
            "evidence_map": True,
            "test_contracts": False,
            "validation": False,
            "model_library": False,
            "hierarchy_closure": False,
        },
        "allow_review_gaps": True,
        "allow_optional_gaps": True,
        "allow_skipped_required_checks": False,
    }
    data.update(overrides)
    plan = tmp_path / "project_closure_plan.yaml"
    plan.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return plan


def test_clean_project_closure_passes() -> None:
    report = run_project_closure(PUMP / "project_closure_plan.yaml")

    assert report.ok
    assert report.closure_status == "passed"
    assert report.summary["checked_input_count"] >= 7
    assert ProjectClosureReportSpec.model_validate(report.to_dict()).closure_status == "passed"


def test_blocking_evidence_gap_blocks_closure(tmp_path: Path) -> None:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    data["evidence_bindings"] = [
        item for item in data["evidence_bindings"] if item["binding_id"] != "clean_flow_readback_to_model_y"
    ]
    data["evidence_bundles"][0]["bindings"] = [
        item for item in data["evidence_bundles"][0]["bindings"] if item != "clean_flow_readback_to_model_y"
    ]
    registry = tmp_path / "missing_binding_registry.yaml"
    registry.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    plan = _write_plan(tmp_path, evidence_registry=str(registry))

    report = run_project_closure(plan)

    assert not report.ok
    assert report.closure_status == "blocked"
    assert any(item["type"] == "binding_expectation_unmet" for item in report.blocking_findings)
    assert any(item["check"] == "evidence_map" for item in report.checked_inputs)


def test_review_only_evidence_gap_makes_closure_partial(tmp_path: Path) -> None:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    data["project_profile"] = {
        "project_name_unknown_reason": "not found in available fixture sources",
        "run_period": {"unknown_reason": "test period not found yet"},
        "location_unknown_reason": "test location not found yet",
    }
    registry = tmp_path / "review_gap_registry.yaml"
    registry.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    plan = _write_plan(tmp_path, evidence_registry=str(registry))

    report = run_project_closure(plan)

    assert not report.ok
    assert report.closure_status == "partial"
    assert report.blocking_findings == []
    assert any(item["type"] == "project_profile_project_name_unknown" for item in report.review_findings)


def test_skipped_required_validation_blocks_closure(tmp_path: Path) -> None:
    plan = _write_plan(
        tmp_path,
        claim_scope="validation_ready",
        validation_plans=[],
        required_checks={
            "project_audit": True,
            "evidence_check": True,
            "evidence_gap_check": True,
            "evidence_map": True,
            "test_contracts": False,
            "validation": True,
            "model_library": False,
            "hierarchy_closure": False,
        },
    )

    report = run_project_closure(plan)

    assert not report.ok
    assert report.closure_status == "blocked"
    assert any(item["check"] == "validation" for item in report.skipped_checks)
    assert any(item["type"] == "project_closure_required_check_skipped" for item in report.blocking_findings)
