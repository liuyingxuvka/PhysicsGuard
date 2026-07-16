"""Executable ModelMesh checks for PhysicsGuard baseline/current ownership."""

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
from physicsguard.skill_execution_depth import ROUTE_POLICIES


ROOT = Path(__file__).resolve().parents[1]
MESH_PATH = Path(__file__).with_name("physicsguard_skill_suite_mesh.json")
PRIMARY = "physicsguard-model-dataset-validation"
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
FORBIDDEN_SKILLGUARD_FIELDS = {
    "calibration",
}
FORBIDDEN_CHECK_FIELDS = {
    "depth_evidence_protocol",
    "depth_evidence_domain",
    "depth_evidence_output",
    "calibration_evidence_protocol",
    "calibration_evidence_domain",
    "calibration_evidence_output",
}


def _finding(findings: list[dict[str, str]], code: str, message: str) -> None:
    findings.append({"code": code, "message": message})


def _binding_id_fragment(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


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
    oracles = values["oracles"]
    known_good = values["known-good"]
    known_bad = values["known-bad"]
    if (
        contract.get("schema_version") != "physicsguard.family_baseline_contract.v1"
        or contract.get("artifact_role") != BASELINE_ROLE
    ):
        _finding(findings, "guard_model_schema_wrong", target)
    if contract.get("target_skill_id") != target:
        _finding(findings, "guard_model_target_wrong", target)
    if contract.get("authoring_order") != EXPECTED_GUARD_MODEL["family_baseline_authoring_order"]:
        _finding(findings, "purpose_not_before_candidate", target)
    if contract.get("candidate_requires_contract_fingerprint") is not True:
        _finding(findings, "candidate_fingerprint_optional", target)
    if "selectable_modes" in contract:
        _finding(findings, "selectable_mode_present", target)
    failures = contract.get("prevented_failure_classes")
    if not isinstance(failures, list) or not failures:
        _finding(findings, "prevented_failure_missing", target)
        failures = []
    failure_ids = {
        str(row.get("failure_id", ""))
        for row in failures
        if isinstance(row, Mapping) and row.get("failure_id")
    }
    for row in failures:
        if not isinstance(row, Mapping):
            continue
        if any(
            not str(row.get(field, ""))
            for field in (
                "block_when",
                "expected_finding_code",
                "proof_strength",
                "known_limit",
                "claim_boundary",
            )
        ):
            _finding(findings, "prevented_failure_incomplete", target)
    oracle_rows = oracles.get("oracles") if isinstance(oracles, Mapping) else []
    oracle_failure_ids = {
        str(row.get("failure_id", ""))
        for row in oracle_rows or []
        if isinstance(row, Mapping)
    }
    bad_rows = known_bad.get("cases") if isinstance(known_bad, Mapping) else []
    bad_failure_ids = {
        str(row.get("failure_id", ""))
        for row in bad_rows or []
        if isinstance(row, Mapping)
    }
    if failure_ids != oracle_failure_ids:
        _finding(findings, "failure_without_oracle", target)
    if failure_ids != bad_failure_ids or len(bad_rows or []) != len(failure_ids):
        _finding(findings, "failure_without_exact_known_bad", target)
    obligations = set(oracles.get("required_obligation_ids", []))
    if set(known_good.get("covered_obligation_ids", [])) != obligations:
        _finding(findings, "known_good_incomplete", target)

    skillguard = json.loads(
        (skill_root / ".skillguard" / "contract-source.json").read_text(encoding="utf-8")
    )
    stale = sorted(FORBIDDEN_SKILLGUARD_FIELDS.intersection(skillguard))
    if stale:
        _finding(findings, "skillguard_semantic_field_present", f"{target}:{','.join(stale)}")
    checks = skillguard.get("checks") or []
    check_by_id = {
        str(row.get("check_id", "")): row
        for row in checks
        if isinstance(row, Mapping)
    }
    native_owner = str(contract.get("native_owner_id", ""))
    native_route = str(contract.get("native_route_id", ""))
    contract_check = f"check:{target}:family-baseline-contract"
    candidate_check = f"check:{target}:family-baseline-candidate"
    good_check = f"check:{target}:family-baseline-good"
    if skillguard.get("integration_mode") != "native-integrated":
        _finding(findings, "native_integration_mode_wrong", target)
    if skillguard.get("native_route_owner") != native_owner:
        _finding(findings, "native_route_owner_wrong", target)
    if skillguard.get("default_route_id") != native_route:
        _finding(findings, "native_default_route_wrong", target)
    expected_route_bindings = [
        {
            "binding_id": f"native:{target}:current",
            "native_route_id": native_route,
            "required_before_closure": True,
            "source": "guard-model/contract.json",
        }
    ]
    if skillguard.get("native_route_bindings") != expected_route_bindings:
        _finding(findings, "native_route_binding_wrong", target)
    if skillguard.get("may_define_parallel_execution_route") is not False:
        _finding(findings, "parallel_execution_route_not_forbidden", target)
    if skillguard.get("may_define_skillguard_runtime_route") is not False:
        _finding(findings, "skillguard_runtime_route_not_forbidden", target)
    if skillguard.get("release_eligible") is not False:
        _finding(findings, "source_contract_release_eligible", target)
    expected_check_bindings = [
        {
            "binding_id": (
                f"native-check:{target}:"
                f"{_binding_id_fragment(str(row.get('check_id', '')))}"
            ),
            "evidence_source": "guard-model/verify.py",
            "native_check_id": str(row.get("check_id", "")),
            "required": True,
        }
        for row in checks
        if isinstance(row, Mapping)
    ]
    actual_check_binding_rows = skillguard.get("native_check_bindings")
    if actual_check_binding_rows != expected_check_bindings:
        _finding(findings, "native_check_binding_inventory_wrong", target)
    depth_profile = skillguard.get("depth_profile")
    check_ids = [str(row.get("check_id", "")) for row in checks]
    if not isinstance(depth_profile, Mapping):
        _finding(findings, "depth_profile_missing", target)
        depth_profile = {}
    expected_depth_identity = {
        "schema_version": "skillguard.depth_profile.v2",
        "profile_id": f"profile:{target}:family-baseline-regression",
        "target_skill_id": target,
        "integration_mode": "native-integrated",
        "native_owner_id": native_owner,
        "native_route_ids": [native_route],
        "native_check_ids": check_ids,
        "skillguard_adds_domain_route": False,
        "enforcement_level": "enforced",
        "required_closure_profiles": ["enforced"],
    }
    for field, expected in expected_depth_identity.items():
        if depth_profile.get(field) != expected:
            _finding(findings, "depth_profile_identity_wrong", f"{target}:{field}")
    provider_runtime = depth_profile.get("provider_runtime")
    if not isinstance(provider_runtime, Mapping) or any(
        provider_runtime.get(field) != expected
        for field, expected in {
            "provider_id": "skillguard-local-provider",
            "required_runtime_contract_id": "skillguard-declared-check-supervision-current",
            "required_enrollment_status": "enrolled",
            "readiness_check_ids": [contract_check],
        }.items()
    ):
        _finding(findings, "depth_profile_provider_runtime_wrong", target)
    if "calibration" in depth_profile:
        _finding(findings, "depth_profile_semantic_calibration_present", target)
    required_obligation_ids = [
        str(obligation_id)
        for row in checks
        for obligation_id in row.get("covers_obligation_ids", [])
    ]
    if skillguard.get("closure_profiles") != [
        {
            "profile_id": "enforced",
            "required_obligation_ids": required_obligation_ids,
        }
    ]:
        _finding(findings, "native_checks_not_required_before_sole_closure", target)
    if (
        contract_check not in check_by_id
        or candidate_check not in check_by_id
        or good_check not in check_by_id
    ):
        _finding(findings, "mandatory_proof_check_missing", target)
    elif check_by_id[candidate_check].get("depends_on_check_ids") != [contract_check]:
        _finding(findings, "candidate_dependency_wrong", candidate_check)
    elif check_by_id[good_check].get("depends_on_check_ids") != [candidate_check]:
        _finding(findings, "known_good_dependency_wrong", good_check)
    for failure_id in failure_ids:
        suffix = failure_id.rsplit(":", 1)[-1]
        check_id = f"check:{target}:family-baseline-bad:{suffix}"
        row = check_by_id.get(check_id)
        if row is None:
            _finding(findings, "known_bad_check_missing", f"{target}:{failure_id}")
            continue
        if row.get("depends_on_check_ids") != [good_check]:
            _finding(findings, "known_bad_dependency_wrong", check_id)
    for row in checks:
        retired = sorted(FORBIDDEN_CHECK_FIELDS.intersection(row))
        if retired:
            _finding(findings, "retired_skillguard_check_field", f"{target}:{','.join(retired)}")


def check_mesh(mesh: Mapping[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    if mesh.get("guard_model_contract") != EXPECTED_GUARD_MODEL:
        _finding(findings, "guard_model_contract_drift", "PhysicsGuard semantic ownership or fixed proof order drifted.")
    children = mesh.get("children")
    if not isinstance(children, list):
        children = []
        _finding(findings, "missing_children", "Mesh children must be a list.")
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
        owner = str(child.get("native_owner_id", ""))
        if owner in owners:
            _finding(findings, "duplicate_native_owner", owner)
        owners.add(owner)
        policy = ROUTE_POLICIES.get(target)
        if policy is None:
            _finding(findings, "foreign_child", target)
            continue
        if owner != policy.native_owner_id or child.get("native_route_id") != policy.native_route_id:
            _finding(findings, "child_identity_mismatch", target)
        if child.get("reattachment") != "terminal native depth receipt consumed by parent without re-execution":
            _finding(findings, "unsafe_or_missing_reattachment", target)
    if set(by_target) != set(ROUTE_POLICIES):
        _finding(findings, "child_inventory_mismatch", "The ten maintained PhysicsGuard skill ids must be exact.")
    siblings = mesh.get("affected_siblings")
    if not isinstance(siblings, list) or [row.get("target_skill_id") for row in siblings] != [PRIMARY]:
        _finding(findings, "primary_sibling_missing", PRIMARY)
    parent = mesh.get("parent_closure")
    if not isinstance(parent, Mapping) or any(
        parent.get(field) != expected
        for field, expected in {
            "requires_all_children": True,
            "requires_affected_siblings": True,
            "receipt_state": "terminal_success",
            "consumption": "receipt_only",
            "child_graph_expansion": "forbidden",
            "locally_green_unattached_child": "blocked",
        }.items()
    ):
        _finding(findings, "unsafe_parent_closure", "Parent must consume every current child receipt exactly once.")
    projection = mesh.get("evidence_projection")
    if not isinstance(projection, Mapping) or projection.get("evidence_domains") != [
        "capability_validation",
        "scheduled_production",
    ]:
        _finding(findings, "evidence_domain_drift", "Capability proof cannot close a scheduled project.")
    if (
        not isinstance(projection, Mapping)
        or projection.get("scheduled_production_identity_source")
        != "exactly_one_target_owned_identity_sidecar_in_declared_inputs"
    ):
        _finding(
            findings,
            "scheduled_identity_source_drift",
            "Formal production identity must come only from one target-owned sidecar in the declared inputs.",
        )
    for target in sorted([*ROUTE_POLICIES, PRIMARY]):
        _check_target_contract(target, findings)
    return {
        "artifact_kind": "physicsguard_skill_suite_mesh_check",
        "status": "pass" if not findings else "blocked",
        "child_count": len(by_target),
        "governed_target_count": len(ROUTE_POLICIES) + 1,
        "findings": findings,
    }


def known_bad_results(mesh: Mapping[str, Any]) -> dict[str, str]:
    cases: dict[str, dict[str, Any]] = {}
    missing = copy.deepcopy(mesh)
    missing["children"] = missing["children"][:-1]
    cases["missing_child"] = missing
    duplicate = copy.deepcopy(mesh)
    duplicate["children"].append(copy.deepcopy(duplicate["children"][0]))
    cases["duplicate_child"] = duplicate
    wrong_owner = copy.deepcopy(mesh)
    wrong_owner["children"][1]["native_owner_id"] = wrong_owner["children"][0]["native_owner_id"]
    cases["duplicate_owner"] = wrong_owner
    missing_primary = copy.deepcopy(mesh)
    missing_primary["affected_siblings"] = []
    cases["missing_primary"] = missing_primary
    unsafe_parent = copy.deepcopy(mesh)
    unsafe_parent["parent_closure"]["child_graph_expansion"] = "allowed"
    cases["unsafe_parent"] = unsafe_parent
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
    return {name: check_mesh(case)["status"] for name, case in cases.items()}


def main() -> int:
    mesh = json.loads(MESH_PATH.read_text(encoding="utf-8"))
    result = check_mesh(mesh)
    result["known_bads"] = known_bad_results(mesh)
    if any(status != "blocked" for status in result["known_bads"].values()):
        result["status"] = "blocked"
        _finding(result["findings"], "known_bad_not_blocked", "Every declared topology bad case must block.")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
