"""Executable FlowGuard checks for PhysicsGuard skill-maintenance structure.

The suite report is deliberately non-authoritative.  This checker validates
the ten-member ownership/model boundary and each member's declared source
contract; it never reads, executes, aggregates, or authorizes SkillGuard
receipts.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import re
from typing import Any, Mapping

from physicsguard.guard_model_contract import (
    BASELINE_ROLE,
    GuardModelContractError,
    validate_baseline_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
MESH_PATH = Path(__file__).with_name("physicsguard_skill_suite_mesh.json")
CANONICAL_MODULES = {
    "src/physicsguard/guard_model_contract.py",
    "src/physicsguard/skill_execution_depth.py",
}
EXPECTED: dict[str, tuple[str, str, int]] = {
    "physicsguard-ai-debugging": (
        "physicsguard.ai-debugging",
        "route:physicsguard-ai-debugging:audit",
        8,
    ),
    "physicsguard-audit-closure": (
        "physicsguard.audit-closure",
        "route:physicsguard-audit-closure:close",
        8,
    ),
    "physicsguard-candidate-model-blueprint": (
        "physicsguard.candidate-model-blueprint",
        "route:physicsguard-candidate-model-blueprint:build",
        7,
    ),
    "physicsguard-model-dataset-validation": (
        "physicsguard-model-dataset-validation",
        "route:physicsguard-model-dataset-validation",
        8,
    ),
    "physicsguard-model-library": (
        "physicsguard.model-library",
        "route:physicsguard-model-library:reuse",
        7,
    ),
    "physicsguard-model-understanding-preflight": (
        "physicsguard.model-understanding-preflight",
        "route:physicsguard-model-understanding-preflight:review",
        7,
    ),
    "physicsguard-project-adoption": (
        "physicsguard.project-adoption",
        "route:physicsguard-project-adoption:audit",
        7,
    ),
    "physicsguard-project-evidence-registry": (
        "physicsguard.project-evidence-registry",
        "route:physicsguard-project-evidence-registry:check",
        7,
    ),
    "physicsguard-signal-mapping-review": (
        "physicsguard.signal-mapping-review",
        "route:physicsguard-signal-mapping-review:review",
        7,
    ),
    "physicsguard-test-file-contract-review": (
        "physicsguard.test-file-contract-review",
        "route:physicsguard-test-file-contract-review:check",
        8,
    ),
}
EXPECTED_GUARD_MODEL = {
    "semantic_owner": "physicsguard",
    "skillguard_role": "declared_checks_receipts_dependencies_and_closure_only",
    "family_baseline_role": "family_baseline_regression",
    "current_model_role": "current_model_purpose",
    "current_model_authority_root": ".physicsguard/model-purpose/<model-id>",
    "family_baseline_authoring_order": [
        "freeze_prevented_failure_contract",
        "build_candidate",
        "prove_known_good",
        "prove_every_known_bad",
        "issue_native_receipt",
    ],
    "current_model_authoring_order": [
        "freeze_current_model_purpose",
        "build_candidate",
        "prove_known_good",
        "prove_every_known_bad",
        "issue_current_model_receipt",
    ],
    "every_declared_failure_requires_exact_known_bad": True,
    "candidate_requires_contract_fingerprint": True,
    "candidate_artifact": "guard-model/candidate.json",
    "candidate_binding": "exact_contract_fingerprint_and_ordered_authoring_event_chain",
    "proof_strengths": [
        "native_semantic_detection",
        "native_obligation_admission_gate",
    ],
    "semantic_claim_requires_exact_native_fixture": True,
    "admission_claim_boundary": "candidate_rejected_only_when_current_target_native_obligation_evidence_is_absent_or_native_failed",
    "mode_branching": "forbidden",
    "family_baseline_can_close_current_model": False,
}


def _finding(findings: list[dict[str, str]], code: str, message: str) -> None:
    findings.append({"code": code, "message": message})


def _binding_id_fragment(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _path_selectors(check: Mapping[str, Any]) -> set[str]:
    return {
        str(row.get("path", ""))
        for row in check.get("input_selectors", [])
        if isinstance(row, Mapping) and row.get("kind") == "path"
    }


def _check_target_contract(target: str, findings: list[dict[str, str]]) -> None:
    skill_root = ROOT / "skill" / target
    guard_root = skill_root / "guard-model"
    values: dict[str, dict[str, Any]] = {}
    for name in ("contract", "candidate", "oracles", "known-good", "known-bad"):
        path = guard_root / f"{name}.json"
        if not path.is_file():
            _finding(findings, "guard_model_file_missing", f"{target}:{path.name}")
            return
        values[name] = json.loads(path.read_text(encoding="utf-8"))
    try:
        validate_baseline_bundle(skill_root)
    except GuardModelContractError as exc:
        _finding(findings, "guard_model_bundle_invalid", f"{target}:{exc}")

    contract = values["contract"]
    if (
        contract.get("schema_version") != "physicsguard.family_baseline_contract.v1"
        or contract.get("artifact_role") != BASELINE_ROLE
        or contract.get("target_skill_id") != target
    ):
        _finding(findings, "guard_model_identity_wrong", target)
    if contract.get("authoring_order") != EXPECTED_GUARD_MODEL["family_baseline_authoring_order"]:
        _finding(findings, "purpose_not_before_candidate", target)
    if contract.get("candidate_requires_contract_fingerprint") is not True:
        _finding(findings, "candidate_fingerprint_optional", target)
    if "selectable_modes" in contract:
        _finding(findings, "selectable_mode_present", target)

    failures = contract.get("prevented_failure_classes")
    failures = failures if isinstance(failures, list) else []
    failure_ids = {
        str(row.get("failure_id", ""))
        for row in failures
        if isinstance(row, Mapping) and row.get("failure_id")
    }
    oracle_ids = {
        str(row.get("failure_id", ""))
        for row in values["oracles"].get("oracles", [])
        if isinstance(row, Mapping)
    }
    bad_ids = {
        str(row.get("failure_id", ""))
        for row in values["known-bad"].get("cases", [])
        if isinstance(row, Mapping)
    }
    if not failure_ids or failure_ids != oracle_ids or failure_ids != bad_ids:
        _finding(findings, "native_failure_proof_inventory_wrong", target)

    source_path = skill_root / ".skillguard" / "contract-source.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    owner, route, expected_count = EXPECTED[target]
    checks = [row for row in source.get("checks", []) if isinstance(row, Mapping)]
    check_ids = [str(row.get("check_id", "")) for row in checks]
    semantic_ids = [str(row.get("semantic_check_id", "")) for row in checks]
    owner_ids = [str(row.get("execution_owner_id", "")) for row in checks]
    subject_ids = [str(row.get("evidence_subject_id", "")) for row in checks]
    if len(checks) != expected_count:
        _finding(findings, "declared_check_count_wrong", f"{target}:{len(checks)}")
    if any(len(set(rows)) != len(rows) for rows in (check_ids, semantic_ids, owner_ids, subject_ids)):
        _finding(findings, "member_check_identity_not_unique", target)
    if source.get("maintenance_unit_id") != "unit:physicsguard-family":
        _finding(findings, "foreign_maintenance_unit", target)
    if source.get("member_skill_ids") != sorted(EXPECTED):
        _finding(findings, "member_inventory_wrong", target)
    if source.get("native_route_owner") != owner or source.get("default_route_id") != route:
        _finding(findings, "native_route_identity_wrong", target)
    if source.get("native_route_bindings") != [
        {
            "binding_id": f"native:{target}:current",
            "native_route_id": route,
            "required_before_closure": True,
            "source": "guard-model/contract.json",
        }
    ]:
        _finding(findings, "native_route_binding_wrong", target)
    if source.get("may_define_parallel_execution_route") is not False:
        _finding(findings, "parallel_execution_route_not_forbidden", target)
    if source.get("may_define_skillguard_runtime_route") is not False:
        _finding(findings, "skillguard_runtime_route_not_forbidden", target)
    if source.get("release_eligible") is not False:
        _finding(findings, "source_contract_release_eligible", target)

    depth = source.get("depth_profile")
    if not isinstance(depth, Mapping):
        _finding(findings, "depth_profile_missing", target)
    else:
        if depth.get("native_owner_id") != owner or depth.get("native_route_ids") != [route]:
            _finding(findings, "depth_profile_native_identity_wrong", target)
        if depth.get("native_check_ids") != check_ids:
            _finding(findings, "depth_profile_check_inventory_wrong", target)
        if depth.get("skillguard_adds_domain_route") is not False:
            _finding(findings, "skillguard_adds_domain_route", target)

    expected_bindings = [
        {
            "binding_id": f"native-check:{target}:{_binding_id_fragment(check_id)}",
            "evidence_source": "physicsguard.guard_model_contract",
            "native_check_id": check_id,
            "required": True,
        }
        for check_id in check_ids
    ]
    if source.get("native_check_bindings") != expected_bindings:
        _finding(findings, "native_check_binding_inventory_wrong", target)

    for check in checks:
        if check.get("maintenance_unit_id") != "unit:physicsguard-family":
            _finding(findings, "check_foreign_maintenance_unit", str(check.get("check_id", "")))
        if check.get("member_skill_id") != target:
            _finding(findings, "check_member_identity_wrong", str(check.get("check_id", "")))
        args = [str(value) for value in check.get("args", [])]
        if args[:2] != ["-m", "physicsguard.guard_model_contract"]:
            _finding(findings, "noncanonical_guard_model_entrypoint", str(check.get("check_id", "")))
        selectors = _path_selectors(check)
        if not CANONICAL_MODULES <= selectors:
            _finding(findings, "canonical_simulator_input_missing", str(check.get("check_id", "")))
        if any(
            path.endswith("/guard-model/verify.py")
            or path.endswith("/runtime/skill_execution_depth.py")
            for path in selectors
        ):
            _finding(findings, "copied_simulator_input_present", str(check.get("check_id", "")))

    implementation_paths = set(map(str, source.get("implementation_paths", [])))
    if not CANONICAL_MODULES <= implementation_paths:
        _finding(findings, "canonical_simulator_implementation_missing", target)
    if any(
        path.endswith("/guard-model/verify.py")
        or path.endswith("/runtime/skill_execution_depth.py")
        for path in implementation_paths
    ):
        _finding(findings, "copied_simulator_implementation_present", target)


def _check_retired_authority_absent(findings: list[dict[str, str]]) -> None:
    retired = (
        ROOT / ".flowguard" / "skillguard-parent",
        ROOT / ".flowguard" / "physicsguard_suite_parent_inventory.json",
        ROOT / "scripts" / "generate_physicsguard_suite_parent_contract.py",
        ROOT / "scripts" / "verify_physicsguard_suite_parent.py",
    )
    for path in retired:
        if path.exists():
            _finding(findings, "retired_parent_authority_present", path.relative_to(ROOT).as_posix())
    if not (ROOT / "scripts" / "report_physicsguard_skill_suite.py").is_file():
        _finding(findings, "non_authoritative_summary_missing", "scripts/report_physicsguard_skill_suite.py")


def _check_local_runtime_copies(mesh: Mapping[str, Any], findings: list[dict[str, str]]) -> None:
    disposition = str(mesh.get("canonical_simulator", {}).get("dataset_bundle_disposition", ""))
    for path in sorted((ROOT / "skill").glob("physicsguard-*/guard-model/verify.py")):
        _finding(findings, "copied_guard_model_verifier_present", path.relative_to(ROOT).as_posix())
    for path in sorted((ROOT / "skill").glob("physicsguard-*/runtime/skill_execution_depth.py")):
        _finding(findings, "copied_execution_depth_present", path.relative_to(ROOT).as_posix())
    dataset_package = ROOT / "skill" / "physicsguard-model-dataset-validation" / "runtime" / "physicsguard"
    if disposition == "removed_after_isolated_equivalence":
        if dataset_package.exists():
            _finding(findings, "dataset_bundle_present_after_removal", dataset_package.relative_to(ROOT).as_posix())
    elif disposition == "retained_generated_projection":
        manifest = dataset_package.parent / "native-runtime-manifest.json"
        if not dataset_package.is_dir() or not manifest.is_file():
            _finding(findings, "retained_dataset_projection_incomplete", manifest.relative_to(ROOT).as_posix())
    else:
        _finding(findings, "dataset_bundle_disposition_unresolved", disposition)


def check_mesh(mesh: Mapping[str, Any], *, check_targets: bool = True) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    if mesh.get("guard_model_contract") != EXPECTED_GUARD_MODEL:
        _finding(findings, "guard_model_contract_drift", "PhysicsGuard target semantics or proof order drifted.")

    boundary = mesh.get("maintenance_boundary")
    expected_boundary = {
        "maintenance_unit_id": "unit:physicsguard-family",
        "member_count": 10,
        "suite_summary_authoritative": False,
        "suite_summary_may_execute_checks": False,
        "suite_summary_may_consume_receipts": False,
        "suite_summary_may_issue_closure": False,
        "forbidden_parent_unit_id": "unit:physicsguard-skill-suite-parent",
        "summary_path": "scripts/report_physicsguard_skill_suite.py",
    }
    if not isinstance(boundary, Mapping) or any(
        boundary.get(field) != expected for field, expected in expected_boundary.items()
    ):
        _finding(findings, "maintenance_boundary_wrong", "Suite summary must remain same-unit and non-authoritative.")

    children = mesh.get("children")
    children = children if isinstance(children, list) else []
    by_target: dict[str, Mapping[str, Any]] = {}
    owners: set[str] = set()
    for child in children:
        if not isinstance(child, Mapping):
            _finding(findings, "invalid_child", "Child rows must be objects.")
            continue
        target = str(child.get("target_skill_id", ""))
        if target in by_target:
            _finding(findings, "duplicate_child", target)
        by_target[target] = child
        if target not in EXPECTED:
            _finding(findings, "foreign_child", target)
            continue
        owner, route, count = EXPECTED[target]
        if child.get("native_owner_id") != owner or child.get("native_route_id") != route:
            _finding(findings, "child_identity_mismatch", target)
        if child.get("declared_check_count") != count:
            _finding(findings, "child_check_count_mismatch", target)
        if child.get("summary_relation") != "inventory_only_member_receipt_not_consumed":
            _finding(findings, "receipt_consuming_summary_relation", target)
        if owner in owners:
            _finding(findings, "duplicate_native_owner", owner)
        owners.add(owner)
    if set(by_target) != set(EXPECTED) or len(children) != len(EXPECTED):
        _finding(findings, "child_inventory_mismatch", "Exactly ten PhysicsGuard members are required.")
    if "affected_siblings" in mesh or "parent_closure" in mesh:
        _finding(findings, "retired_parent_authority_in_model", "No child or sibling may be reattached to a parent closure.")

    simulator = mesh.get("canonical_simulator")
    if not isinstance(simulator, Mapping):
        _finding(findings, "canonical_simulator_missing", "Canonical simulator boundary is required.")
    else:
        if set(map(str, simulator.get("source_authority", []))) != CANONICAL_MODULES:
            _finding(findings, "canonical_simulator_authority_wrong", "Exactly two canonical source modules are required.")
        if simulator.get("copied_editable_implementations_allowed") is not False:
            _finding(findings, "copied_editable_simulator_allowed", "Copied implementations cannot be editable authority.")
        if simulator.get("missing_dependency_behavior") != "fail_visible":
            _finding(findings, "runtime_fallback_allowed", "Missing canonical package must fail visibly.")

    architecture = mesh.get("architecture_reduction", {})
    candidate_ids = {
        str(row.get("candidate_id", ""))
        for row in architecture.get("candidates", [])
        if isinstance(row, Mapping)
    }
    if candidate_ids != {
        "remove-cross-unit-parent-authority",
        "collapse-satellite-runtime-copies",
        "remove-dataset-bundled-runtime",
    }:
        _finding(findings, "architecture_reduction_inventory_wrong", "All contraction candidates must remain visible.")

    structure = mesh.get("structure_mesh", {})
    if set(map(str, structure.get("target_modules", []))) != {
        "physicsguard.guard_model_contract",
        "physicsguard.skill_execution_depth",
    } or structure.get("public_entrypoint_plan") != "package_module_entrypoints_no_fallback":
        _finding(findings, "structure_mesh_target_wrong", "Canonical module target and no-fallback entrypoints are required.")

    test_mesh = mesh.get("test_mesh", {})
    planned = int(test_mesh.get("planned", -1))
    executed = int(test_mesh.get("executed", -1))
    failed = int(test_mesh.get("failed", -1))
    not_run = int(test_mesh.get("not_run", -1))
    if planned != sum(value[2] for value in EXPECTED.values()):
        _finding(findings, "test_mesh_inventory_wrong", str(planned))
    if planned != executed + not_run or failed > executed:
        _finding(findings, "test_mesh_accounting_wrong", f"{planned}:{executed}:{failed}:{not_run}")
    if test_mesh.get("diagnostic_boundary") == "declared_complete" and not_run:
        _finding(findings, "hidden_not_run_under_complete", str(not_run))
    if not_run and not str(test_mesh.get("not_run_reason", "")):
        _finding(findings, "not_run_reason_missing", str(not_run))

    lifecycle = mesh.get("evidence_lifecycle", {})
    if lifecycle.get("source_authority") is not False or lifecycle.get("freshness_input") is not False:
        _finding(findings, "evidence_output_promoted_to_source", "Receipts and runs are outputs only.")
    if lifecycle.get("quarantine_authorized") is not False or lifecycle.get("purge_authorized") is not False:
        _finding(findings, "evidence_deletion_authorized", "This change permits read-only audit/plan only.")

    if check_targets:
        _check_retired_authority_absent(findings)
        _check_local_runtime_copies(mesh, findings)
        for target in sorted(EXPECTED):
            _check_target_contract(target, findings)
    return {
        "artifact_kind": "physicsguard_skill_suite_maintenance_mesh_check",
        "authoritative": False,
        "structure_status": "pass" if not findings else "blocked",
        "member_count": len(by_target),
        "declared_check_count": sum(value[2] for value in EXPECTED.values()),
        "findings": findings,
        "claim_boundary": (
            "This is source-structure/model evidence only. It executes no member check, "
            "consumes no receipt, and issues no SkillGuard or PhysicsGuard closure."
        ),
    }


def known_bad_results(mesh: Mapping[str, Any]) -> dict[str, str]:
    cases: dict[str, dict[str, Any]] = {}
    missing = copy.deepcopy(mesh)
    missing["children"] = missing["children"][:-1]
    cases["missing_member"] = missing
    duplicate = copy.deepcopy(mesh)
    duplicate["children"].append(copy.deepcopy(duplicate["children"][0]))
    cases["duplicate_member"] = duplicate
    wrong_owner = copy.deepcopy(mesh)
    wrong_owner["children"][1]["native_owner_id"] = wrong_owner["children"][0]["native_owner_id"]
    cases["duplicate_owner"] = wrong_owner
    foreign_unit = copy.deepcopy(mesh)
    foreign_unit["maintenance_boundary"]["maintenance_unit_id"] = "unit:foreign"
    cases["foreign_unit"] = foreign_unit
    authoritative = copy.deepcopy(mesh)
    authoritative["maintenance_boundary"]["suite_summary_authoritative"] = True
    cases["authoritative_summary"] = authoritative
    consumes = copy.deepcopy(mesh)
    consumes["maintenance_boundary"]["suite_summary_may_consume_receipts"] = True
    cases["receipt_consuming_summary"] = consumes
    copied = copy.deepcopy(mesh)
    copied["canonical_simulator"]["copied_editable_implementations_allowed"] = True
    cases["copied_editable_simulator"] = copied
    hidden = copy.deepcopy(mesh)
    hidden["test_mesh"]["diagnostic_boundary"] = "declared_complete"
    hidden["test_mesh"]["executed"] = hidden["test_mesh"]["planned"] - 1
    hidden["test_mesh"]["not_run"] = 1
    hidden["test_mesh"]["not_run_reason"] = ""
    cases["hidden_not_run"] = hidden
    semantic_owner = copy.deepcopy(mesh)
    semantic_owner["guard_model_contract"]["semantic_owner"] = "skillguard"
    cases["skillguard_owns_semantics"] = semantic_owner
    optional = copy.deepcopy(mesh)
    optional["guard_model_contract"]["mode_branching"] = "allowed"
    cases["selectable_mode"] = optional
    wrong_order = copy.deepcopy(mesh)
    wrong_order["guard_model_contract"]["current_model_authoring_order"] = wrong_order[
        "guard_model_contract"
    ]["current_model_authoring_order"][1:]
    cases["candidate_before_purpose"] = wrong_order
    return {
        name: check_mesh(case, check_targets=False)["structure_status"]
        for name, case in cases.items()
    }


def main() -> int:
    mesh = json.loads(MESH_PATH.read_text(encoding="utf-8"))
    result = check_mesh(mesh)
    result["known_bads"] = known_bad_results(mesh)
    if any(status != "blocked" for status in result["known_bads"].values()):
        result["structure_status"] = "blocked"
        _finding(result["findings"], "known_bad_not_blocked", "Every declared topology bad case must block.")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["structure_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
