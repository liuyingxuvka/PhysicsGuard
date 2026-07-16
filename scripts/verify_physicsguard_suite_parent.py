"""Capture and replay the receipt-only PhysicsGuard suite parent boundary.

The ten maintained PhysicsGuard skills own their guard-model semantics and
native good/bad proofs.  This module never executes those proofs.  It consumes
their already-issued SkillGuard closures, replays installation currentness,
and freezes the exact child identities needed by the existing suite ModelMesh.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "physicsguard.skill_suite_parent_inventory.v1"
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
CLAIM_BOUNDARY = (
    "The parent proves only current replay of the ten frozen child closures, "
    "their exact source/install projections, and their installation receipts. "
    "It launches no child proof and makes no physical judgment of its own."
)


class ParentReceiptError(ValueError):
    """Fail-closed suite parent validation error."""


def _codex_home(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def _bootstrap_skillguard(codex_home: Path) -> None:
    scripts = codex_home / "skills" / "skillguard" / "scripts"
    if not scripts.is_dir():
        raise ParentReceiptError("installed_skillguard_scripts_missing")
    value = str(scripts)
    if value not in sys.path:
        sys.path.insert(0, value)


def _read_object(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParentReceiptError(f"{code}:{path.as_posix()}") from exc
    if not isinstance(value, dict):
        raise ParentReceiptError(f"{code}:{path.as_posix()}")
    return value


def _stable_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(_stable_bytes(value))
    os.replace(temporary, path)


def _relative(path: Path, root: Path, code: str) -> str:
    try:
        return path.resolve(strict=True).relative_to(root.resolve(strict=True)).as_posix()
    except (OSError, ValueError) as exc:
        raise ParentReceiptError(code) from exc


def _unsigned_hash(value: Mapping[str, Any], hash_field: str) -> str:
    from skillguard_v2.provenance import canonical_hash

    return canonical_hash({key: item for key, item in value.items() if key != hash_field})


def _runtime_identity() -> tuple[dict[str, Any], str]:
    from skillguard_v2.provenance import canonical_hash
    from skillguard_v2.runtime_fingerprint import guard_execution_runtime_fingerprint

    identity = dict(guard_execution_runtime_fingerprint())
    return identity, canonical_hash(identity)


def _load_inventory(path: Path) -> dict[str, Any]:
    value = _read_object(path, "parent_inventory_unreadable")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ParentReceiptError("parent_inventory_schema_wrong")
    if value.get("inventory_hash") != _unsigned_hash(value, "inventory_hash"):
        raise ParentReceiptError("parent_inventory_hash_mismatch")
    children = value.get("children")
    if not isinstance(children, list):
        raise ParentReceiptError("parent_inventory_children_invalid")
    ids = [str(row.get("skill_id", "")) for row in children if isinstance(row, Mapping)]
    if tuple(ids) != EXPECTED_SKILLS or len(children) != len(EXPECTED_SKILLS):
        raise ParentReceiptError("parent_inventory_child_set_mismatch")
    if value.get("claim_boundary") != CLAIM_BOUNDARY:
        raise ParentReceiptError("parent_inventory_claim_boundary_mismatch")
    return value


def _candidate_reports(repository_root: Path, skill_id: str) -> list[tuple[str, Path, dict[str, Any]]]:
    candidates: list[tuple[str, Path, dict[str, Any]]] = []
    for path in sorted((repository_root / "work" / "r").glob("*/.skillguard/runs/*/supervisor-result.json")):
        report = _read_object(path, "supervisor_result_unreadable")
        if report.get("status") != "passed" or report.get("skill_id") != skill_id:
            continue
        closures = report.get("closures")
        if not isinstance(closures, list) or len(closures) != 1:
            continue
        closure = closures[0]
        if not isinstance(closure, Mapping) or closure.get("profile") != "enforced":
            continue
        candidates.append((str(report.get("created_at", "")), path.parent, report))
    return candidates


def _capture_child(repository_root: Path, codex_home: Path, skill_id: str) -> dict[str, Any]:
    candidates = _candidate_reports(repository_root, skill_id)
    if not candidates:
        raise ParentReceiptError(f"current_child_supervisor_result_missing:{skill_id}")
    _created_at, run_root, report = max(candidates, key=lambda row: (row[0], row[1].as_posix()))
    closure_row = report["closures"][0]
    transaction_root = codex_home / "target-install-transactions" / skill_id
    head = _read_object(transaction_root / "HEAD.json", "target_install_head_unreadable")
    transaction_id = str(head.get("transaction_id", ""))
    receipt_path = transaction_root / "receipts" / f"{transaction_id}.json"
    receipt = _read_object(receipt_path, "target_install_receipt_unreadable")
    source_skill = repository_root / "skill" / skill_id
    installed_skill = codex_home / "skills" / skill_id
    source_contract = _read_object(
        source_skill / ".skillguard" / "compiled-contract.json",
        "source_compiled_contract_unreadable",
    )
    installed_contract = _read_object(
        installed_skill / ".skillguard" / "compiled-contract.json",
        "installed_compiled_contract_unreadable",
    )
    row = {
        "skill_id": skill_id,
        "source_skill_path": _relative(source_skill, repository_root, "source_skill_outside_repository"),
        "installed_skill_path": f"skills/{skill_id}",
        "run_root": _relative(run_root, repository_root, "child_run_outside_repository"),
        "run_id": str(report.get("run_id", "")),
        "contract_hash": str(report.get("contract_hash", "")),
        "manifest_hash": str(report.get("manifest_hash", "")),
        "closure_receipt_id": str(closure_row.get("closure_receipt_id", "")),
        "closure_hash": str(closure_row.get("closure_hash", "")),
        "supervisor_report_hash": str(report.get("report_hash", "")),
        "installation_transaction_id": transaction_id,
        "installation_receipt_hash": str(receipt.get("receipt_hash", "")),
        "installation_projection_identity_hash": str(
            receipt.get("active_projection", {}).get("identity_hash", "")
            if isinstance(receipt.get("active_projection"), Mapping)
            else ""
        ),
        "source_contract_hash": str(source_contract.get("contract_hash", "")),
        "installed_contract_hash": str(installed_contract.get("contract_hash", "")),
    }
    return row


def capture_inventory(repository_root: Path, codex_home: Path, output: Path) -> dict[str, Any]:
    _bootstrap_skillguard(codex_home)
    runtime, runtime_hash = _runtime_identity()
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "suite_id": "physicsguard-maintained-skill-suite",
        "skillguard_runtime_identity": runtime,
        "skillguard_runtime_identity_hash": runtime_hash,
        "owner_evidence_root": "work/oe",
        "children": [
            _capture_child(repository_root, codex_home, skill_id)
            for skill_id in EXPECTED_SKILLS
        ],
        "claim_boundary": CLAIM_BOUNDARY,
    }
    value["inventory_hash"] = _unsigned_hash(value, "inventory_hash")
    _atomic_write(output, value)
    return value


def _verify_installation(
    repository_root: Path,
    codex_home: Path,
    row: Mapping[str, Any],
) -> list[str]:
    from skillguard_v2.installation import installation_projection_identity

    findings: list[str] = []
    skill_id = str(row.get("skill_id", ""))
    source_skill = repository_root / Path(str(row.get("source_skill_path", "")))
    installed_skill = codex_home / Path(str(row.get("installed_skill_path", "")))
    transaction_id = str(row.get("installation_transaction_id", ""))
    transaction_root = codex_home / "target-install-transactions" / skill_id
    receipt = _read_object(
        transaction_root / "receipts" / f"{transaction_id}.json",
        "target_install_receipt_unreadable",
    )
    head = _read_object(transaction_root / "HEAD.json", "target_install_head_unreadable")
    if receipt.get("receipt_hash") != _unsigned_hash(receipt, "receipt_hash"):
        findings.append("target_install_receipt_hash_mismatch")
    if receipt.get("status") != "committed" or receipt.get("skill_id") != skill_id:
        findings.append("target_install_receipt_identity_mismatch")
    if head.get("transaction_id") != transaction_id or head.get("receipt_hash") != receipt.get("receipt_hash"):
        findings.append("target_install_head_mismatch")
    if receipt.get("receipt_hash") != row.get("installation_receipt_hash"):
        findings.append("frozen_installation_receipt_changed")
    try:
        source_projection = installation_projection_identity(source_skill)
        active_projection = installation_projection_identity(installed_skill)
    except (OSError, ValueError) as exc:
        findings.append(f"installation_projection_invalid:{exc}")
        return findings
    expected_projection = receipt.get("canonical_projection")
    if source_projection != expected_projection:
        findings.append("source_installation_projection_drift")
    if active_projection != expected_projection:
        findings.append("installed_projection_drift")
    if receipt.get("active_projection") != expected_projection or receipt.get("stage_projection") != expected_projection:
        findings.append("installation_receipt_projection_mismatch")
    if expected_projection.get("identity_hash") != row.get("installation_projection_identity_hash"):
        findings.append("frozen_installation_projection_changed")
    try:
        from verify_guard_simulation_readiness import _authority_status, _parity_status

        retirement_path = repository_root / ".flowguard" / "retirement-receipts" / f"{skill_id}.json"
        source_authority = _authority_status(source_skill, skill_id, retirement_path)
        installed_authority = _authority_status(installed_skill, skill_id, retirement_path)
        retirement_parity = _parity_status(source_skill, installed_skill)
    except (OSError, ValueError) as exc:
        findings.append(f"retirement_authority_unreadable:{type(exc).__name__}")
    else:
        if not source_authority.get("ok"):
            findings.append("source_retirement_authority_not_current")
        if not installed_authority.get("ok"):
            findings.append("installed_retirement_authority_not_current")
        if not retirement_parity.get("ok"):
            findings.append("retirement_authority_parity_mismatch")
    return findings


def _verify_closure(
    repository_root: Path,
    codex_home: Path,
    inventory: Mapping[str, Any],
    row: Mapping[str, Any],
) -> list[str]:
    from skillguard_v2.closure import load_closure, verify_closure
    from skillguard_v2.run_store import load_contract_snapshot, load_run
    from skillguard_v2.supervisor import _current_fingerprints

    findings: list[str] = []
    skill_id = str(row.get("skill_id", ""))
    run_root = repository_root / Path(str(row.get("run_root", "")))
    installed_skill = codex_home / Path(str(row.get("installed_skill_path", "")))
    report = _read_object(run_root / "supervisor-result.json", "supervisor_result_unreadable")
    if report.get("report_hash") != _unsigned_hash(report, "report_hash"):
        findings.append("supervisor_report_hash_mismatch")
    for field in ("skill_id", "run_id", "contract_hash", "manifest_hash"):
        if report.get(field) != row.get(field):
            findings.append(f"supervisor_{field}_mismatch")
    if report.get("supervisor_report_hash") not in (None, row.get("supervisor_report_hash")):
        findings.append("supervisor_report_frozen_hash_mismatch")
    if report.get("report_hash") != row.get("supervisor_report_hash"):
        findings.append("frozen_supervisor_report_changed")
    closures = report.get("closures")
    closure_rows = [
        value
        for value in closures or []
        if isinstance(value, Mapping)
        and value.get("closure_receipt_id") == row.get("closure_receipt_id")
    ]
    if len(closure_rows) != 1 or closure_rows[0].get("closure_hash") != row.get("closure_hash"):
        findings.append("supervisor_closure_binding_mismatch")
        return findings
    try:
        closure = load_closure(run_root, str(row.get("closure_receipt_id", "")))
    except Exception as exc:  # SkillGuard exposes typed errors but remains an external toolchain.
        findings.append(f"closure_unreadable:{type(exc).__name__}")
        return findings
    if closure.get("closure_hash") != row.get("closure_hash") or closure.get("run_id") != row.get("run_id"):
        findings.append("closure_identity_mismatch")
    contract = load_contract_snapshot(run_root)
    run = load_run(run_root)
    if contract.get("contract_hash") != row.get("contract_hash"):
        findings.append("closure_contract_snapshot_mismatch")
    current_runtime, current_runtime_hash = _runtime_identity()
    if inventory.get("skillguard_runtime_identity") != current_runtime:
        findings.append("skillguard_runtime_identity_drift")
    if inventory.get("skillguard_runtime_identity_hash") != current_runtime_hash:
        findings.append("skillguard_runtime_identity_hash_drift")
    replay = verify_closure(
        run_root,
        str(row.get("closure_receipt_id", "")),
        current_fingerprints=_current_fingerprints(contract, run["request"], installed_skill),
        target_root=installed_skill,
        repository_root=repository_root,
        owner_evidence_root=repository_root / Path(str(inventory.get("owner_evidence_root", ""))),
    )
    if not replay.get("ok"):
        findings.extend(f"closure_replay:{value}" for value in replay.get("findings", []))
    source_contract = _read_object(
        repository_root / Path(str(row.get("source_skill_path", ""))) / ".skillguard/compiled-contract.json",
        "source_compiled_contract_unreadable",
    )
    installed_contract = _read_object(
        installed_skill / ".skillguard/compiled-contract.json",
        "installed_compiled_contract_unreadable",
    )
    if source_contract.get("contract_hash") != row.get("source_contract_hash"):
        findings.append("source_contract_drift")
    if installed_contract.get("contract_hash") != row.get("installed_contract_hash"):
        findings.append("installed_contract_drift")
    if source_contract.get("contract_hash") != installed_contract.get("contract_hash"):
        findings.append("source_installed_contract_mismatch")
    return findings


def verify_child(
    repository_root: Path,
    codex_home: Path,
    inventory_path: Path,
    skill_id: str,
) -> dict[str, Any]:
    _bootstrap_skillguard(codex_home)
    inventory = _load_inventory(inventory_path)
    row = next((value for value in inventory["children"] if value.get("skill_id") == skill_id), None)
    if row is None:
        raise ParentReceiptError(f"parent_child_unknown:{skill_id}")
    findings = [
        *_verify_installation(repository_root, codex_home, row),
        *_verify_closure(repository_root, codex_home, inventory, row),
    ]
    return {
        "artifact_kind": "physicsguard_suite_child_receipt_replay",
        "skill_id": skill_id,
        "status": "pass" if not findings else "blocked",
        "findings": findings,
        "closure_receipt_id": row.get("closure_receipt_id"),
        "installation_transaction_id": row.get("installation_transaction_id"),
        "execution_count": 0,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def verify_suite(repository_root: Path, codex_home: Path, inventory_path: Path) -> dict[str, Any]:
    results = [verify_child(repository_root, codex_home, inventory_path, skill_id) for skill_id in EXPECTED_SKILLS]
    findings = [
        f"{result['skill_id']}:{finding}"
        for result in results
        for finding in result["findings"]
    ]
    return {
        "artifact_kind": "physicsguard_suite_parent_receipt_replay",
        "status": "pass" if not findings else "blocked",
        "child_count": len(results),
        "children": results,
        "findings": findings,
        "execution_count": 0,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("capture", "verify-child", "verify-suite"),
        help="Capture the frozen child inventory or replay it without executing child proofs.",
    )
    parser.add_argument("--repository-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--codex-home")
    parser.add_argument(
        "--inventory",
        default=".flowguard/physicsguard_suite_parent_inventory.json",
    )
    parser.add_argument("--skill-id", choices=EXPECTED_SKILLS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repository_root = Path(args.repository_root).resolve()
    codex_home = _codex_home(args.codex_home)
    inventory_path = Path(args.inventory)
    if not inventory_path.is_absolute():
        inventory_path = repository_root / inventory_path
    try:
        if args.action == "capture":
            result: Mapping[str, Any] = capture_inventory(repository_root, codex_home, inventory_path)
            status = "pass"
        elif args.action == "verify-child":
            if not args.skill_id:
                raise ParentReceiptError("verify_child_skill_id_required")
            result = verify_child(repository_root, codex_home, inventory_path, args.skill_id)
            status = str(result.get("status", "blocked"))
        else:
            result = verify_suite(repository_root, codex_home, inventory_path)
            status = str(result.get("status", "blocked"))
    except ParentReceiptError as exc:
        result = {
            "artifact_kind": "physicsguard_suite_parent_receipt_replay",
            "status": "blocked",
            "findings": [str(exc)],
            "execution_count": 0,
            "claim_boundary": CLAIM_BOUNDARY,
        }
        status = "blocked"
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if status == "pass" or args.action == "capture" else 1


if __name__ == "__main__":
    raise SystemExit(main())
