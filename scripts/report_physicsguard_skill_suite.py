"""Report PhysicsGuard maintained-skill structure without authorizing evidence.

This command reads source inventory and contract metadata only.  It does not
load SkillGuard, inspect run/evidence stores, execute checks, read receipts, or
issue a suite closure.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


EXPECTED_SKILLS = (
    "physicsguard-ai-debugging",
    "physicsguard-audit-closure",
    "physicsguard-candidate-model-blueprint",
    "physicsguard-model-dataset-validation",
    "physicsguard-model-library",
    "physicsguard-model-understanding-preflight",
    "physicsguard-project-adoption",
    "physicsguard-project-evidence-registry",
    "physicsguard-signal-mapping-review",
    "physicsguard-test-file-contract-review",
)
UNIT_ID = "unit:physicsguard-family"
CLAIM_BOUNDARY = (
    "This report proves only the ten-member source inventory, native-owner "
    "partition, and declared-check identity shape. It executes no check, reads "
    "or consumes no receipt, and issues no SkillGuard or PhysicsGuard closure."
)


class SuiteStructureError(ValueError):
    """Fail-closed source-structure error."""


def _read_object(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SuiteStructureError(f"{code}:{path.as_posix()}") from exc
    if not isinstance(value, dict):
        raise SuiteStructureError(f"{code}:{path.as_posix()}")
    return value


def _member_row(
    repository_root: Path,
    manifest_row: Mapping[str, Any],
    mesh_row: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    findings: list[str] = []
    skill_id = str(manifest_row.get("skill_id", ""))
    skill_path = str(manifest_row.get("skill_path", ""))
    expected_path = f"skill/{skill_id}"
    if skill_path != expected_path:
        findings.append("author_skill_path_mismatch")
    source = _read_object(
        repository_root / expected_path / ".skillguard" / "contract-source.json",
        "member_contract_unreadable",
    )
    checks = [row for row in source.get("checks", []) if isinstance(row, Mapping)]
    check_ids = [str(row.get("check_id", "")) for row in checks]
    semantic_ids = [str(row.get("semantic_check_id", "")) for row in checks]
    owner_ids = [str(row.get("execution_owner_id", "")) for row in checks]
    subject_ids = [str(row.get("evidence_subject_id", "")) for row in checks]
    if source.get("skill_id") != skill_id:
        findings.append("contract_skill_id_mismatch")
    if source.get("maintenance_unit_id") != UNIT_ID:
        findings.append("contract_foreign_unit")
    if source.get("member_skill_ids") != list(EXPECTED_SKILLS):
        findings.append("contract_member_inventory_mismatch")
    if any(len(set(rows)) != len(rows) for rows in (check_ids, semantic_ids, owner_ids, subject_ids)):
        findings.append("contract_check_identity_not_unique")
    if any(row.get("maintenance_unit_id") != UNIT_ID for row in checks):
        findings.append("check_foreign_unit")
    if any(row.get("member_skill_id") != skill_id for row in checks):
        findings.append("check_member_mismatch")
    if manifest_row.get("maintenance_unit_id") != UNIT_ID:
        findings.append("author_manifest_foreign_unit")
    if source.get("native_route_owner") != manifest_row.get("native_owner_id"):
        findings.append("native_owner_mismatch")
    if mesh_row.get("native_owner_id") != source.get("native_route_owner"):
        findings.append("mesh_native_owner_mismatch")
    if mesh_row.get("native_route_id") != source.get("default_route_id"):
        findings.append("mesh_native_route_mismatch")
    if mesh_row.get("declared_check_count") != len(checks):
        findings.append("mesh_check_count_mismatch")
    return (
        {
            "skill_id": skill_id,
            "maintenance_unit_id": UNIT_ID,
            "native_owner_id": source.get("native_route_owner"),
            "native_route_id": source.get("default_route_id"),
            "declared_check_count": len(checks),
            "semantic_check_count": len(set(semantic_ids)),
            "execution_owner_count": len(set(owner_ids)),
            "evidence_subject_count": len(set(subject_ids)),
        },
        findings,
    )


def build_report(repository_root: Path) -> dict[str, Any]:
    manifest = _read_object(
        repository_root / ".skillguard" / "author-project.json",
        "author_manifest_unreadable",
    )
    mesh = _read_object(
        repository_root / ".flowguard" / "physicsguard_skill_suite_mesh.json",
        "suite_mesh_unreadable",
    )
    findings: list[str] = []
    if manifest.get("repository_role") != "skill_maintainer_source":
        findings.append("author_repository_role_wrong")
    managed = [row for row in manifest.get("managed_skills", []) if isinstance(row, Mapping)]
    managed_by_id = {str(row.get("skill_id", "")): row for row in managed}
    if tuple(sorted(managed_by_id)) != EXPECTED_SKILLS or len(managed) != len(EXPECTED_SKILLS):
        findings.append("author_member_inventory_mismatch")
    mesh_rows = [row for row in mesh.get("children", []) if isinstance(row, Mapping)]
    mesh_by_id = {str(row.get("target_skill_id", "")): row for row in mesh_rows}
    if tuple(sorted(mesh_by_id)) != EXPECTED_SKILLS or len(mesh_rows) != len(EXPECTED_SKILLS):
        findings.append("mesh_member_inventory_mismatch")
    boundary = mesh.get("maintenance_boundary")
    if not isinstance(boundary, Mapping) or any(
        boundary.get(field) is not False
        for field in (
            "suite_summary_authoritative",
            "suite_summary_may_execute_checks",
            "suite_summary_may_consume_receipts",
            "suite_summary_may_issue_closure",
        )
    ):
        findings.append("mesh_summary_authority_not_false")

    retired_paths = (
        ".flowguard/skillguard-parent",
        ".flowguard/physicsguard_suite_parent_inventory.json",
        "scripts/generate_physicsguard_suite_parent_contract.py",
        "scripts/verify_physicsguard_suite_parent.py",
    )
    for relative in retired_paths:
        if (repository_root / relative).exists():
            findings.append(f"retired_parent_authority_present:{relative}")

    members: list[dict[str, Any]] = []
    for skill_id in EXPECTED_SKILLS:
        manifest_row = managed_by_id.get(skill_id)
        mesh_row = mesh_by_id.get(skill_id)
        if manifest_row is None or mesh_row is None:
            continue
        row, member_findings = _member_row(repository_root, manifest_row, mesh_row)
        members.append(row)
        findings.extend(f"{skill_id}:{finding}" for finding in member_findings)

    return {
        "artifact_kind": "physicsguard_skill_suite_structure_report",
        "authoritative": False,
        "structure_status": "pass" if not findings else "blocked",
        "maintenance_unit_id": UNIT_ID,
        "member_count": len(members),
        "declared_check_count": sum(int(row["declared_check_count"]) for row in members),
        "members": members,
        "findings": findings,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = build_report(Path(args.repository_root).resolve())
    except SuiteStructureError as exc:
        result = {
            "artifact_kind": "physicsguard_skill_suite_structure_report",
            "authoritative": False,
            "structure_status": "blocked",
            "maintenance_unit_id": UNIT_ID,
            "member_count": 0,
            "declared_check_count": 0,
            "members": [],
            "findings": [str(exc)],
            "claim_boundary": CLAIM_BOUNDARY,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["structure_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
