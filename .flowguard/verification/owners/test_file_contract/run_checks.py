"""Run FlowGuard checks for the PhysicsGuard test-file contract route and replay them on the real code."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "models/owners"))

import yaml
from flowguard.explorer import Explorer

from test_file_contract import physicsguard_test_file_contract_model as model

ROOT = Path(__file__).resolve().parents[4]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"
IMPLEMENTED_BY = {
    "VerifyManifestFreshness": "src/physicsguard/core/test_file_contract.py:_manifest_findings",
    "ResolveTestbenchProfile": "src/physicsguard/core/test_file_contract.py:_testbench_profile_findings",
    "ResolveModelBinding": "src/physicsguard/core/test_file_contract.py:_model_binding_targets",
    "EnforceCoverageContract": "src/physicsguard/core/parameter_coverage.py:check_parameter_coverage",
    "GateAnalysisClaim": "src/physicsguard/core/test_file_contract.py:check_test_file_contract",
}
TESTED_BY = {
    "no_testfile_claim_without_catalog_roles_and_mappings": [
        "tests/test_test_file_contract_core.py:test_added_manifest_field_blocks_contract",
    ],
    "no_testfile_claim_without_mapping_evidence_or_known_targets": [
        "tests/test_test_file_contract_core.py:test_mapping_without_evidence_does_not_count_as_covered",
    ],
    "no_testfile_claim_without_contract_pass": [
        "tests/test_test_file_contract_core.py:test_clean_contract_passes_with_evidence_backed_mappings",
        "tests/test_test_file_contract_core.py:test_review_required_contract_is_partial_and_not_ok",
    ],
}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _edit(relative: str, change):
    def apply(pump: Path) -> str:
        path = pump / relative
        data = _load(path)
        change(data)
        _write(path, data)
        return "contracts/clean_contract.yaml"

    return apply


def _append_row(pump: Path) -> str:
    data_file = pump / "data" / "clean.csv"
    data_file.write_text(data_file.read_text(encoding="utf-8") + "0.3,11.5,23.0,true\n", encoding="utf-8")
    return "contracts/clean_contract.yaml"


def _delete_source(pump: Path) -> str:
    (pump / "data" / "clean.csv").unlink()
    return "contracts/clean_contract.yaml"


def _edges(change):
    return _edit("coverage/pump_loop_mapping_edges.yaml", change)


def _drop_flow_edge(data: dict) -> None:
    data["edges"] = [item for item in data["edges"] if item["source_id"] != "field:flow_readback_kg_s"]


def _strip_evidence(data: dict) -> None:
    for edge in data["edges"]:
        edge["evidence"] = []


def _unknown_target(data: dict) -> None:
    next(item for item in data["edges"] if item["target"] == "pump_signal_map.y")["target"] = "pump_signal_map.missing"


def _review_required(data: dict) -> None:
    data["roles"][1]["coverage_status"] = "review_required"
    data["roles"][1]["reason"] = "AI inferred mapping from field name but human review is still needed."


REAL_CASES = {
    "clean_testfile": lambda pump: "contracts/clean_contract.yaml",
    "source_missing": _delete_source,
    "manifest_stale": _append_row,
    "extractor_missing": _edit("data/clean_manifest.yaml", lambda data: data.pop("extractor")),
    "profile_missing": _edit("contracts/clean_contract.yaml", lambda data: data.pop("testbench_profile")),
    "binding_missing": _edit("contracts/clean_contract.yaml", lambda data: data.pop("model_binding")),
    "catalog_gap": lambda pump: "contracts/added_field_contract.yaml",
    "role_gap": lambda pump: "contracts/unclassified_contract.yaml",
    "mapping_gap": _edges(_drop_flow_edge),
    "mapping_no_evidence": _edges(_strip_evidence),
    "unknown_model_target": _edges(_unknown_target),
    "review_required": _edit("coverage/pump_loop_role_matrix.yaml", _review_required),
    "contract_failed": lambda pump: "contracts/stale_model_contract.yaml",
}


def _model_statuses(case: model.ContractInput) -> set[str]:
    """Real contract statuses that agree with the model's terminal for this case."""

    run = model.build_workflow().execute(model.initial_state(), case, terminal_predicate=model.terminal_predicate)
    path = run.completed_paths[0]
    if isinstance(path.current_input, model.AnalysisClaimAllowed):
        return {"pass"}
    if path.trace.steps[-1].label.endswith("_partial"):
        return {"partial"}
    return {"partial", "fail"}


def conformance() -> list[str]:
    """Run each mapped model case through check_test_file_contract; return the mismatches."""

    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from physicsguard.core.test_file_contract import check_test_file_contract

    inputs = {item.case_id: item for item in model.EXTERNAL_INPUTS}
    mismatches = []
    with tempfile.TemporaryDirectory() as tmp:
        for index, (case_id, prepare) in enumerate(REAL_CASES.items()):
            pump = Path(tmp) / f"case_{index}" / "pump_loop"
            shutil.copytree(PUMP, pump)
            contract = pump / prepare(pump)
            try:
                real_status = check_test_file_contract(contract).status
            except (ValueError, FileNotFoundError):
                real_status = "fail"
            expected = _model_statuses(inputs[case_id])
            if real_status not in expected:
                mismatches.append(f"{case_id}: real status {real_status!r}, model expects {sorted(expected)}")
    return mismatches


def main() -> int:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        required_labels=(
            "no_test_data_optional_route",
            "test_data_route_selected",
            "manifest_generated",
            "manifest_fresh",
            "testbench_profile_resolved",
            "model_binding_resolved",
            "catalog_complete",
            "role_matrix_complete",
            "mapping_edges_evidenced",
            "coverage_contract_passed",
            "broad_claim_allowed",
            "source_file_missing",
            "manifest_not_generated",
            "manifest_missing_extractor",
            "manifest_stale",
            "testbench_profile_missing",
            "model_binding_missing",
            "catalog_missing_fields",
            "role_matrix_missing_roles",
            "mapping_edges_missing",
            "mapping_missing_evidence",
            "mapping_unknown_targets_model_gap",
            "review_required_partial",
            "planned_child_model_partial",
            "contract_check_failed",
        ),
    ).explore()
    print(report.format_text())
    mismatches = conformance()
    print(f"conformance: {len(REAL_CASES) - len(mismatches)}/{len(REAL_CASES)} model cases match the real code")
    for line in mismatches:
        print(f"  mismatch: {line}")
    return 0 if report.ok and not mismatches else 1


if __name__ == "__main__":
    from flowguard.map.runner import run_owner
    raise SystemExit(run_owner(main))
