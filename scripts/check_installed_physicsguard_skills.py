"""Read-only audit of installed PhysicsGuard consumer projections.

PhysicsGuard owns only the exact ten-member suite inventory.  Consumer file
selection, release identity, author-control exclusion, symlink rejection, and
installed-tree auditing belong solely to the current installed SkillGuard API.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from physicsguard_skill_install_authority import (  # noqa: E402
    DEFAULT_CODEX_HOME,
    DEFAULT_SKILLGUARD_ROOT,
    PHYSICSGUARD_SKILL_IDS,
    SkillGuardConsumerApi,
    load_member_contract,
    load_skillguard_consumer_api,
    path_is_link_or_reparse,
    physicsguard_member_roots,
)


DEFAULT_INSTALLED_ROOT = DEFAULT_CODEX_HOME / "skills"
AUDIT_SCHEMA_VERSION = "physicsguard.installed_skill_audit.v1"
AUDIT_ARTIFACT_KIND = "physicsguard_installed_skill_audit"
FORBIDDEN_INSTALLED_SKILLS = {
    "physicsguard-database-adoption",
    "physicsguard-database-catalog",
    "physicsguard-database-maintenance",
    "physicsguard-database-project-intake",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-root", type=Path, default=DEFAULT_INSTALLED_ROOT)
    parser.add_argument("--skillguard-root", type=Path, default=DEFAULT_SKILLGUARD_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        raw_result = check_installed_skills(
            args.installed_root,
            skillguard_root=args.skillguard_root,
        )
        if not isinstance(raw_result, Mapping):
            raise TypeError("installed_skill_audit_result_not_object")
        result = dict(raw_result)
        if type(result.get("ok")) is not bool:
            raise TypeError("installed_skill_audit_ok_not_boolean")
        payload = json.dumps(
            result,
            ensure_ascii=False,
            indent=None if args.json else 2,
            sort_keys=True,
            allow_nan=False,
        )
    except Exception as exc:
        result = blocked_installed_skill_audit(
            installed_root=args.installed_root,
            repository_root=ROOT,
            finding_type="installed_skill_audit_machine_output_blocked",
            detail=_exception_detail(exc),
        )
        payload = json.dumps(
            result,
            ensure_ascii=False,
            indent=None if args.json else 2,
            sort_keys=True,
            allow_nan=False,
        )
    print(payload)
    return 0 if result["ok"] else 1


def check_installed_skills(
    installed_root: Path,
    *,
    skillguard_root: Path = DEFAULT_SKILLGUARD_ROOT,
    repository_root: Path = ROOT,
) -> dict[str, Any]:
    """Compare all ten installed trees with current SkillGuard source plans."""

    findings: list[dict[str, Any]] = []
    member_results: list[dict[str, Any]] = []
    try:
        members = physicsguard_member_roots(repository_root)
    except Exception as exc:
        return {
            **_audit_identity(),
            "ok": False,
            "status": "blocked",
            "repo_skill_root": str(Path(repository_root) / "skill"),
            "installed_root": str(installed_root),
            "skill_count": 0,
            "expected_skill_ids": list(PHYSICSGUARD_SKILL_IDS),
            "skillguard_authority": None,
            "member_results": [],
            "findings": [
                {
                    "severity": "error",
                    "type": "physicsguard_source_inventory_blocked",
                    "detail": _exception_detail(exc),
                }
            ],
            "claim_boundary": _claim_boundary(),
        }
    try:
        api = load_skillguard_consumer_api(skillguard_root)
    except Exception as exc:
        return {
            **_audit_identity(),
            "ok": False,
            "status": "blocked",
            "repo_skill_root": str(Path(repository_root) / "skill"),
            "installed_root": str(installed_root),
            "skill_count": len(members),
            "expected_skill_ids": list(PHYSICSGUARD_SKILL_IDS),
            "skillguard_authority": None,
            "member_results": [],
            "findings": [
                {
                    "severity": "error",
                    "type": "skillguard_consumer_authority_unavailable",
                    "detail": _exception_detail(exc),
                }
            ],
            "claim_boundary": _claim_boundary(),
        }
    try:
        authority_record = _json_mapping(
            api.authority_record(), "skillguard_authority_record"
        )
    except Exception as exc:
        return {
            **_audit_identity(),
            "ok": False,
            "status": "blocked",
            "repo_skill_root": str(Path(repository_root) / "skill"),
            "installed_root": str(installed_root),
            "skill_count": len(members),
            "expected_skill_ids": list(PHYSICSGUARD_SKILL_IDS),
            "skillguard_authority": None,
            "member_results": [],
            "findings": [
                {
                    "severity": "error",
                    "type": "skillguard_authority_record_invalid",
                    "detail": _exception_detail(exc),
                }
            ],
            "claim_boundary": _claim_boundary(),
        }

    installed_lexical = Path(installed_root).expanduser().absolute()
    if path_is_link_or_reparse(installed_lexical) or not installed_lexical.is_dir():
        return {
            **_audit_identity(),
            "ok": False,
            "status": "blocked",
            "repo_skill_root": str(Path(repository_root) / "skill"),
            "installed_root": str(installed_lexical),
            "skill_count": len(members),
            "expected_skill_ids": list(PHYSICSGUARD_SKILL_IDS),
            "skillguard_authority": authority_record,
            "member_results": [],
            "findings": [
                {
                    "severity": "error",
                    "type": "installed_skill_root_unsafe",
                    "path": str(installed_lexical),
                }
            ],
            "claim_boundary": _claim_boundary(),
        }
    installed_root = installed_lexical.resolve(strict=True)

    expected_ids = set(PHYSICSGUARD_SKILL_IDS)
    try:
        installed_entries = tuple(installed_root.iterdir())
    except Exception as exc:
        installed_entries = ()
        findings.append(
            {
                "severity": "error",
                "type": "installed_skill_root_scan_blocked",
                "path": str(installed_root),
                "detail": _exception_detail(exc),
            }
        )
    for installed_entry in sorted(installed_entries, key=lambda path: path.name.casefold()):
        skill_name = installed_entry.name
        if (
            skill_name.casefold().startswith("physicsguard-")
            and skill_name not in expected_ids
        ):
            unsafe = path_is_link_or_reparse(installed_entry)
            if unsafe:
                entry_kind = "link_or_reparse"
            elif installed_entry.is_dir():
                entry_kind = "directory"
            elif installed_entry.is_file():
                entry_kind = "file"
            else:
                entry_kind = "other"
            findings.append(
                {
                    "severity": "error",
                    "type": "unexpected_installed_physicsguard_residual",
                    "skill": skill_name,
                    "path": str(installed_entry),
                    "entry_kind": entry_kind,
                    "known_retired_id": skill_name in FORBIDDEN_INSTALLED_SKILLS,
                }
            )
    for skill_id, skill_dir in members:
        installed_dir = installed_root / skill_id
        if not installed_dir.exists() and not installed_dir.is_symlink():
            row = _blocked_member_result(
                skill_id, skill_dir, installed_dir, "installed_skill_missing"
            )
            member_results.append(row)
            findings.append(
                {
                    "severity": "error",
                    "type": "installed_skill_missing",
                    "skill": skill_id,
                    "path": str(installed_dir),
                }
            )
            continue
        if path_is_link_or_reparse(installed_dir) or not installed_dir.is_dir():
            row = _blocked_member_result(
                skill_id,
                skill_dir,
                installed_dir,
                "installed_skill_root_unsafe",
            )
            member_results.append(row)
            findings.append(
                {
                    "severity": "error",
                    "type": "installed_skill_root_unsafe",
                    "skill": skill_id,
                    "path": str(installed_dir),
                }
            )
            continue
        try:
            row = _consumer_projection_status(skill_id, skill_dir, installed_dir, api)
        except Exception as exc:
            row = _blocked_member_result(
                skill_id,
                skill_dir,
                installed_dir,
                f"consumer_projection_check_failed:{_exception_detail(exc)}",
            )
        member_results.append(row)
        if not row["ok"]:
            findings.append(
                {
                    "severity": "error",
                    "type": "installed_consumer_projection_mismatch",
                    "skill": skill_id,
                    "path": str(installed_dir),
                    "reasons": list(row["reasons"]),
                    "expected_release_id": row.get("expected_release_id"),
                    "actual_release_id": row.get("actual_release_id"),
                }
            )
    return {
        **_audit_identity(),
        "ok": not findings,
        "status": "pass" if not findings else "blocked",
        "repo_skill_root": str(Path(repository_root) / "skill"),
        "installed_root": str(installed_root),
        "skill_count": len(members),
        "expected_skill_ids": list(PHYSICSGUARD_SKILL_IDS),
        "skillguard_authority": authority_record,
        "member_results": member_results,
        "findings": findings,
        "claim_boundary": _claim_boundary(),
    }


def _consumer_projection_status(
    skill_id: str,
    source: Path,
    installed: Path,
    api: SkillGuardConsumerApi,
) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        contract = load_member_contract(source, skill_id)
        plan = _json_mapping(
            api.consumer_distribution_plan(source, contract),
            "consumer_distribution_plan",
        )
    except Exception as exc:
        return _blocked_member_result(
            skill_id,
            source,
            installed,
            f"source_plan_unavailable:{_exception_detail(exc)}",
        )

    plan_files, plan_file_reasons = _normalized_files(
        plan.get("files"), "source_consumer_files"
    )
    plan_findings, plan_finding_reasons = _normalized_findings(
        plan.get("findings"), "source_plan_findings"
    )
    reasons.extend(plan_file_reasons)
    reasons.extend(plan_finding_reasons)
    plan_summary = {
        "schema_version": _text_or_none(plan.get("schema_version")),
        "status": _text_or_none(plan.get("status")),
        "skill_id": _text_or_none(plan.get("skill_id")),
        "projection_id": _text_or_none(plan.get("projection_id")),
        "release_id": _text_or_none(plan.get("release_id")),
        "release_manifest_path": _text_or_none(
            plan.get("release_manifest_path")
        ),
        "files": plan_files,
        "findings": plan_findings,
    }
    if plan_summary["schema_version"] is None:
        reasons.append("source_consumer_schema_version_invalid")
    if plan_summary["status"] != "passed":
        reasons.append("source_consumer_plan_blocked")
    if plan_summary["skill_id"] != skill_id:
        reasons.append("source_consumer_plan_skill_mismatch")
    if plan_summary["projection_id"] != "projection:consumer-distribution":
        reasons.append("source_consumer_plan_projection_mismatch")
    if plan_summary["release_manifest_path"] != "consumer-release.json":
        reasons.append("source_consumer_manifest_path_mismatch")
    if not plan_files:
        reasons.append("source_consumer_inventory_invalid")
    if not plan_summary["release_id"]:
        reasons.append("source_consumer_release_id_missing")
    for finding in plan_findings:
        reasons.append(
            "source_plan_finding:"
            f"{finding['code']}:{finding['path']}"
        )

    try:
        audit = _json_mapping(
            api.audit_consumer_distribution(installed),
            "audit_consumer_distribution",
        )
    except Exception as exc:
        blocked = _blocked_member_result(
            skill_id,
            source,
            installed,
            f"installed_audit_unavailable:{_exception_detail(exc)}",
            source_plan=plan_summary,
        )
        blocked["reasons"] = list(
            dict.fromkeys([*reasons, *blocked["reasons"]])
        )
        return blocked

    audit_findings, audit_finding_reasons = _normalized_findings(
        audit.get("findings"), "installed_audit_findings"
    )
    reasons.extend(audit_finding_reasons)
    audit_status = _text_or_none(audit.get("status"))
    audit_skill_id = _text_or_none(audit.get("skill_id"))
    audit_release_id = _text_or_none(audit.get("release_id"))
    raw_member_count = audit.get("member_count")
    if type(raw_member_count) is int and raw_member_count >= 0:
        member_count: int | None = raw_member_count
    else:
        member_count = None
        reasons.append("installed_consumer_member_count_invalid")

    raw_manifest = audit.get("manifest")
    if isinstance(raw_manifest, Mapping):
        manifest = dict(raw_manifest)
    else:
        manifest = {}
        reasons.append("installed_consumer_manifest_missing")
    manifest_files, manifest_file_reasons = _normalized_files(
        manifest.get("files"), "installed_consumer_files"
    )
    reasons.extend(manifest_file_reasons)
    manifest_summary = (
        {
            "schema_version": _text_or_none(manifest.get("schema_version")),
            "skill_id": _text_or_none(manifest.get("skill_id")),
            "projection_id": _text_or_none(manifest.get("projection_id")),
            "release_id": _text_or_none(manifest.get("release_id")),
            "files": manifest_files,
            "author_control_excluded": (
                manifest.get("author_control_excluded")
                if type(manifest.get("author_control_excluded")) is bool
                else None
            ),
            "manifest_hash": _text_or_none(manifest.get("manifest_hash")),
        }
        if manifest
        else None
    )
    audit_summary = {
        "schema_version": _text_or_none(audit.get("schema_version")),
        "status": audit_status,
        "skill_id": audit_skill_id,
        "release_id": audit_release_id,
        "member_count": member_count,
        "findings": audit_findings,
        "manifest": manifest_summary,
    }

    if audit_status != "passed":
        reasons.append("installed_consumer_audit_blocked")
    if audit_skill_id != skill_id:
        reasons.append("installed_consumer_skill_mismatch")
    if audit_release_id != plan_summary["release_id"]:
        reasons.append("installed_consumer_release_id_mismatch")
    if not manifest_files:
        reasons.append("installed_consumer_inventory_invalid")
    if not manifest_summary or not manifest_summary["manifest_hash"]:
        reasons.append("installed_consumer_manifest_hash_missing")
    if member_count is not None and member_count != len(manifest_files):
        reasons.append("installed_consumer_member_count_mismatch")
    expected_identity = {
        "schema_version": plan_summary["schema_version"],
        "skill_id": skill_id,
        "projection_id": plan_summary["projection_id"],
        "release_id": plan_summary["release_id"],
        "files": plan_files,
        "author_control_excluded": True,
    }
    for field, expected in expected_identity.items():
        actual = manifest_summary.get(field) if manifest_summary else None
        if actual != expected:
            reasons.append(f"installed_consumer_manifest_field_mismatch:{field}")
    for finding in audit_findings:
        reasons.append(
            "installed_audit_finding:"
            f"{finding['code']}:{finding['path']}"
        )
    reasons = list(dict.fromkeys(reasons))
    return {
        "skill_id": skill_id,
        "ok": not reasons,
        "status": "pass" if not reasons else "blocked",
        "source_root": str(source),
        "installed_root": str(installed),
        "expected_release_id": plan_summary["release_id"],
        "actual_release_id": audit_release_id,
        "expected_files": plan_files,
        "actual_files": manifest_files,
        "reasons": reasons,
        "source_plan": plan_summary,
        "installed_audit": audit_summary,
    }


def _json_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label}_not_object")
    candidate = dict(value)
    try:
        json.dumps(candidate, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TypeError(
            f"{label}_not_json_serializable:{type(exc).__name__}"
        ) from exc
    return candidate


def _normalized_files(
    value: object,
    reason_prefix: str,
) -> tuple[list[dict[str, str]], list[str]]:
    if type(value) is not list:
        return [], [f"{reason_prefix}_not_list"]
    rows: list[dict[str, str]] = []
    reasons: list[str] = []
    seen: set[str] = set()
    for index, raw_row in enumerate(value):
        if not isinstance(raw_row, Mapping):
            reasons.append(f"{reason_prefix}_row_not_object:{index}")
            continue
        path = raw_row.get("path")
        content_hash = raw_row.get("content_hash")
        if type(path) is not str or not path:
            reasons.append(f"{reason_prefix}_path_invalid:{index}")
            continue
        if type(content_hash) is not str or not content_hash:
            reasons.append(f"{reason_prefix}_content_hash_invalid:{index}")
            continue
        if path in seen:
            reasons.append(f"{reason_prefix}_duplicate_path:{path}")
            continue
        seen.add(path)
        rows.append({"path": path, "content_hash": content_hash})
    return rows, reasons


def _normalized_findings(
    value: object,
    reason_prefix: str,
) -> tuple[list[dict[str, str]], list[str]]:
    if type(value) is not list:
        return [], [f"{reason_prefix}_not_list"]
    rows: list[dict[str, str]] = []
    reasons: list[str] = []
    for index, raw_row in enumerate(value):
        if not isinstance(raw_row, Mapping):
            reasons.append(f"{reason_prefix}_row_not_object:{index}")
            continue
        code = raw_row.get("code")
        path = raw_row.get("path")
        detail = raw_row.get("detail")
        if type(code) is not str or not code:
            reasons.append(f"{reason_prefix}_code_invalid:{index}")
            continue
        if type(path) is not str:
            reasons.append(f"{reason_prefix}_path_invalid:{index}")
            continue
        if type(detail) is not str:
            reasons.append(f"{reason_prefix}_detail_invalid:{index}")
            continue
        rows.append({"code": code, "path": path, "detail": detail})
    return rows, reasons


def _text_or_none(value: object) -> str | None:
    return value if type(value) is str else None


def _blocked_member_result(
    skill_id: str,
    source: Path,
    installed: Path,
    reason: str,
    *,
    source_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "skill_id": skill_id,
        "ok": False,
        "status": "blocked",
        "source_root": str(source),
        "installed_root": str(installed),
        "expected_release_id": (
            source_plan.get("release_id") if source_plan is not None else None
        ),
        "actual_release_id": None,
        "expected_files": (
            list(source_plan.get("files", [])) if source_plan is not None else []
        ),
        "actual_files": [],
        "reasons": [reason],
        "source_plan": dict(source_plan) if source_plan is not None else None,
        "installed_audit": None,
    }


def _audit_identity() -> dict[str, str]:
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "artifact_kind": AUDIT_ARTIFACT_KIND,
    }


def blocked_installed_skill_audit(
    *,
    installed_root: Path,
    repository_root: Path,
    finding_type: str,
    detail: str,
) -> dict[str, Any]:
    return {
        **_audit_identity(),
        "ok": False,
        "status": "blocked",
        "repo_skill_root": str(Path(repository_root) / "skill"),
        "installed_root": str(Path(installed_root)),
        "skill_count": 0,
        "expected_skill_ids": list(PHYSICSGUARD_SKILL_IDS),
        "skillguard_authority": None,
        "member_results": [],
        "findings": [
            {
                "severity": "error",
                "type": finding_type,
                "detail": detail,
            }
        ],
        "claim_boundary": _claim_boundary(),
    }


def _exception_detail(exc: Exception) -> str:
    try:
        detail = str(exc)
    except Exception:
        detail = "unprintable_exception"
    return f"{type(exc).__name__}:{detail}"


def _claim_boundary() -> str:
    return (
        "This read-only check proves only that the exact ten installed PhysicsGuard "
        "trees equal the current SkillGuard consumer-distribution plans. It writes "
        "nothing, executes no target-native check, issues no installation receipt, "
        "and proves no package, Git, tag, or release identity."
    )


if __name__ == "__main__":
    raise SystemExit(main())
