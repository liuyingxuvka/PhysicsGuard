"""Plan or coordinate one exact ten-member PhysicsGuard consumer installation.

The coordinator owns only suite membership and ordering.  Every projection,
stage check, filesystem lock, activation journal, receipt, and rollback is
performed by the current installed SkillGuard public target-installation API.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from physicsguard_skill_install_authority import (  # noqa: E402
    DEFAULT_CODEX_HOME,
    DEFAULT_SKILLGUARD_ROOT,
    PHYSICSGUARD_MAINTENANCE_UNIT_ID,
    PHYSICSGUARD_SKILL_IDS,
    SkillGuardAuthorityUnavailable,
    SkillGuardConsumerApi,
    load_member_contract,
    load_skillguard_consumer_api,
    physicsguard_member_roots,
)


TRANSACTION_ID_PATTERN = re.compile(r"^target-install-[0-9a-f]{32}$")
CANONICAL_HASH_PATTERN = re.compile(r"^[0-9A-F]{64}$")


def build_suite_plan(
    repository_root: Path,
    api: SkillGuardConsumerApi,
) -> dict[str, Any]:
    """Create a pure source plan through SkillGuard without staging or installing."""

    try:
        members = physicsguard_member_roots(repository_root)
    except (OSError, ValueError) as exc:
        return {
            "status": "blocked",
            "maintenance_unit_id": PHYSICSGUARD_MAINTENANCE_UNIT_ID,
            "member_ids": list(PHYSICSGUARD_SKILL_IDS),
            "members": [],
            "blockers": [f"suite_inventory_blocked:{type(exc).__name__}:{exc}"],
        }
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []
    for skill_id, member_root in members:
        try:
            contract = load_member_contract(member_root, skill_id)
            raw_plan = api.consumer_distribution_plan(member_root, contract)
            if not isinstance(raw_plan, Mapping):
                raise TypeError("consumer_distribution_plan_not_object")
            plan = dict(raw_plan)
        except Exception as exc:
            plan = None
            blockers.append(
                f"member_plan_unavailable:{skill_id}:{type(exc).__name__}:{exc}"
            )
        else:
            if plan.get("status") != "passed":
                blockers.append(f"member_plan_blocked:{skill_id}")
            if plan.get("skill_id") != skill_id:
                blockers.append(f"member_plan_skill_mismatch:{skill_id}")
            if plan.get("projection_id") != "projection:consumer-distribution":
                blockers.append(f"member_plan_projection_mismatch:{skill_id}")
            if plan.get("release_manifest_path") != "consumer-release.json":
                blockers.append(f"member_plan_manifest_path_mismatch:{skill_id}")
            files = plan.get("files")
            if not isinstance(files, list) or not files:
                blockers.append(f"member_plan_inventory_invalid:{skill_id}")
            if not str(plan.get("release_id", "")):
                blockers.append(f"member_plan_release_id_missing:{skill_id}")
            plan_findings = plan.get("findings")
            if not isinstance(plan_findings, list):
                blockers.append(f"member_plan_findings_invalid:{skill_id}")
            elif plan_findings:
                blockers.append(f"member_plan_findings_present:{skill_id}")
        rows.append(
            {
                "skill_id": skill_id,
                "member_root": str(member_root),
                "plan": plan,
            }
        )
    return {
        "status": "blocked" if blockers else "passed",
        "maintenance_unit_id": PHYSICSGUARD_MAINTENANCE_UNIT_ID,
        "member_ids": list(PHYSICSGUARD_SKILL_IDS),
        "members": rows,
        "blockers": blockers,
        "claim_boundary": (
            "This plan is a read-only projection from the current SkillGuard "
            "consumer planner. It creates no stage, lock, journal, receipt, or install."
        ),
    }


def _activation_result_findings(
    skill_id: str,
    report: Mapping[str, Any],
    verification: Mapping[str, Any],
) -> list[str]:
    findings: list[str] = []
    transaction_id = str(report.get("transaction_id", ""))
    receipt = report.get("receipt")
    head = report.get("head")
    if report.get("status") != "passed":
        findings.append("activation_status_blocked")
    if report.get("skill_id") != skill_id:
        findings.append("activation_skill_identity_mismatch")
    if not TRANSACTION_ID_PATTERN.fullmatch(transaction_id):
        findings.append("activation_transaction_pointer_malformed")
    if not isinstance(receipt, Mapping):
        receipt = {}
        findings.append("activation_receipt_pointer_missing")
    if not isinstance(head, Mapping):
        head = {}
        findings.append("activation_head_pointer_missing")
    receipt_hash = str(receipt.get("receipt_hash", ""))
    if (
        receipt.get("status") != "committed"
        or receipt.get("skill_id") != skill_id
        or receipt.get("transaction_id") != transaction_id
        or not CANONICAL_HASH_PATTERN.fullmatch(receipt_hash)
    ):
        findings.append("activation_receipt_pointer_identity_mismatch")
    if (
        head.get("skill_id") != skill_id
        or head.get("transaction_id") != transaction_id
        or head.get("receipt_hash") != receipt_hash
        or not isinstance(head.get("generation"), int)
        or int(head.get("generation", 0)) < 1
    ):
        findings.append("activation_head_pointer_identity_mismatch")
    expected_projection = verification.get("canonical_projection")
    receipt_projection = receipt.get("canonical_projection")
    if (
        not isinstance(expected_projection, Mapping)
        or not isinstance(receipt_projection, Mapping)
        or receipt_projection.get("release_id")
        != expected_projection.get("release_id")
    ):
        findings.append("activation_projection_identity_mismatch")
    return findings


def coordinate_suite_install(
    repository_root: Path,
    stage_root: Path,
    codex_home: Path,
    api: SkillGuardConsumerApi,
) -> dict[str, Any]:
    """Prepare and verify all members before activation; roll back in reverse."""

    required = {
        "prepare_target_stage": api.prepare_target_stage,
        "verify_target_stage": api.verify_target_stage,
        "activate_target_stage": api.activate_target_stage,
        "rollback_target_install": api.rollback_target_install,
    }
    missing = sorted(name for name, value in required.items() if not callable(value))
    if missing:
        return {
            "status": "blocked",
            "phase": "api_preflight",
            "blockers": [f"skillguard_install_api_missing:{name}" for name in missing],
            "activated": [],
            "rollbacks": [],
        }
    suite_plan = build_suite_plan(repository_root, api)
    if suite_plan["status"] != "passed":
        return {
            "status": "blocked",
            "phase": "plan",
            "suite_plan": suite_plan,
            "prepared": [],
            "verified": [],
            "activated": [],
            "rollbacks": [],
            "blockers": list(suite_plan["blockers"]),
        }

    prepare = api.prepare_target_stage
    verify = api.verify_target_stage
    activate = api.activate_target_stage
    rollback = api.rollback_target_install
    assert prepare is not None
    assert verify is not None
    assert activate is not None
    assert rollback is not None

    repository = Path(repository_root).resolve(strict=True)
    stage_parent = Path(stage_root).absolute()
    home = Path(codex_home).expanduser().absolute()
    member_roots = {
        skill_id: member_root
        for skill_id, member_root in physicsguard_member_roots(repository)
    }
    prepared: list[dict[str, Any]] = []
    verified: list[dict[str, Any]] = []
    activated: list[dict[str, Any]] = []
    rollbacks: list[dict[str, Any]] = []

    for skill_id in PHYSICSGUARD_SKILL_IDS:
        stage = stage_parent / skill_id
        try:
            raw_report = prepare(repository, member_roots[skill_id], stage)
            report = (
                dict(raw_report)
                if isinstance(raw_report, Mapping)
                else {
                    "status": "blocked",
                    "blockers": ["coordinator_observed_non_object_prepare_result"],
                }
            )
        except Exception as exc:  # SkillGuard owns and types the underlying failure.
            report = {
                "status": "blocked",
                "blockers": [f"coordinator_observed_exception:{type(exc).__name__}:{exc}"],
            }
        prepared.append({"skill_id": skill_id, "stage_root": str(stage), "report": report})
        if report.get("status") != "passed" or report.get("skill_id") != skill_id:
            return _blocked_install_result(
                phase="prepare",
                suite_plan=suite_plan,
                prepared=prepared,
                verified=verified,
                activated=activated,
                rollbacks=rollbacks,
                blockers=[
                    f"member_prepare_blocked:{skill_id}"
                    if report.get("status") != "passed"
                    else f"member_prepare_identity_mismatch:{skill_id}"
                ],
            )

    for skill_id in PHYSICSGUARD_SKILL_IDS:
        stage = stage_parent / skill_id
        try:
            raw_report = verify(repository, member_roots[skill_id], stage)
            report = (
                dict(raw_report)
                if isinstance(raw_report, Mapping)
                else {
                    "status": "blocked",
                    "blockers": ["coordinator_observed_non_object_verify_result"],
                }
            )
        except Exception as exc:
            report = {
                "status": "blocked",
                "blockers": [f"coordinator_observed_exception:{type(exc).__name__}:{exc}"],
            }
        verified.append({"skill_id": skill_id, "stage_root": str(stage), "report": report})
        if (
            report.get("status") != "passed"
            or report.get("skill_id") != skill_id
            or not str(report.get("stage_verification_hash", ""))
        ):
            return _blocked_install_result(
                phase="verify",
                suite_plan=suite_plan,
                prepared=prepared,
                verified=verified,
                activated=activated,
                rollbacks=rollbacks,
                blockers=[
                    f"member_verify_blocked:{skill_id}"
                    if report.get("status") != "passed"
                    else f"member_verify_identity_mismatch:{skill_id}"
                ],
            )

    verification_by_id = {
        str(row["skill_id"]): row["report"] for row in verified
    }
    for skill_id in PHYSICSGUARD_SKILL_IDS:
        stage = stage_parent / skill_id
        try:
            raw_report = activate(
                repository,
                member_roots[skill_id],
                stage,
                home,
                stage_verification=verification_by_id[skill_id],
            )
            report = (
                dict(raw_report)
                if isinstance(raw_report, Mapping)
                else {
                    "status": "blocked",
                    "blockers": ["coordinator_observed_non_object_activate_result"],
                }
            )
        except Exception as exc:
            report = {
                "status": "blocked",
                "blockers": [f"coordinator_observed_exception:{type(exc).__name__}:{exc}"],
            }
        activation_row = {"skill_id": skill_id, "report": report}
        activated.append(activation_row)
        activation_findings = _activation_result_findings(
            skill_id,
            report,
            verification_by_id[skill_id],
        )
        activation_current = not activation_findings
        if activation_current:
            continue
        rollback_candidates = [
            prior
            for prior in reversed(activated)
            if prior["skill_id"] != skill_id
            or (
                prior["report"].get("status") == "passed"
                and TRANSACTION_ID_PATTERN.fullmatch(
                    str(prior["report"].get("transaction_id", ""))
                )
            )
        ]
        for prior in rollback_candidates:
            prior_report = prior["report"]
            transaction_id = str(prior_report.get("transaction_id", ""))
            prior_skill_id = str(prior["skill_id"])
            if not transaction_id:
                rollback_report = {
                    "status": "blocked",
                    "blockers": ["successful_activation_transaction_id_missing"],
                }
            else:
                try:
                    raw_rollback_report = rollback(
                        home, prior_skill_id, transaction_id
                    )
                    rollback_report = (
                        dict(raw_rollback_report)
                        if isinstance(raw_rollback_report, Mapping)
                        else {
                            "status": "blocked",
                            "blockers": [
                                "coordinator_observed_non_object_rollback_result"
                            ],
                        }
                    )
                    if (
                        rollback_report.get("status") == "passed"
                        and (
                            rollback_report.get("skill_id") != prior_skill_id
                            or rollback_report.get("transaction_id") != transaction_id
                            or rollback_report.get("restored_status")
                            != "manually_rolled_back"
                        )
                    ):
                        rollback_report = {
                            "status": "blocked",
                            "skill_id": prior_skill_id,
                            "transaction_id": transaction_id,
                            "blockers": ["rollback_identity_mismatch"],
                            "observed_result": rollback_report,
                        }
                except Exception as exc:
                    rollback_report = {
                        "status": "blocked",
                        "blockers": [
                            f"coordinator_observed_exception:{type(exc).__name__}:{exc}"
                        ],
                    }
            rollbacks.append(
                {
                    "skill_id": prior_skill_id,
                    "transaction_id": transaction_id,
                    "report": rollback_report,
                }
            )
        rollback_blockers = [
            f"member_rollback_blocked:{row['skill_id']}"
            for row in rollbacks
            if row["report"].get("status") != "passed"
        ]
        cleanup_unconfirmed = bool(rollback_blockers) or any(
            "target_rollback_failed" in str(blocker)
            for blocker in report.get("blockers", [])
        )
        return _blocked_install_result(
            phase="activate",
            suite_plan=suite_plan,
            prepared=prepared,
            verified=verified,
            activated=activated,
            rollbacks=rollbacks,
            blockers=[
                (
                    f"member_activation_blocked:{skill_id}"
                    if report.get("status") != "passed"
                    else f"member_activation_identity_mismatch:{skill_id}"
                ),
                *activation_findings,
                *(["cleanup_unconfirmed"] if cleanup_unconfirmed else []),
                *rollback_blockers,
            ],
            suite_state=(
                "cleanup_unconfirmed" if cleanup_unconfirmed else "rolled_back_clean"
            ),
        )

    return {
        "status": "passed",
        "phase": "complete",
        "maintenance_unit_id": PHYSICSGUARD_MAINTENANCE_UNIT_ID,
        "member_ids": list(PHYSICSGUARD_SKILL_IDS),
        "suite_plan": suite_plan,
        "prepared": prepared,
        "verified": verified,
        "activated": activated,
        "rollbacks": rollbacks,
        "blockers": [],
        "suite_state": "committed_pending_final_audit",
        "claim_boundary": _claim_boundary(),
    }


def _blocked_install_result(
    *,
    phase: str,
    suite_plan: dict[str, Any],
    prepared: list[dict[str, Any]],
    verified: list[dict[str, Any]],
    activated: list[dict[str, Any]],
    rollbacks: list[dict[str, Any]],
    blockers: list[str],
    suite_state: str = "no_activation",
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "phase": phase,
        "maintenance_unit_id": PHYSICSGUARD_MAINTENANCE_UNIT_ID,
        "member_ids": list(PHYSICSGUARD_SKILL_IDS),
        "suite_plan": suite_plan,
        "prepared": prepared,
        "verified": verified,
        "activated": activated,
        "rollbacks": rollbacks,
        "blockers": blockers,
        "suite_state": suite_state,
        "claim_boundary": _claim_boundary(),
    }


def _claim_boundary() -> str:
    return (
        "The coordinator proves only the ordered outcome returned by the current "
        "SkillGuard target-installation API for these ten members. SkillGuard owns "
        "every projection, lock, journal, receipt, verification, and rollback. The "
        "result proves no PhysicsGuard domain behavior, package, Git, tag, or release."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--install", action="store_true")
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--stage-root", type=Path)
    parser.add_argument("--codex-home", type=Path, default=DEFAULT_CODEX_HOME)
    parser.add_argument("--skillguard-root", type=Path, default=DEFAULT_SKILLGUARD_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.install and args.stage_root is None:
        parser.error("--stage-root is required with --install")
    try:
        api = load_skillguard_consumer_api(
            args.skillguard_root,
            require_installation=args.install,
        )
        result = (
            build_suite_plan(args.repository_root, api)
            if args.plan
            else coordinate_suite_install(
                args.repository_root,
                args.stage_root,
                args.codex_home,
                api,
            )
        )
        result["skillguard_authority"] = api.authority_record()
    except SkillGuardAuthorityUnavailable as exc:
        result = {
            "status": "blocked",
            "phase": "api_preflight",
            "skillguard_authority": None,
            "blockers": [f"skillguard_authority_unavailable:{exc}"],
            "claim_boundary": _claim_boundary(),
        }
    except Exception as exc:
        result = {
            "status": "blocked",
            "phase": "coordinator",
            "skillguard_authority": None,
            "blockers": [
                f"coordinator_unhandled_exception:{type(exc).__name__}:{exc}"
            ],
            "suite_state": "cleanup_unconfirmed" if args.install else "no_activation",
            "claim_boundary": _claim_boundary(),
        }
    try:
        payload = json.dumps(
            result,
            ensure_ascii=False,
            indent=None if args.json else 2,
            sort_keys=True,
            allow_nan=False,
        )
    except Exception as exc:
        result = {
            "status": "blocked",
            "phase": "machine_output",
            "skillguard_authority": None,
            "blockers": [
                f"coordinator_result_not_serializable:{type(exc).__name__}"
            ],
            "suite_state": "cleanup_unconfirmed" if args.install else "no_activation",
            "claim_boundary": _claim_boundary(),
        }
        payload = json.dumps(
            result,
            ensure_ascii=False,
            indent=None if args.json else 2,
            sort_keys=True,
            allow_nan=False,
        )
    print(payload)
    return 0 if result.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
