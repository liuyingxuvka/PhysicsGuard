from __future__ import annotations

from pathlib import Path

import yaml

from physicsguard.core.contract_diff import diff_test_file_contracts
from physicsguard.core.data_file_manifest import field_signature_hash, generate_delimited_manifest
from physicsguard.core.test_file_contract import (
    check_test_file_contract,
    check_test_file_parameter_coverage,
)


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"


def test_generate_delimited_manifest_counts_fields_time_and_signature(tmp_path: Path) -> None:
    data_file = tmp_path / "sample.csv"
    data_file.write_text(
        "time_s,x,y\n0.0,1.0,2.0\n0.1,1.5,3.0\n",
        encoding="utf-8",
    )

    manifest = generate_delimited_manifest(data_file, time_column="time_s")

    assert manifest.shape.field_count == 3
    assert manifest.shape.row_count == 2
    assert manifest.time.duration_s == 0.1
    assert manifest.field_signature_hash == field_signature_hash(manifest)


def test_clean_contract_passes_with_evidence_backed_mappings() -> None:
    report = check_test_file_contract(PUMP / "contracts" / "clean_contract.yaml")

    assert report.ok
    assert report.status == "pass"
    assert report.summary["analysis_claim_gate"] == "open_for_scoped_analysis"


def test_added_manifest_field_blocks_contract() -> None:
    report = check_test_file_contract(PUMP / "contracts" / "added_field_contract.yaml")

    assert not report.ok
    assert report.status == "fail"
    assert any(finding.type == "manifest_field_missing_from_catalog" for finding in report.findings)


def test_stale_model_binding_blocks_contract() -> None:
    report = check_test_file_contract(PUMP / "contracts" / "stale_model_contract.yaml")

    assert not report.ok
    assert any(finding.type == "stale_model_binding" for finding in report.findings)


def test_mapping_without_evidence_does_not_count_as_covered(tmp_path: Path) -> None:
    mapping_data = yaml.safe_load((PUMP / "coverage" / "pump_loop_mapping_edges.yaml").read_text(encoding="utf-8"))
    for edge in mapping_data["edges"]:
        edge["evidence"] = []
    mapping_path = tmp_path / "mapping_edges_no_evidence.yaml"
    mapping_path.write_text(yaml.safe_dump(mapping_data, sort_keys=False), encoding="utf-8")

    contract_data = yaml.safe_load((PUMP / "contracts" / "clean_contract.yaml").read_text(encoding="utf-8"))
    contract_data["manifest"] = str((PUMP / "data" / "clean_manifest.yaml").resolve())
    contract_data["testbench_profile"] = str((PUMP / "profiles" / "pump_loop_testbench_profile.yaml").resolve())
    contract_data["extractor_profile"] = str((PUMP / "profiles" / "pump_loop_extractor_profile.yaml").resolve())
    contract_data["model_binding"] = str((PUMP / "bindings" / "pump_loop_model_binding.yaml").resolve())
    contract_data["parameter_catalog"] = str((PUMP / "catalogs" / "pump_loop_parameter_catalog.yaml").resolve())
    contract_data["role_matrix"] = str((PUMP / "coverage" / "pump_loop_role_matrix.yaml").resolve())
    contract_data["mapping_edges"] = str(mapping_path)
    contract_data["coverage_policy"] = str((PUMP / "coverage" / "pump_loop_coverage_policy.yaml").resolve())
    contract_path = tmp_path / "contract.yaml"
    contract_path.write_text(yaml.safe_dump(contract_data, sort_keys=False), encoding="utf-8")

    report = check_test_file_parameter_coverage(contract_path)

    assert not report.ok
    assert any(finding.type == "mapping_edge_missing_evidence" for finding in report.findings)


def test_review_required_contract_is_partial_and_not_ok(tmp_path: Path) -> None:
    role_data = yaml.safe_load((PUMP / "coverage" / "pump_loop_role_matrix.yaml").read_text(encoding="utf-8"))
    role_data["roles"][1]["coverage_status"] = "review_required"
    role_data["roles"][1]["reason"] = "AI inferred mapping from field name but human review is still needed."
    role_path = tmp_path / "review_required_roles.yaml"
    role_path.write_text(yaml.safe_dump(role_data, sort_keys=False), encoding="utf-8")

    contract_data = yaml.safe_load((PUMP / "contracts" / "clean_contract.yaml").read_text(encoding="utf-8"))
    contract_data["manifest"] = str((PUMP / "data" / "clean_manifest.yaml").resolve())
    contract_data["testbench_profile"] = str((PUMP / "profiles" / "pump_loop_testbench_profile.yaml").resolve())
    contract_data["extractor_profile"] = str((PUMP / "profiles" / "pump_loop_extractor_profile.yaml").resolve())
    contract_data["model_binding"] = str((PUMP / "bindings" / "pump_loop_model_binding.yaml").resolve())
    contract_data["parameter_catalog"] = str((PUMP / "catalogs" / "pump_loop_parameter_catalog.yaml").resolve())
    contract_data["role_matrix"] = str(role_path)
    contract_data["mapping_edges"] = str((PUMP / "coverage" / "pump_loop_mapping_edges.yaml").resolve())
    contract_data["coverage_policy"] = str((PUMP / "coverage" / "pump_loop_coverage_policy.yaml").resolve())
    contract_path = tmp_path / "review_required_contract.yaml"
    contract_path.write_text(yaml.safe_dump(contract_data, sort_keys=False), encoding="utf-8")

    report = check_test_file_contract(contract_path)

    assert not report.ok
    assert report.status == "partial"
    assert report.summary["analysis_claim_gate"] == "limited_claims_only"
    assert any(finding.type == "role_review_required" for finding in report.findings)


def test_contract_diff_flags_possible_rename() -> None:
    diff = diff_test_file_contracts(
        PUMP / "contracts" / "clean_contract.yaml",
        PUMP / "contracts" / "renamed_field_contract.yaml",
    )

    assert diff.status == "changed"
    assert any(change["type"] == "possible_field_rename" for change in diff.changes)
