"""Executable FlowGuard checks for PhysicsGuard skill-maintenance structure.

The suite report is deliberately non-authoritative.  This checker validates
the ten-member ownership/model boundary and each member's declared source
contract; it never reads, executes, aggregates, or authorizes SkillGuard
receipts.
"""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import importlib.util
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
PROMPT_LOAD_GRAPH_PATH = Path(__file__).with_name(
    "physicsguard_skill_prompt_load_graph.json"
)
PURPOSE_CONTRACT_GENERATOR_PATH = (
    ROOT / "scripts" / "upgrade_purpose_contracts.py"
)
ROUTE_CAPSULE_SCHEMA = "physicsguard.skill_route_capsule.v1"
PROMPT_LOAD_GRAPH_SCHEMA = "physicsguard.skill_prompt_load_graph.v1"
REQUIRED_DEEP_CAPABILITIES = {
    "execution_depth",
    "mapping",
    "residual",
    "uncertainty",
    "diagnosability",
    "predictive_rollout",
    "purpose_before_candidate",
    "prediction_before_observation",
    "model_miss",
    "typed_regression",
    "independent_holdout",
    "exact_terminal_boundary",
}
ENTRY_SHARED_GOVERNED_INPUTS = {
    ".flowguard/check_physicsguard_skill_suite_mesh.py",
    ".flowguard/model-regression-manifest.json",
    ".flowguard/physicsguard_skill_prompt_load_graph.json",
    ".flowguard/physicsguard_skill_suite_mesh.json",
    "VERSION",
    "pyproject.toml",
    "src/physicsguard/__init__.py",
    "scripts/check_installed_physicsguard_skills.py",
    # These author-side helpers are imported by the shared entry/loading
    # checks.  They belong to the common governed spine, not to the
    # family-only maintenance owner.
    "scripts/physicsguard_skill_install_authority.py",
    "scripts/upgrade_purpose_contracts.py",
    "scripts/verify_guard_simulation_readiness.py",
    "tests/test_guard_skill_mesh.py",
    "tests/test_installed_skill_sync.py",
    "tests/test_physicsguard_skill_entry_loading.py",
    "tests/test_post_archive_retirement_authority.py",
    "tests/test_skillguard_v2_runtime_authority_audit.py",
    "tests/test_version_consistency.py",
}
FAMILY_MAINTENANCE_MEMBER_ID = "physicsguard-audit-closure"
FAMILY_MAINTENANCE_CHECK_ID = "check:physicsguard-family:distribution-authority"
FAMILY_MAINTENANCE_OWNER_ID = "owner:physicsguard-family:distribution-authority"
FAMILY_MAINTENANCE_PROJECTION_ID = (
    "projection:physicsguard-family-maintenance-definition"
)
FAMILY_MAINTENANCE_INPUTS = {
    ".flowguard/check_physicsguard_skill_suite_mesh.py",
    ".flowguard/model-regression-manifest.json",
    ".flowguard/physicsguard_skill_prompt_load_graph.json",
    ".flowguard/physicsguard_skill_suite_mesh.json",
    ".skillguard/test-mesh.json",
    "VERSION",
    "pyproject.toml",
    "scripts/check_physicsguard_test_mesh.py",
    "scripts/check_installed_physicsguard_skills.py",
    "scripts/install_physicsguard_skills.py",
    "scripts/physicsguard_skill_install_authority.py",
    "scripts/report_physicsguard_skill_suite.py",
    "scripts/upgrade_purpose_contracts.py",
    "scripts/verify_guard_simulation_readiness.py",
    "src/physicsguard/__init__.py",
    "tests/test_guard_skill_mesh.py",
    "tests/test_installed_skill_sync.py",
    "tests/test_install_physicsguard_skills.py",
    "tests/test_physicsguard_family_maintenance.py",
    "tests/test_physicsguard_skill_install_authority.py",
    "tests/test_post_archive_retirement_authority.py",
    "tests/test_skillguard_v2_runtime_authority_audit.py",
    "tests/test_version_consistency.py",
}
FAMILY_MAINTENANCE_EXCLUSIVE_INPUTS = (
    FAMILY_MAINTENANCE_INPUTS - ENTRY_SHARED_GOVERNED_INPUTS
)
CANONICAL_MODULES = {
    "src/physicsguard/guard_model_contract.py",
    "src/physicsguard/skill_execution_depth.py",
    "src/physicsguard/schema/task_local_revision.py",
    "src/physicsguard/core/task_local_revision.py",
    "src/physicsguard/cli.py",
}
TASK_MODEL_MODULES = {
    "src/physicsguard/schema/task_local_revision.py",
    "src/physicsguard/core/task_local_revision.py",
    "src/physicsguard/cli.py",
}
EXPECTED: dict[str, tuple[str, str, int]] = {
    "physicsguard-ai-debugging": (
        "physicsguard.ai-debugging",
        "route:physicsguard-ai-debugging:audit",
        9,
    ),
    "physicsguard-audit-closure": (
        "physicsguard.audit-closure",
        "route:physicsguard-audit-closure:close",
        10,
    ),
    "physicsguard-candidate-model-blueprint": (
        "physicsguard.candidate-model-blueprint",
        "route:physicsguard-candidate-model-blueprint:build",
        8,
    ),
    "physicsguard-model-dataset-validation": (
        "physicsguard-model-dataset-validation",
        "route:physicsguard-model-dataset-validation",
        9,
    ),
    "physicsguard-model-library": (
        "physicsguard.model-library",
        "route:physicsguard-model-library:reuse",
        8,
    ),
    "physicsguard-model-understanding-preflight": (
        "physicsguard.model-understanding-preflight",
        "route:physicsguard-model-understanding-preflight:review",
        8,
    ),
    "physicsguard-project-adoption": (
        "physicsguard.project-adoption",
        "route:physicsguard-project-adoption:audit",
        8,
    ),
    "physicsguard-project-evidence-registry": (
        "physicsguard.project-evidence-registry",
        "route:physicsguard-project-evidence-registry:check",
        8,
    ),
    "physicsguard-signal-mapping-review": (
        "physicsguard.signal-mapping-review",
        "route:physicsguard-signal-mapping-review:review",
        8,
    ),
    "physicsguard-test-file-contract-review": (
        "physicsguard.test-file-contract-review",
        "route:physicsguard-test-file-contract-review:check",
        9,
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
    "task_local_model_role": "strict_receipt_derived_model_deepening",
    "task_local_gap_authority": "target_owned_six_family_native_depth_receipt",
    "task_local_closure_rule": "zero_native_gaps_plus_exact_candidate_regression_independent_holdout_and_predictive_receipts",
}


def _finding(findings: list[dict[str, str]], code: str, message: str) -> None:
    findings.append({"code": code, "message": message})


def _binding_id_fragment(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def _current_toolchain_identity_resolution() -> tuple[dict[str, str] | None, str | None]:
    """Freeze the same direct-current identity used by the official generator.

    Resolution failures are returned as an explicit blocker.  The checker never
    substitutes a historical version literal or treats the generated mesh as
    its own authority.
    """

    try:
        spec = importlib.util.spec_from_file_location(
            "physicsguard_purpose_contract_generator_for_suite_check",
            PURPOSE_CONTRACT_GENERATOR_PATH,
        )
        if spec is None or spec.loader is None:
            raise ImportError("purpose_contract_generator_loader_missing")
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        identity = generator.current_toolchain_identity(
            repository_root=ROOT,
            flowguard_project_path=ROOT / ".flowguard" / "project.toml",
            skillguard_root=generator.DEFAULT_SKILLGUARD_ROOT,
        )
        if not isinstance(identity, Mapping) or not identity:
            raise TypeError("current_toolchain_identity_not_object")
        return {str(key): str(value) for key, value in identity.items()}, None
    except Exception as exc:
        return None, f"{type(exc).__name__}:{exc}"


def check_prompt_load_graph(
    graph: Mapping[str, Any], *, check_files: bool = True
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    expected_toolchain, authority_error = _current_toolchain_identity_resolution()
    if authority_error is not None:
        _finding(
            findings,
            "toolchain_authority_unresolved",
            authority_error,
        )
    if graph.get("schema_version") != PROMPT_LOAD_GRAPH_SCHEMA:
        _finding(findings, "prompt_load_graph_schema_wrong", str(graph.get("schema_version", "")))
    if expected_toolchain is not None and graph.get("suite_version") != expected_toolchain["physicsguard_version"]:
        _finding(findings, "prompt_load_suite_version_stale", str(graph.get("suite_version", "")))
    if expected_toolchain is not None and graph.get("toolchain_identity") != expected_toolchain:
        _finding(findings, "prompt_load_toolchain_identity_stale", str(graph.get("toolchain_identity", "")))
    if graph.get("route_count") != 10:
        _finding(findings, "prompt_load_route_count_wrong", str(graph.get("route_count", "")))
    if graph.get("initial_loading_rule") != "selected_metadata_plus_compact_skill_plus_route_capsule_only":
        _finding(findings, "prompt_initial_loading_rule_wrong", "Only selected metadata, compact prompt, and capsule may load initially.")
    if graph.get("all_reference_loading_forbidden") is not True:
        _finding(findings, "eager_all_references_allowed", "All references must remain conditional.")
    if graph.get("cross_skill_loading_rule") != "typed_handoff_only":
        _finding(findings, "cross_skill_loading_not_typed", "Cross-skill material requires a typed handoff.")
    if graph.get("maximum_reference_depth") != 1:
        _finding(findings, "reference_depth_wrong", str(graph.get("maximum_reference_depth", "")))
    if set(map(str, graph.get("required_deep_capabilities", []))) != REQUIRED_DEEP_CAPABILITIES:
        _finding(findings, "deep_capability_inventory_wrong", "The full native depth surface must remain reachable.")

    nodes = graph.get("nodes")
    nodes = nodes if isinstance(nodes, list) else []
    by_path: dict[str, Mapping[str, Any]] = {}
    for row in nodes:
        if not isinstance(row, Mapping):
            _finding(findings, "prompt_load_node_invalid", "Nodes must be objects.")
            continue
        path = str(row.get("path", ""))
        if not path or path in by_path:
            _finding(findings, "prompt_load_node_duplicate", path)
        by_path[path] = row
        if check_files:
            source = ROOT / path
            if not source.is_file():
                _finding(findings, "prompt_load_file_missing", path)
            elif row.get("sha256") != _sha256(source) or row.get("bytes") != source.stat().st_size:
                _finding(findings, "prompt_load_file_stale", path)

    routes = graph.get("routes")
    routes = routes if isinstance(routes, list) else []
    route_by_target: dict[str, Mapping[str, Any]] = {}
    expected_conditional_names = {
        "references/native-route-protocol.md",
        "references/native-depth-and-purpose.md",
        "references/template-pack-routing.md",
    }
    for route_row in routes:
        if not isinstance(route_row, Mapping):
            _finding(findings, "prompt_load_route_invalid", "Routes must be objects.")
            continue
        target = str(route_row.get("target_skill_id", ""))
        if target in route_by_target:
            _finding(findings, "prompt_load_route_duplicate", target)
        route_by_target[target] = route_row
        if target not in EXPECTED:
            _finding(findings, "prompt_load_foreign_route", target)
            continue
        owner, native_route, _ = EXPECTED[target]
        if route_row.get("native_owner_id") != owner or route_row.get("native_route_id") != native_route:
            _finding(findings, "prompt_load_route_owner_wrong", target)
        expected_role = "composite" if target == "physicsguard-ai-debugging" else "direct"
        if route_row.get("route_role") != expected_role:
            _finding(findings, "prompt_load_route_role_wrong", target)
        if route_row.get("broad_route_prerequisite") is not False:
            _finding(findings, "broad_route_prerequisite_present", target)
        fixture = route_row.get("selection_fixture")
        if not isinstance(fixture, Mapping) or fixture.get("expected_skill_id") != target:
            _finding(findings, "broad_route_captures_direct_request", target)
        initial_paths = [str(value) for value in route_row.get("initial_paths", [])]
        expected_initial = [
            f"skill/{target}/agents/openai.yaml",
            f"skill/{target}/SKILL.md",
            f"skill/{target}/references/route-capsule.json",
        ]
        if initial_paths != expected_initial:
            _finding(findings, "prompt_initial_inventory_wrong", target)
        conditional = route_row.get("conditional_references")
        conditional = conditional if isinstance(conditional, list) else []
        conditional_paths = {str(row.get("path", "")) for row in conditional if isinstance(row, Mapping)}
        if conditional_paths != expected_conditional_names:
            _finding(findings, "conditional_reference_inventory_wrong", target)
        if set(initial_paths) & {
            f"skill/{target}/{value}" for value in conditional_paths
        }:
            _finding(findings, "eager_all_references", target)
        if int(route_row.get("initial_bytes", -1)) > int(graph.get("max_initial_route_bytes", -1)):
            _finding(findings, "initial_route_budget_exceeded", target)
        if set(map(str, route_row.get("deep_capabilities", []))) != REQUIRED_DEEP_CAPABILITIES:
            _finding(findings, "deep_capability_unreachable", target)
        for reference in conditional:
            if not isinstance(reference, Mapping):
                continue
            relative = str(reference.get("path", ""))
            if not relative.startswith("references/") or ".." in Path(relative).parts:
                _finding(findings, "conditional_reference_path_invalid", f"{target}:{relative}")
                continue
            full = f"skill/{target}/{relative}"
            node = by_path.get(full)
            if node is None:
                _finding(findings, "conditional_reference_undeclared", full)
            elif reference.get("sha256") != node.get("sha256"):
                _finding(findings, "conditional_reference_hash_stale", full)
            if relative == "references/native-depth-and-purpose.md" and not REQUIRED_DEEP_CAPABILITIES <= set(
                map(str, reference.get("required_for", []))
            ):
                _finding(findings, "deep_capability_unreachable", target)
            if check_files:
                source = ROOT / full
                if not source.is_file():
                    _finding(findings, "conditional_reference_missing", full)
                elif reference.get("sha256") != _sha256(source):
                    _finding(findings, "conditional_reference_hash_stale", full)
        if check_files:
            capsule_path = ROOT / f"skill/{target}/references/route-capsule.json"
            if capsule_path.is_file():
                capsule = json.loads(capsule_path.read_text(encoding="utf-8"))
                if capsule.get("schema_version") != ROUTE_CAPSULE_SCHEMA:
                    _finding(findings, "route_capsule_schema_wrong", target)
                if (
                    capsule.get("target_skill_id") != target
                    or capsule.get("native_owner_id") != owner
                    or capsule.get("native_route_id") != native_route
                    or capsule.get("route_role") != expected_role
                ):
                    _finding(findings, "route_capsule_identity_wrong", target)
                skill_path = ROOT / f"skill/{target}/SKILL.md"
                if capsule.get("entry_prompt_sha256") != _sha256(skill_path):
                    _finding(findings, "route_capsule_prompt_stale", target)
                prompt = skill_path.read_text(encoding="utf-8")
                if skill_path.stat().st_size > int(graph.get("max_skill_entry_bytes", -1)):
                    _finding(findings, "skill_entry_budget_exceeded", target)
                if "BEGIN MANAGED VALIDATED TEMPLATE PACK" in prompt or "BEGIN MANAGED PURPOSE AND BLOCKABILITY" in prompt:
                    _finding(findings, "eager_managed_protocol_in_entry", target)
                depth = (ROOT / f"skill/{target}/references/native-depth-and-purpose.md").read_text(encoding="utf-8")
                required_text = (
                    "exactly six families",
                    "Freeze the prediction before observation",
                    "model_miss",
                    "one independent holdout receipt",
                    "one predictive-rollout receipt",
                    "model_closed_for_task",
                )
                if any(value not in depth for value in required_text):
                    _finding(findings, "deep_capability_text_missing", target)

    if set(route_by_target) != set(EXPECTED) or len(routes) != len(EXPECTED):
        _finding(findings, "prompt_load_route_inventory_wrong", "Exactly ten routes are required.")
    expected_node_paths = {
        path
        for target in EXPECTED
        for path in (
            f"skill/{target}/agents/openai.yaml",
            f"skill/{target}/SKILL.md",
            f"skill/{target}/references/route-capsule.json",
            f"skill/{target}/references/native-route-protocol.md",
            f"skill/{target}/references/native-depth-and-purpose.md",
            f"skill/{target}/references/template-pack-routing.md",
        )
    }
    if set(by_path) != expected_node_paths:
        _finding(findings, "prompt_load_node_inventory_wrong", "Exactly six prompt artifacts per skill are required.")
    return {
        "artifact_kind": "physicsguard_skill_prompt_load_graph_check",
        "structure_status": "pass" if not findings else "blocked",
        "route_count": len(route_by_target),
        "findings": findings,
        "claim_boundary": "This checks current prompt identities, routing, loading, and deep-capability reachability only; it does not prove future AI behavior.",
    }


def prompt_load_known_bad_results(graph: Mapping[str, Any]) -> dict[str, str]:
    cases: dict[str, dict[str, Any]] = {}
    wrong_owner = copy.deepcopy(graph)
    wrong_owner["routes"][0]["native_owner_id"] = "physicsguard.foreign"
    cases["wrong_route_owner"] = wrong_owner
    broad_capture = copy.deepcopy(graph)
    direct = next(row for row in broad_capture["routes"] if row["route_role"] == "direct")
    direct["selection_fixture"]["expected_skill_id"] = "physicsguard-ai-debugging"
    cases["broad_route_captures_direct_request"] = broad_capture
    eager = copy.deepcopy(graph)
    route = eager["routes"][0]
    route["initial_paths"].append(
        f"skill/{route['target_skill_id']}/references/native-depth-and-purpose.md"
    )
    cases["eager_all_references"] = eager
    missing = copy.deepcopy(graph)
    missing["routes"][0]["conditional_references"] = missing["routes"][0]["conditional_references"][1:]
    cases["conditional_reference_missing"] = missing
    cross_skill = copy.deepcopy(graph)
    source = cross_skill["routes"][0]
    other = cross_skill["routes"][1]["target_skill_id"]
    source["conditional_references"][0]["path"] = f"../{other}/references/native-route-protocol.md"
    cases["undeclared_or_cross_skill_reference"] = cross_skill
    stale = copy.deepcopy(graph)
    stale["routes"][0]["conditional_references"][0]["sha256"] = "0" * 64
    cases["reference_hash_stale"] = stale
    shallow = copy.deepcopy(graph)
    shallow["routes"][0]["deep_capabilities"].remove("independent_holdout")
    cases["deep_capability_unreachable"] = shallow
    stale_toolchain = copy.deepcopy(graph)
    stale_toolchain["toolchain_identity"]["flowguard_version"] = "0.68.1"
    cases["toolchain_identity_stale"] = stale_toolchain
    return {
        name: check_prompt_load_graph(case, check_files=False)["structure_status"]
        for name, case in cases.items()
    }


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
    if (FAMILY_MAINTENANCE_CHECK_ID in check_ids) != (
        target == FAMILY_MAINTENANCE_MEMBER_ID
    ):
        _finding(findings, "family_maintenance_check_cardinality_wrong", target)
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
        task_model_check = f"check:{target}:task-local-model-deepening"
        if (
            depth.get("model_deepening_check_id") != task_model_check
            or task_model_check not in check_ids
        ):
            _finding(findings, "model_deepening_check_binding_wrong", target)
        if depth.get("skillguard_adds_domain_route") is not False:
            _finding(findings, "skillguard_adds_domain_route", target)

    expected_bindings = [
        {
            "binding_id": f"native-check:{target}:{_binding_id_fragment(check_id)}",
            "evidence_source": (
                "physicsguard.family_distribution_authority"
                if check_id == FAMILY_MAINTENANCE_CHECK_ID
                else (
                    "physicsguard.task_local_revision"
                    if check_id.endswith(":task-local-model-deepening")
                    else "physicsguard.guard_model_contract"
                )
            ),
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
        is_task_model = str(check.get("check_id", "")).endswith(
            ":task-local-model-deepening"
        )
        is_family_maintenance = (
            str(check.get("check_id", "")) == FAMILY_MAINTENANCE_CHECK_ID
        )
        expected_entrypoint = (
            ["-m", "pytest"]
            if is_task_model or is_family_maintenance
            else ["-m", "physicsguard.guard_model_contract"]
        )
        if args[:2] != expected_entrypoint:
            _finding(findings, "noncanonical_native_entrypoint", str(check.get("check_id", "")))
        selectors = _path_selectors(check)
        required_modules = (
            set()
            if is_family_maintenance
            else (TASK_MODEL_MODULES if is_task_model else CANONICAL_MODULES)
        )
        if not required_modules <= selectors:
            _finding(findings, "canonical_simulator_input_missing", str(check.get("check_id", "")))
        if is_task_model and not ENTRY_SHARED_GOVERNED_INPUTS <= selectors:
            _finding(findings, "entry_governed_input_missing", str(check.get("check_id", "")))
        if is_task_model and FAMILY_MAINTENANCE_EXCLUSIVE_INPUTS & selectors:
            _finding(
                findings,
                "family_maintenance_leaked_into_member_model_owner",
                str(check.get("check_id", "")),
            )
        if is_family_maintenance and (
            target != FAMILY_MAINTENANCE_MEMBER_ID
            or check.get("execution_owner_id") != FAMILY_MAINTENANCE_OWNER_ID
            or selectors != FAMILY_MAINTENANCE_INPUTS
        ):
            _finding(
                findings,
                "family_maintenance_owner_or_inputs_invalid",
                str(check.get("check_id", "")),
            )
        if any(
            path.endswith("/guard-model/verify.py")
            or path.endswith("/runtime/skill_execution_depth.py")
            for path in selectors
        ):
            _finding(findings, "copied_simulator_input_present", str(check.get("check_id", "")))

    implementation_paths = set(map(str, source.get("implementation_paths", [])))
    if not CANONICAL_MODULES <= implementation_paths:
        _finding(findings, "canonical_simulator_implementation_missing", target)
    if not ENTRY_SHARED_GOVERNED_INPUTS <= implementation_paths:
        _finding(findings, "entry_governed_implementation_missing", target)
    if target == FAMILY_MAINTENANCE_MEMBER_ID:
        if not FAMILY_MAINTENANCE_INPUTS <= implementation_paths:
            _finding(findings, "family_maintenance_implementation_missing", target)
    elif FAMILY_MAINTENANCE_EXCLUSIVE_INPUTS & implementation_paths:
        _finding(findings, "family_maintenance_implementation_duplicated", target)

    projection_consumers = source.get("projection_consumers", [])
    if target == FAMILY_MAINTENANCE_MEMBER_ID:
        projection_is_exact = (
            isinstance(projection_consumers, list)
            and len(projection_consumers) == 1
            and isinstance(projection_consumers[0], Mapping)
            and projection_consumers[0].get("consumer_id")
            == FAMILY_MAINTENANCE_PROJECTION_ID
            and projection_consumers[0].get("kind") == "source_maintenance"
            and _path_selectors(projection_consumers[0])
            == FAMILY_MAINTENANCE_INPUTS
        )
    else:
        projection_is_exact = projection_consumers == []
    if not projection_is_exact:
        _finding(findings, "family_maintenance_projection_wrong", target)

    expected_overrides = [
        {
            "path": f"skill/{target}/.skillguard",
            "role": "contract_schema",
            "install_disposition": "source_only",
            "reason": "author_control_source_only",
        },
        {
            "path": f"skill/{target}/guard-model",
            "role": "test_dev",
            "install_disposition": "source_only",
            "reason": "author_only_guard_contract",
        },
    ]
    if source.get("content_role_overrides") != expected_overrides:
        _finding(findings, "member_author_control_override_drifted", target)
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
    expected_toolchain, authority_error = _current_toolchain_identity_resolution()
    if authority_error is not None:
        _finding(
            findings,
            "toolchain_authority_unresolved",
            authority_error,
        )
    if mesh.get("guard_model_contract") != EXPECTED_GUARD_MODEL:
        _finding(findings, "guard_model_contract_drift", "PhysicsGuard target semantics or proof order drifted.")
    if expected_toolchain is not None and mesh.get("toolchain_identity") != expected_toolchain:
        _finding(findings, "toolchain_identity_stale", str(mesh.get("toolchain_identity", "")))

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
            _finding(findings, "canonical_simulator_authority_wrong", "The five current canonical source modules are required.")
        if simulator.get("copied_editable_implementations_allowed") is not False:
            _finding(findings, "copied_editable_simulator_allowed", "Copied implementations cannot be editable authority.")
        if simulator.get("missing_dependency_behavior") != "fail_visible":
            _finding(findings, "runtime_fallback_allowed", "Missing canonical package must fail visibly.")
        expected_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        if simulator.get("consumer_dependency") != f"physicsguard=={expected_version}":
            _finding(findings, "canonical_simulator_version_stale", str(simulator.get("consumer_dependency", "")))

    entry_loading = mesh.get("entry_loading")
    expected_entry_loading = {
        "route_count": 10,
        "direct_route_count": 9,
        "composite_route_count": 1,
        "composite_route_id": "route:physicsguard-ai-debugging:audit",
        "composite_is_parent": False,
        "route_capsule_schema": ROUTE_CAPSULE_SCHEMA,
        "prompt_load_graph": ".flowguard/physicsguard_skill_prompt_load_graph.json",
        "initial_loading_rule": "selected_metadata_plus_compact_skill_plus_route_capsule_only",
        "conditional_reference_paths": [
            "references/native-route-protocol.md",
            "references/native-depth-and-purpose.md",
            "references/template-pack-routing.md",
        ],
        "maximum_reference_depth": 1,
        "required_deep_capabilities": sorted(REQUIRED_DEEP_CAPABILITIES),
    }
    if not isinstance(entry_loading, Mapping) or any(
        (
            sorted(map(str, entry_loading.get(field, []))) != expected
            if field == "required_deep_capabilities"
            else entry_loading.get(field) != expected
        )
        for field, expected in expected_entry_loading.items()
    ):
        _finding(findings, "entry_loading_model_wrong", "The ten-route narrow-entry model must remain exact.")

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
        "contract-eager-skill-entry-prompts",
    }:
        _finding(findings, "architecture_reduction_inventory_wrong", "All contraction candidates must remain visible.")

    structure = mesh.get("structure_mesh", {})
    if set(map(str, structure.get("target_modules", []))) != {
        "physicsguard.guard_model_contract",
        "physicsguard.skill_execution_depth",
        "physicsguard.schema.task_local_revision",
        "physicsguard.core.task_local_revision",
        "physicsguard.cli",
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
        if not PROMPT_LOAD_GRAPH_PATH.is_file():
            _finding(findings, "prompt_load_graph_missing", PROMPT_LOAD_GRAPH_PATH.name)
        else:
            prompt_report = check_prompt_load_graph(
                json.loads(PROMPT_LOAD_GRAPH_PATH.read_text(encoding="utf-8"))
            )
            findings.extend(
                {
                    "code": f"prompt_load:{row['code']}",
                    "message": row["message"],
                }
                for row in prompt_report["findings"]
            )
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
    stale_toolchain = copy.deepcopy(mesh)
    stale_toolchain["toolchain_identity"]["skillguard_version"] = "0.7.1"
    cases["toolchain_identity_stale"] = stale_toolchain
    return {
        name: check_mesh(case, check_targets=False)["structure_status"]
        for name, case in cases.items()
    }


def main() -> int:
    mesh = json.loads(MESH_PATH.read_text(encoding="utf-8"))
    result = check_mesh(mesh)
    result["known_bads"] = known_bad_results(mesh)
    if PROMPT_LOAD_GRAPH_PATH.is_file():
        result["prompt_load_known_bads"] = prompt_load_known_bad_results(
            json.loads(PROMPT_LOAD_GRAPH_PATH.read_text(encoding="utf-8"))
        )
    else:
        result["prompt_load_known_bads"] = {"prompt_load_graph_missing": "blocked"}
    if any(status != "blocked" for status in result["known_bads"].values()):
        result["structure_status"] = "blocked"
        _finding(result["findings"], "known_bad_not_blocked", "Every declared topology bad case must block.")
    if any(status != "blocked" for status in result["prompt_load_known_bads"].values()):
        result["structure_status"] = "blocked"
        _finding(result["findings"], "prompt_load_known_bad_not_blocked", "Every declared prompt-loading bad case must block.")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["structure_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
