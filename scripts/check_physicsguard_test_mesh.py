"""Read-only static audit for the PhysicsGuard SkillGuard TestMesh definition.

This checker proves that the one unit-level manifest can select the exact
existing owner topology from every member's current compiled contract.  It
does not claim a run, execute an owner, aggregate receipts, or publish a
terminal validation result.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill"
GENERATOR_PATH = ROOT / "scripts" / "upgrade_purpose_contracts.py"
EXPECTED_UNIT_ID = "unit:physicsguard-family"
EXPECTED_OWNER_COUNTS = {
    "physicsguard-ai-debugging": 9,
    "physicsguard-audit-closure": 10,
    "physicsguard-candidate-model-blueprint": 8,
    "physicsguard-model-dataset-validation": 9,
    "physicsguard-model-library": 8,
    "physicsguard-model-understanding-preflight": 8,
    "physicsguard-project-adoption": 8,
    "physicsguard-project-evidence-registry": 8,
    "physicsguard-signal-mapping-review": 8,
    "physicsguard-test-file-contract-review": 9,
}
EXPECTED_OWNER_COUNT = 85
EXPECTED_HEALTH_FIELDS = {
    "ambiguous_role_paths",
    "dependency_parse_errors",
    "duplicate_owner_ids",
    "invalid_dependency_edges",
    "owner_cycles",
    "unmapped_paths",
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path.relative_to(ROOT).as_posix()}")
    return value


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "physicsguard_purpose_contract_generator_for_test_mesh", GENERATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise ValueError("generator_import_spec_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record(
    findings: list[dict[str, str]], condition: bool, code: str, detail: str
) -> None:
    if not condition:
        findings.append({"code": code, "detail": detail})


def _rows_by_id(
    rows: object, key: str, findings: list[dict[str, str]], scope: str
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(rows, list):
        findings.append({"code": f"{scope}_rows_invalid", "detail": key})
        return {}
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            findings.append({"code": f"{scope}_row_invalid", "detail": key})
            continue
        row_id = str(row.get(key, ""))
        if not row_id or row_id in indexed:
            findings.append(
                {"code": f"{scope}_id_missing_or_duplicate", "detail": row_id}
            )
            continue
        indexed[row_id] = row
    return indexed


def _selector_paths(row: Mapping[str, Any]) -> set[str]:
    selectors = row.get("input_selectors", [])
    if not isinstance(selectors, list):
        return set()
    return {
        str(selector.get("path", ""))
        for selector in selectors
        if isinstance(selector, Mapping)
        and selector.get("kind") == "path"
        and selector.get("path")
    }


def _component_paths(
    plan: Mapping[str, Any], findings: list[dict[str, str]], skill_id: str
) -> tuple[dict[str, Mapping[str, Any]], dict[str, str]]:
    components = _rows_by_id(
        plan.get("components"), "component_id", findings, f"{skill_id}:components"
    )
    path_to_component: dict[str, str] = {}
    for component_id, component in components.items():
        member_paths = component.get("member_paths", [])
        if not isinstance(member_paths, list):
            findings.append(
                {
                    "code": "component_member_paths_invalid",
                    "detail": f"{skill_id}:{component_id}",
                }
            )
            continue
        for path_value in member_paths:
            path = str(path_value)
            if path in path_to_component:
                findings.append(
                    {
                        "code": "component_path_duplicated",
                        "detail": f"{skill_id}:{path}",
                    }
                )
            path_to_component[path] = component_id
    return components, path_to_component


def _closure_owner_ids(
    compiled: Mapping[str, Any],
    owners: Mapping[str, Mapping[str, Any]],
    findings: list[dict[str, str]],
    skill_id: str,
) -> tuple[set[str], set[str]]:
    profiles = _rows_by_id(
        compiled.get("closure_profiles"),
        "profile_id",
        findings,
        f"{skill_id}:closure_profiles",
    )
    profile = profiles.get("enforced")
    if profile is None:
        findings.append(
            {"code": "enforced_closure_missing", "detail": skill_id}
        )
        return set(), set()
    obligations = _rows_by_id(
        compiled.get("obligations"),
        "obligation_id",
        findings,
        f"{skill_id}:obligations",
    )
    checks = _rows_by_id(
        compiled.get("checks"), "check_id", findings, f"{skill_id}:checks"
    )
    required_checks: set[str] = set()
    required_obligations = profile.get("required_obligation_ids", [])
    if not isinstance(required_obligations, list) or not required_obligations:
        findings.append(
            {"code": "enforced_obligations_invalid", "detail": skill_id}
        )
        return set(), set()
    for obligation_value in required_obligations:
        obligation_id = str(obligation_value)
        obligation = obligations.get(obligation_id)
        if obligation is None:
            findings.append(
                {
                    "code": "closure_obligation_unknown",
                    "detail": f"{skill_id}:{obligation_id}",
                }
            )
            continue
        check_ids = obligation.get("required_check_ids", [])
        if not isinstance(check_ids, list) or not check_ids:
            findings.append(
                {
                    "code": "closure_obligation_check_empty",
                    "detail": f"{skill_id}:{obligation_id}",
                }
            )
            continue
        required_checks.update(str(value) for value in check_ids)

    selected: set[str] = set()
    for check_id in required_checks:
        check = checks.get(check_id)
        if check is None:
            findings.append(
                {
                    "code": "closure_check_unknown",
                    "detail": f"{skill_id}:{check_id}",
                }
            )
            continue
        selected.add(str(check.get("execution_owner_id", "")))
    pending = list(selected)
    while pending:
        owner_id = pending.pop()
        owner = owners.get(owner_id)
        if owner is None:
            findings.append(
                {
                    "code": "closure_owner_unknown",
                    "detail": f"{skill_id}:{owner_id}",
                }
            )
            continue
        dependencies = owner.get("depends_on_owner_ids", [])
        if not isinstance(dependencies, list):
            findings.append(
                {
                    "code": "owner_dependencies_invalid",
                    "detail": f"{skill_id}:{owner_id}",
                }
            )
            continue
        for dependency_value in dependencies:
            dependency = str(dependency_value)
            if dependency not in selected:
                selected.add(dependency)
                pending.append(dependency)
    selected.discard("")
    return required_checks, selected


def _check_dependency_order(
    owners: Mapping[str, Mapping[str, Any]],
    findings: list[dict[str, str]],
    skill_id: str,
) -> None:
    pending = set(owners)
    completed: set[str] = set()
    while pending:
        ready = sorted(
            owner_id
            for owner_id in pending
            if set(
                str(value)
                for value in owners[owner_id].get("depends_on_owner_ids", [])
            )
            <= completed
        )
        if not ready:
            findings.append(
                {
                    "code": "owner_dependency_cycle_or_foreign_dependency",
                    "detail": f"{skill_id}:{','.join(sorted(pending))}",
                }
            )
            return
        pending.difference_update(ready)
        completed.update(ready)


def audit(repository_root: Path = ROOT) -> dict[str, Any]:
    global ROOT, SKILL_ROOT, GENERATOR_PATH
    ROOT = repository_root.resolve()
    SKILL_ROOT = ROOT / "skill"
    GENERATOR_PATH = ROOT / "scripts" / "upgrade_purpose_contracts.py"
    findings: list[dict[str, str]] = []
    generator = _load_generator()
    expected_manifest = generator.expected_unit_test_mesh_manifest()
    manifest_path = ROOT / ".skillguard" / "test-mesh.json"
    manifest = _load_json(manifest_path)
    _record(
        findings,
        manifest == expected_manifest,
        "unit_test_mesh_generator_parity_failed",
        ".skillguard/test-mesh.json",
    )
    all_mesh_paths = sorted(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("test-mesh.json")
        if ".skillguard" in path.parts and ".git" not in path.parts
    )
    _record(
        findings,
        all_mesh_paths == [".skillguard/test-mesh.json"],
        "unit_test_mesh_authority_not_unique",
        ",".join(all_mesh_paths),
    )

    expected_members = sorted(generator.TARGETS)
    _record(
        findings,
        expected_members == sorted(EXPECTED_OWNER_COUNTS),
        "generator_member_inventory_drifted",
        ",".join(expected_members),
    )
    maintenance_paths = set(generator.FAMILY_MAINTENANCE_INPUTS)
    maintenance_exclusive_paths = maintenance_paths - set(
        generator.ENTRY_SHARED_GOVERNED_INPUTS
    )
    maintenance_projection_id = generator.FAMILY_MAINTENANCE_PROJECTION_ID
    maintenance_member_id = generator.FAMILY_MAINTENANCE_MEMBER_ID
    maintenance_check_id = generator.FAMILY_MAINTENANCE_CHECK_ID
    maintenance_owner_id = generator.FAMILY_MAINTENANCE_OWNER_ID
    all_owner_ids: set[str] = set()
    all_check_ids: set[str] = set()
    family_maintenance_owner_ids: set[str] = set()
    owner_counts: dict[str, int] = {}
    member_results: list[dict[str, Any]] = []

    for skill_id in expected_members:
        control_root = SKILL_ROOT / skill_id / ".skillguard"
        source = _load_json(control_root / "contract-source.json")
        compiled = _load_json(control_root / "compiled-contract.json")
        check_manifest = _load_json(control_root / "check-manifest.json")

        for label, value in (
            ("source", source),
            ("compiled", compiled),
            ("check_manifest", check_manifest),
        ):
            _record(
                findings,
                value.get("skill_id") == skill_id,
                "member_skill_identity_mismatch",
                f"{skill_id}:{label}",
            )
            _record(
                findings,
                value.get("maintenance_unit_id") == EXPECTED_UNIT_ID,
                "maintenance_unit_identity_mismatch",
                f"{skill_id}:{label}",
            )
            _record(
                findings,
                value.get("member_skill_ids") == expected_members,
                "maintenance_member_inventory_mismatch",
                f"{skill_id}:{label}",
            )

        _record(
            findings,
            check_manifest.get("contract_hash") == compiled.get("contract_hash"),
            "manifest_contract_hash_mismatch",
            skill_id,
        )
        _record(
            findings,
            check_manifest.get("check_declarations_hash")
            == compiled.get("check_declarations_hash"),
            "manifest_check_hash_mismatch",
            skill_id,
        )

        source_checks = _rows_by_id(
            source.get("checks"), "check_id", findings, f"{skill_id}:source_checks"
        )
        compiled_checks = _rows_by_id(
            compiled.get("checks"),
            "check_id",
            findings,
            f"{skill_id}:compiled_checks",
        )
        manifest_checks = _rows_by_id(
            check_manifest.get("checks"),
            "check_id",
            findings,
            f"{skill_id}:manifest_checks",
        )
        _record(
            findings,
            set(source_checks) == set(compiled_checks) == set(manifest_checks),
            "check_inventory_projection_mismatch",
            skill_id,
        )
        for check_id, compiled_check in compiled_checks.items():
            manifest_check = manifest_checks.get(check_id)
            source_check = source_checks.get(check_id)
            _record(
                findings,
                manifest_check == compiled_check,
                "compiled_manifest_check_projection_mismatch",
                f"{skill_id}:{check_id}",
            )
            if source_check is None:
                continue
            for field in (
                "maintenance_unit_id",
                "member_skill_id",
                "evidence_subject_id",
                "execution_owner_id",
                "semantic_check_id",
                "evidence_domain_id",
            ):
                _record(
                    findings,
                    compiled_check.get(field) == source_check.get(field),
                    "source_compiled_check_identity_mismatch",
                    f"{skill_id}:{check_id}:{field}",
                )
            _record(
                findings,
                compiled_check.get("maintenance_unit_id") == EXPECTED_UNIT_ID
                and compiled_check.get("member_skill_id") == skill_id,
                "check_unit_member_projection_invalid",
                f"{skill_id}:{check_id}",
            )

        plan = compiled.get("content_impact_plan")
        if not isinstance(plan, Mapping):
            findings.append(
                {"code": "content_impact_plan_missing", "detail": skill_id}
            )
            continue
        _record(
            findings,
            plan.get("schema_version") == "skillguard.content_impact_plan.current",
            "content_impact_plan_schema_invalid",
            skill_id,
        )
        _record(
            findings,
            plan.get("unknown_mapping_disposition") == "block",
            "unknown_mapping_not_blocked",
            skill_id,
        )
        health = plan.get("health")
        health_pass = (
            isinstance(health, Mapping)
            and set(health) == EXPECTED_HEALTH_FIELDS
            and all(isinstance(health[key], list) and not health[key] for key in health)
        )
        _record(
            findings,
            health_pass,
            "content_impact_plan_unhealthy",
            skill_id,
        )
        _record(
            findings,
            check_manifest.get("content_impact_plan") == plan,
            "manifest_content_impact_plan_mismatch",
            skill_id,
        )

        owners = _rows_by_id(
            plan.get("owners"),
            "execution_owner_id",
            findings,
            f"{skill_id}:owners",
        )
        projections = _rows_by_id(
            plan.get("check_projections"),
            "check_id",
            findings,
            f"{skill_id}:check_projections",
        )
        _record(
            findings,
            set(projections) == set(compiled_checks),
            "check_projection_inventory_mismatch",
            skill_id,
        )
        for check_id, projection in projections.items():
            check = compiled_checks.get(check_id, {})
            for field in (
                "semantic_check_id",
                "evidence_domain_id",
                "execution_owner_id",
                "projection_declaration_hash",
            ):
                _record(
                    findings,
                    projection.get(field) == check.get(field),
                    "check_projection_identity_mismatch",
                    f"{skill_id}:{check_id}:{field}",
                )

        required_checks, selected_owners = _closure_owner_ids(
            compiled, owners, findings, skill_id
        )
        _record(
            findings,
            required_checks == set(compiled_checks),
            "enforced_closure_not_check_complete",
            skill_id,
        )
        _record(
            findings,
            selected_owners == set(owners),
            "enforced_closure_not_owner_complete",
            skill_id,
        )
        _check_dependency_order(owners, findings, skill_id)
        _record(
            findings,
            all(
                isinstance(owner.get("check_ids"), list)
                and len(owner["check_ids"]) == 1
                and owner["check_ids"][0] in compiled_checks
                for owner in owners.values()
            ),
            "owner_check_cardinality_not_exact",
            skill_id,
        )

        projection_consumers = _rows_by_id(
            plan.get("projection_consumers"),
            "consumer_id",
            findings,
            f"{skill_id}:projection_consumers",
        )
        source_projection_rows = _rows_by_id(
            source.get("projection_consumers"),
            "consumer_id",
            findings,
            f"{skill_id}:source_projection_consumers",
        )
        source_maintenance_projection = source_projection_rows.get(
            maintenance_projection_id
        )
        components, path_to_component = _component_paths(plan, findings, skill_id)
        maintenance_component_ids = {
            path_to_component.get(path, "") for path in maintenance_paths
        }
        compiled_maintenance_projection = projection_consumers.get(
            maintenance_projection_id
        )
        maintenance_check = compiled_checks.get(maintenance_check_id)
        maintenance_owner = owners.get(maintenance_owner_id)
        implementation_paths = set(map(str, source.get("implementation_paths", [])))
        if skill_id == maintenance_member_id:
            _record(
                findings,
                source_maintenance_projection is not None
                and source_maintenance_projection.get("kind") == "source_maintenance"
                and _selector_paths(source_maintenance_projection) == maintenance_paths,
                "source_maintenance_projection_invalid",
                skill_id,
            )
            _record(
                findings,
                "" not in maintenance_component_ids,
                "maintenance_component_missing",
                skill_id,
            )
            _record(
                findings,
                compiled_maintenance_projection is not None
                and compiled_maintenance_projection.get("kind")
                == "source_maintenance"
                and set(
                    compiled_maintenance_projection.get("input_component_ids", [])
                )
                == maintenance_component_ids,
                "compiled_maintenance_projection_invalid",
                skill_id,
            )
            _record(
                findings,
                maintenance_check is not None
                and maintenance_check.get("execution_owner_id")
                == maintenance_owner_id
                and _selector_paths(maintenance_check) == maintenance_paths,
                "family_maintenance_check_invalid",
                skill_id,
            )
            _record(
                findings,
                maintenance_owner is not None
                and maintenance_owner.get("check_ids") == [maintenance_check_id],
                "family_maintenance_owner_invalid",
                skill_id,
            )
            family_maintenance_owner_ids.update(
                owner_id
                for owner_id in owners
                if owner_id == maintenance_owner_id
            )
            for path in sorted(maintenance_exclusive_paths):
                component = components.get(path_to_component.get(path, ""), {})
                consumers = set(
                    str(value) for value in component.get("consumer_ids", [])
                )
                _record(
                    findings,
                    component.get("install_disposition") == "source_only"
                    and maintenance_projection_id in consumers
                    and maintenance_owner_id in consumers
                    and not {
                        value
                        for value in consumers
                        if value.startswith("owner:")
                        and value != maintenance_owner_id
                    },
                    "maintenance_component_role_or_owner_invalid",
                    f"{skill_id}:{path}",
                )
        else:
            _record(
                findings,
                source_maintenance_projection is None
                and compiled_maintenance_projection is None
                and maintenance_check is None
                and maintenance_owner is None,
                "family_maintenance_authority_duplicated",
                skill_id,
            )
            _record(
                findings,
                maintenance_exclusive_paths.isdisjoint(implementation_paths),
                "family_maintenance_inputs_duplicated",
                skill_id,
            )

        task_model_check = compiled_checks.get(
            f"check:{skill_id}:task-local-model-deepening", {}
        )
        task_model_selectors = _selector_paths(task_model_check)
        _record(
            findings,
            set(generator.ENTRY_SHARED_GOVERNED_INPUTS)
            <= task_model_selectors
            and maintenance_exclusive_paths.isdisjoint(
                task_model_selectors
            ),
            "member_shared_governed_inputs_drifted",
            skill_id,
        )
        route_blueprint_paths = set(
            generator.BLUEPRINT_ROUTE_INPUTS.get(skill_id, ())
        )
        route_test_paths = {
            path
            for path in route_blueprint_paths
            if path.startswith("tests/") and path.endswith(".py")
        }
        task_model_args = [str(value) for value in task_model_check.get("args", [])]
        try:
            keyword_expression = task_model_args[task_model_args.index("-k") + 1]
        except (ValueError, IndexError):
            keyword_expression = ""
        _record(
            findings,
            route_blueprint_paths <= task_model_selectors
            and route_blueprint_paths <= implementation_paths
            and route_test_paths <= set(task_model_args)
            and all(Path(path).stem in keyword_expression for path in route_test_paths),
            "route_blueprint_owner_mapping_drifted",
            skill_id,
        )
        _record(
            findings,
            source.get("content_role_overrides")
            == generator._content_role_overrides(skill_id),
            "member_author_control_override_drifted",
            skill_id,
        )

        owner_counts[skill_id] = len(owners)
        _record(
            findings,
            len(owners) == EXPECTED_OWNER_COUNTS.get(skill_id),
            "member_owner_count_drifted",
            f"{skill_id}:{len(owners)}",
        )
        duplicate_owners = all_owner_ids & set(owners)
        duplicate_checks = all_check_ids & set(compiled_checks)
        _record(
            findings,
            not duplicate_owners,
            "cross_member_owner_duplicate",
            f"{skill_id}:{','.join(sorted(duplicate_owners))}",
        )
        _record(
            findings,
            not duplicate_checks,
            "cross_member_check_duplicate",
            f"{skill_id}:{','.join(sorted(duplicate_checks))}",
        )
        all_owner_ids.update(owners)
        all_check_ids.update(compiled_checks)
        member_results.append(
            {
                "member_skill_id": skill_id,
                "check_owner_count": len(owners),
                "closure_profile_id": "enforced",
                "plan_only_static_eligibility": "eligible" if not findings else "pending",
            }
        )

    _record(
        findings,
        len(all_owner_ids) == EXPECTED_OWNER_COUNT
        and len(all_check_ids) == EXPECTED_OWNER_COUNT,
        "unit_owner_or_check_total_drifted",
        f"owners={len(all_owner_ids)};checks={len(all_check_ids)}",
    )
    _record(
        findings,
        family_maintenance_owner_ids == {maintenance_owner_id},
        "family_maintenance_owner_not_unique",
        ",".join(sorted(family_maintenance_owner_ids)),
    )

    status = "pass" if not findings else "blocked"
    for row in member_results:
        row["plan_only_static_eligibility"] = (
            "eligible" if status == "pass" else "blocked"
        )
    return {
        "schema_version": "physicsguard.skillguard_test_mesh_static_audit.v1",
        "status": status,
        "maintenance_unit_id": EXPECTED_UNIT_ID,
        "mesh_id": manifest.get("mesh_id", ""),
        "member_count": len(expected_members),
        "check_owner_count": len(all_owner_ids),
        "execution_count": 0,
        "plan_only_execution_status": "not_run",
        "member_results": member_results,
        "source_maintenance_projection": {
            "consumer_id": maintenance_projection_id,
            "paths": sorted(maintenance_paths),
            "semantic_owner_selection": [maintenance_owner_id],
            "required_next_action_on_change": (
                "regenerate the exact current member sources, compile their projections, "
                "run the one family distribution owner plus only the affected domain "
                "owners, then freeze current member-specific plan_only plans"
            ),
        },
        "family_maintenance_impact": {
            "direct_semantic_owner_ids": sorted(family_maintenance_owner_ids),
            "disposition": (
                "one direct-current family owner validates generation, distribution, "
                "installation, currentness, and readiness; member domain owners are "
                "selected only by their exact changed components"
            ),
        },
        "unknown_mapping_disposition": "block",
        "findings": findings,
        "claim_boundary": (
            "A pass proves only static current-format eligibility for ten "
            "member-specific plan_only freezes covering 84 domain/model owners and "
            "one family distribution owner. "
            "No run was claimed, no plan_only was executed, no owner process was "
            "launched, and no execution or aggregation receipt was created."
        ),
    }


def main() -> int:
    result = audit(ROOT)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
