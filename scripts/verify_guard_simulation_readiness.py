from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
HOME_SKILLS = CODEX_HOME / "skills"
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from check_installed_physicsguard_skills import (  # noqa: E402
    blocked_installed_skill_audit,
    check_installed_skills,
)


PACKAGE_NAME = "physicsguard"
SUITE_MESH_PATH = ROOT / ".flowguard" / "physicsguard_skill_suite_mesh.json"
FLOWGUARD_PROJECT_PATH = ROOT / ".flowguard" / "project.toml"
SKILLS = (
    ("physicsguard-ai-debugging", "skill/physicsguard-ai-debugging", "physicsguard-ai-debugging"),
    ("physicsguard-audit-closure", "skill/physicsguard-audit-closure", "physicsguard-audit-closure"),
    ("physicsguard-candidate-model-blueprint", "skill/physicsguard-candidate-model-blueprint", "physicsguard-candidate-model-blueprint"),
    ("physicsguard-model-dataset-validation", "skill/physicsguard-model-dataset-validation", "physicsguard-model-dataset-validation"),
    ("physicsguard-model-library", "skill/physicsguard-model-library", "physicsguard-model-library"),
    ("physicsguard-model-understanding-preflight", "skill/physicsguard-model-understanding-preflight", "physicsguard-model-understanding-preflight"),
    ("physicsguard-project-adoption", "skill/physicsguard-project-adoption", "physicsguard-project-adoption"),
    ("physicsguard-project-evidence-registry", "skill/physicsguard-project-evidence-registry", "physicsguard-project-evidence-registry"),
    ("physicsguard-signal-mapping-review", "skill/physicsguard-signal-mapping-review", "physicsguard-signal-mapping-review"),
    ("physicsguard-test-file-contract-review", "skill/physicsguard-test-file-contract-review", "physicsguard-test-file-contract-review"),
)
V2_AUTHORITY_FILES = (
    "contract-source.json",
    "compiled-contract.json",
    "check-manifest.json",
)
FORBIDDEN_V1_FILES = (
    "check_manifest.json",
    "work-contract.json",
    "check.py",
    "checks/check_closure.py",
    "checks/check_evidence.py",
    "checks/check_phase_order.py",
    "checks/check_quality_floor.py",
    "checks/check_route.py",
    "skillguard_closure_policy.json",
    "skillguard_evidence_rules.json",
    "skillguard_manifest.json",
    "skillguard_profile.json",
    "skillguard_skill_contract.json",
    "skillguard_progress_ledger.jsonl",
)
FORBIDDEN_V1_DIRS = ("ai_judgments", "evidence", "reports", "runs")
RETIREMENT_RECEIPT_SCHEMA = "physicsguard.v1_retirement_completion_receipt.v2"
RETIREMENT_RECEIPT_ROOT = ROOT / ".flowguard" / "retirement-receipts"
RETIREMENT_INVENTORY = ROOT / ".flowguard" / "physicsguard_v1_retirement_inventory.json"
RETIREMENT_CLAIM_BOUNDARY = (
    "This deterministic receipt proves only that the expanded former-V1 residual "
    "inventory was absent from the named source skill while the exact current V2 "
    "authority files were present. Current installed parity, installation receipts, "
    "native closure, parent consumption, release, and future AI behavior require "
    "separate current evidence."
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest().lower()


def _receipt_inventory() -> dict[str, Any]:
    value = json.loads(RETIREMENT_INVENTORY.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("retirement_inventory_object_required")
    return value


def _authority_hashes(control_root: Path) -> dict[str, str]:
    return {
        name: _sha256(control_root / name)
        for name in V2_AUTHORITY_FILES
        if (control_root / name).is_file()
    }


def build_retirement_receipt(skill_root: Path, target_skill_id: str) -> dict[str, Any]:
    inventory = _receipt_inventory()
    control_root = skill_root / ".skillguard"
    missing = [name for name in V2_AUTHORITY_FILES if not (control_root / name).is_file()]
    residuals = _residuals(control_root)
    if missing:
        raise ValueError("retirement_current_authority_missing:" + ",".join(missing))
    if residuals:
        raise ValueError("retirement_residuals_present:" + ",".join(residuals))
    scope = [str(value) for value in inventory.get("scope", [])]
    expected_scope = f"skill/{target_skill_id}"
    if expected_scope not in scope:
        raise ValueError(f"retirement_target_outside_inventory:{target_skill_id}")
    base: dict[str, Any] = {
        "schema_version": RETIREMENT_RECEIPT_SCHEMA,
        "status": "retired",
        "target_skill_id": target_skill_id,
        "retirement_inventory_sha256": _sha256(RETIREMENT_INVENTORY),
        "current_authority_sha256": _authority_hashes(control_root),
        "residual_scan": {
            "forbidden_files": list(FORBIDDEN_V1_FILES),
            "forbidden_directories": list(FORBIDDEN_V1_DIRS),
            "forbid_control_root_python_cache": True,
            "residuals": [],
            "residual_count": 0,
        },
        "claim_boundary": RETIREMENT_CLAIM_BOUNDARY,
    }
    receipt_id = f"retirement-{_canonical_sha256(base)[:24]}"
    receipt = {**base, "receipt_id": receipt_id}
    receipt["receipt_hash"] = _canonical_sha256(receipt)
    return receipt


def retirement_receipt_path(target_skill_id: str) -> Path:
    return RETIREMENT_RECEIPT_ROOT / f"{target_skill_id}.json"


def write_retirement_receipt(
    skill_root: Path,
    target_skill_id: str,
    receipt_path: Path | None = None,
) -> dict[str, Any]:
    receipt = build_retirement_receipt(skill_root, target_skill_id)
    path = receipt_path or retirement_receipt_path(target_skill_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(_canonical_bytes(receipt))
    os.replace(temporary, path)
    return receipt


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _check_package_identity(expected_version: str = "") -> dict[str, Any]:
    module = importlib.import_module(PACKAGE_NAME)
    module_path = Path(module.__file__).resolve()
    metadata_version = importlib.metadata.version(PACKAGE_NAME)
    module_version = str(getattr(module, "__version__", ""))
    return {
        "check": "canonical_package_identity",
        "ok": (
            metadata_version == module_version
            and (not expected_version or module_version == expected_version)
            and _is_within(module_path, ROOT)
        ),
        "expected_version": expected_version,
        "metadata_version": metadata_version,
        "module_version": module_version,
        "module_path": str(module_path),
        "expected_repository_root": str(ROOT.resolve()),
    }


def _current_toolchain_identity() -> dict[str, str]:
    """Resolve the generator's sole direct-current frozen toolchain identity."""

    from upgrade_purpose_contracts import current_toolchain_identity

    return current_toolchain_identity(
        repository_root=ROOT,
        flowguard_project_path=FLOWGUARD_PROJECT_PATH,
    )


def _declared_toolchain_identity(
    expected_identity: Mapping[str, str],
) -> dict[str, str]:
    mesh = json.loads(SUITE_MESH_PATH.read_text(encoding="utf-8"))
    declared = mesh.get("toolchain_identity")
    if not isinstance(declared, Mapping):
        raise ValueError("toolchain_identity_missing")
    expected = {str(key): str(value) for key, value in expected_identity.items()}
    if not expected:
        raise ValueError("current_toolchain_identity_empty")
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in declared.items()):
        raise ValueError("toolchain_identity_values_wrong")
    actual_keys = set(declared)
    expected_keys = set(expected)
    if actual_keys != expected_keys:
        raise ValueError(
            "toolchain_identity_fields_wrong:"
            f"missing={sorted(expected_keys - actual_keys)}:"
            f"extra={sorted(actual_keys - expected_keys)}"
        )
    return {key: declared[key] for key in sorted(expected_keys)}


def _check_toolchain_identity() -> dict[str, Any]:
    findings: list[str] = []
    try:
        current = _current_toolchain_identity()
        declared = _declared_toolchain_identity(current)
        source = dict(current)
        observed = dict(current)
        if declared != current:
            findings.append("declared_toolchain_identity_stale")
    except (
        ImportError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        declared = {}
        source = {}
        observed = {}
        findings.append(f"toolchain_identity_unreadable:{type(exc).__name__}:{exc}")
    return {
        "ok": not findings,
        "status": "pass" if not findings else "blocked",
        "declared": declared,
        "source": source,
        "observed": observed,
        "findings": findings,
    }


def _residuals(control_root: Path) -> list[str]:
    found = [
        relative
        for relative in FORBIDDEN_V1_FILES
        if (control_root / relative).is_file()
    ]
    for relative in FORBIDDEN_V1_DIRS:
        directory = control_root / relative
        if directory.is_dir() and any(path.is_file() for path in directory.rglob("*")):
            found.append(f"{relative}/**")
    if any(
        path.is_file()
        for cache in control_root.rglob("__pycache__")
        for path in cache.rglob("*")
    ):
        found.append("**/__pycache__/**")
    return sorted(found)


def _retirement_receipt_status(
    control_root: Path,
    target_skill_id: str,
    receipt_path: Path | None = None,
) -> dict[str, Any]:
    path = receipt_path or retirement_receipt_path(target_skill_id)
    try:
        current_inventory = _receipt_inventory()
        current_inventory_hash = _sha256(RETIREMENT_INVENTORY)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "ok": False,
            "path": str(path),
            "reason": f"retirement_inventory_unreadable:{type(exc).__name__}",
        }
    if not path.is_file():
        return {"ok": False, "path": str(path), "reason": "expanded_scope_retirement_receipt_missing"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "path": str(path), "reason": f"invalid_retirement_receipt:{exc}"}
    findings: list[str] = []
    if payload.get("schema_version") != RETIREMENT_RECEIPT_SCHEMA:
        findings.append("retirement_receipt_schema_wrong")
    if payload.get("status") != "retired" or payload.get("target_skill_id") != target_skill_id:
        findings.append("retirement_receipt_identity_wrong")
    if payload.get("retirement_inventory_sha256") != current_inventory_hash:
        findings.append("retirement_inventory_stale")
    if f"skill/{target_skill_id}" not in current_inventory.get("scope", []):
        findings.append("retirement_target_outside_inventory")
    if payload.get("current_authority_sha256") != _authority_hashes(control_root):
        findings.append("retirement_current_authority_stale")
    residual_scan = payload.get("residual_scan")
    expected_scan = {
        "forbidden_files": list(FORBIDDEN_V1_FILES),
        "forbidden_directories": list(FORBIDDEN_V1_DIRS),
        "forbid_control_root_python_cache": True,
        "residuals": [],
        "residual_count": 0,
    }
    if residual_scan != expected_scan:
        findings.append("retirement_residual_scan_invalid")
    if payload.get("claim_boundary") != RETIREMENT_CLAIM_BOUNDARY:
        findings.append("retirement_claim_boundary_wrong")
    without_hash = {key: value for key, value in payload.items() if key != "receipt_hash"}
    if payload.get("receipt_hash") != _canonical_sha256(without_hash):
        findings.append("retirement_receipt_hash_mismatch")
    base = {
        key: value
        for key, value in payload.items()
        if key not in {"receipt_id", "receipt_hash"}
    }
    if payload.get("receipt_id") != f"retirement-{_canonical_sha256(base)[:24]}":
        findings.append("retirement_receipt_id_mismatch")
    ok = not findings
    return {
        "ok": ok,
        "path": str(path),
        "receipt_id": payload.get("receipt_id"),
        "receipt_hash": payload.get("receipt_hash"),
        "target_skill_id": payload.get("target_skill_id"),
        "residual_count": payload.get("residual_scan", {}).get("residual_count"),
        "findings": findings,
    }


def _authority_status(
    skill_root: Path,
    target_skill_id: str,
    receipt_path: Path | None = None,
) -> dict[str, Any]:
    control_root = skill_root / ".skillguard"
    missing = [
        relative
        for relative in V2_AUTHORITY_FILES
        if not (control_root / relative).is_file()
    ]
    residuals = _residuals(control_root)
    retirement = _retirement_receipt_status(control_root, target_skill_id, receipt_path)
    return {
        "ok": not missing and not residuals and retirement["ok"],
        "skill_root": str(skill_root),
        "missing_v2_authority": missing,
        "former_v1_residuals": residuals,
        "retirement_receipt": retirement,
    }


def _skill_status(
    target_skill_id: str,
    source_relative: str,
    installed_name: str,
    installation_member: Mapping[str, Any] | None,
) -> dict[str, Any]:
    source_skill = (ROOT / source_relative).resolve()
    receipt = retirement_receipt_path(target_skill_id)
    source = _authority_status(source_skill, target_skill_id, receipt)
    if installation_member is None:
        installed = {
            "skill_id": installed_name,
            "ok": False,
            "status": "blocked",
            "reasons": ["shared_installation_audit_member_missing"],
        }
    else:
        installed = dict(installation_member)
    return {
        "target_skill_id": target_skill_id,
        "ok": bool(source.get("ok")) and bool(installed.get("ok")),
        "source": source,
        "installed": installed,
        "source_installed_consumer_parity": installed,
    }


def main() -> int:
    toolchain = _check_toolchain_identity()
    expected_version = str(toolchain.get("declared", {}).get("physicsguard_version", ""))
    try:
        package = _machine_mapping(
            _check_package_identity(expected_version),
            "package_identity_result",
        )
        if type(package.get("ok")) is not bool:
            raise TypeError("package_identity_ok_not_boolean")
    except Exception as exc:
        package = _blocked_package_identity(expected_version, exc)
    try:
        installation_audit = _machine_mapping(
            check_installed_skills(HOME_SKILLS),
            "shared_installation_audit_result",
        )
        if type(installation_audit.get("ok")) is not bool:
            raise TypeError("shared_installation_audit_ok_not_boolean")
        if type(installation_audit.get("member_results")) is not list:
            raise TypeError("shared_installation_audit_member_results_not_list")
        if type(installation_audit.get("findings")) is not list:
            raise TypeError("shared_installation_audit_findings_not_list")
        if not all(
            isinstance(row, Mapping)
            for row in installation_audit["member_results"]
        ):
            raise TypeError("shared_installation_audit_member_not_object")
    except Exception as exc:
        installation_audit = blocked_installed_skill_audit(
            installed_root=HOME_SKILLS,
            repository_root=ROOT,
            finding_type="shared_installation_audit_unavailable",
            detail=_exception_detail(exc),
        )
    installation_by_id = {
        str(row.get("skill_id", "")): row
        for row in installation_audit.get("member_results", [])
        if isinstance(row, Mapping)
    }
    skills = [
        _skill_status(*row, installation_by_id.get(row[0]))
        for row in SKILLS
    ]
    ok = (
        toolchain["ok"]
        and package["ok"]
        and bool(installation_audit.get("ok"))
        and all(skill["ok"] for skill in skills)
    )
    result = {
        "artifact_kind": "guard_family_v2_runtime_authority_audit",
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "toolchain": toolchain,
        "package": package,
        "skills": skills,
        "consumer_installation_audit": installation_audit,
        "installation_currentness": {
            "status": "external_exact_receipt_required",
            "claim_boundary": "Byte parity here does not prove issuance, terminal closure, parent consumption, or installation-currentness replay.",
        },
        "claim_boundary": "Pass proves canonical package identity, exact author-side V2 authority-file presence, expanded former-V1 residual absence, expanded-scope retirement receipt presence, and exact clean consumer parity. It executes no native owner and cannot close production by itself.",
    }
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )
    return 0 if ok else 1


def _machine_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label}_not_object")
    candidate = dict(value)
    try:
        json.dumps(candidate, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TypeError(f"{label}_not_json_serializable:{type(exc).__name__}") from exc
    return candidate


def _blocked_package_identity(
    expected_version: str,
    exc: Exception,
) -> dict[str, Any]:
    return {
        "check": "canonical_package_identity",
        "ok": False,
        "status": "blocked",
        "expected_version": expected_version,
        "metadata_version": None,
        "module_version": None,
        "module_path": None,
        "expected_repository_root": str(ROOT.resolve()),
        "findings": [f"package_identity_unavailable:{_exception_detail(exc)}"],
    }


def _exception_detail(exc: Exception) -> str:
    try:
        detail = str(exc)
    except Exception:
        detail = "unprintable_exception"
    return f"{type(exc).__name__}:{detail}"


if __name__ == "__main__":
    raise SystemExit(main())
