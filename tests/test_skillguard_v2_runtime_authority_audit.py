from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import sys

import physicsguard


ROOT = Path(__file__).resolve().parents[1]


def _source_file_hash(path: Path) -> str:
    body = path.read_bytes()
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        pass
    else:
        body = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(body).hexdigest().upper()
SCRIPT = ROOT / "scripts" / "verify_guard_simulation_readiness.py"
PRIMARY_ROOT = ROOT / "skill" / "physicsguard-model-dataset-validation"
SKILLGUARD_SCRIPTS = Path.home() / ".codex" / "skills" / "skillguard" / "scripts"
if str(SKILLGUARD_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILLGUARD_SCRIPTS))

from skillguard_v2.consumer_distribution import build_consumer_distribution


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("guard_v2_authority_audit_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_current_authority(root: Path, target_skill_id: str, audit, receipt_path: Path) -> None:
    control = root / ".skillguard"
    control.mkdir(parents=True)
    (root / "SKILL.md").write_text("current prompt\n", encoding="utf-8")
    for name in ("contract-source.json", "compiled-contract.json", "check-manifest.json"):
        (control / name).write_text(json.dumps({"name": name}), encoding="utf-8")
    audit.write_retirement_receipt(root, target_skill_id, receipt_path)


def test_expanded_residual_scan_blocks_generic_checker_and_mutable_report(tmp_path: Path) -> None:
    audit = _load_audit_module()
    skill = tmp_path / "skill"
    receipt_path = tmp_path / "retirement.json"
    target_skill_id = "physicsguard-ai-debugging"
    _write_current_authority(skill, target_skill_id, audit, receipt_path)
    assert audit._authority_status(skill, target_skill_id, receipt_path)["ok"] is True

    generic = skill / ".skillguard" / "checks" / "check_route.py"
    generic.parent.mkdir(parents=True)
    generic.write_text("raise SystemExit(0)\n", encoding="utf-8")
    status = audit._authority_status(skill, target_skill_id, receipt_path)
    assert status["ok"] is False
    assert "checks/check_route.py" in status["former_v1_residuals"]

    generic.unlink()
    mutable = skill / ".skillguard" / "reports" / "current_closure.json"
    mutable.parent.mkdir(parents=True)
    mutable.write_text("{}\n", encoding="utf-8")
    status = audit._authority_status(skill, target_skill_id, receipt_path)
    assert status["ok"] is False
    assert "reports/**" in status["former_v1_residuals"]


def test_narrow_receipt_cannot_hide_residual_and_consumer_parity_is_exact(
    tmp_path: Path,
) -> None:
    audit = _load_audit_module()
    source = tmp_path / "source"
    installed = tmp_path / "installed"
    receipt_path = tmp_path / "retirement.json"
    target_skill_id = "physicsguard-ai-debugging"
    _write_current_authority(source, target_skill_id, audit, receipt_path)
    contract = json.loads(
        (PRIMARY_ROOT / ".skillguard" / "compiled-contract.json").read_text(
            encoding="utf-8"
        )
    )
    result = build_consumer_distribution(PRIMARY_ROOT, installed, contract)
    assert result["status"] == "passed"
    assert audit._consumer_status(
        PRIMARY_ROOT, installed, PRIMARY_ROOT.name
    )["ok"] is True

    installed.joinpath("SKILL.md").write_text("changed prompt\n", encoding="utf-8")
    assert audit._consumer_status(
        PRIMARY_ROOT, installed, PRIMARY_ROOT.name
    )["ok"] is False

    residual = source / ".skillguard" / "skillguard_manifest.json"
    residual.write_text("{}\n", encoding="utf-8")
    status = audit._authority_status(source, target_skill_id, receipt_path)
    assert status["retirement_receipt"]["ok"] is True
    assert status["ok"] is False
    assert "skillguard_manifest.json" in status["former_v1_residuals"]


def test_retirement_receipt_hash_and_authority_freshness_are_enforced(tmp_path: Path) -> None:
    audit = _load_audit_module()
    skill = tmp_path / "skill"
    receipt_path = tmp_path / "retirement.json"
    target_skill_id = "physicsguard-ai-debugging"
    _write_current_authority(skill, target_skill_id, audit, receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["receipt_hash"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    status = audit._authority_status(skill, target_skill_id, receipt_path)
    assert status["ok"] is False
    assert "retirement_receipt_hash_mismatch" in status["retirement_receipt"]["findings"]

    audit.write_retirement_receipt(skill, target_skill_id, receipt_path)
    (skill / ".skillguard/compiled-contract.json").write_text("{}\n", encoding="utf-8")
    status = audit._authority_status(skill, target_skill_id, receipt_path)
    assert status["ok"] is False
    assert "retirement_current_authority_stale" in status["retirement_receipt"]["findings"]


def test_primary_contract_binds_physicsguard_owned_proofs_without_old_wire() -> None:
    contract = json.loads(
        (PRIMARY_ROOT / ".skillguard/contract-source.json").read_text(encoding="utf-8")
    )
    runtime_authority_paths = {
        "src/physicsguard/guard_model_contract.py",
        "src/physicsguard/skill_execution_depth.py",
        "skill/physicsguard-model-dataset-validation/runtime-requirements.json",
    }
    assert runtime_authority_paths <= set(contract["implementation_paths"])
    assert not (PRIMARY_ROOT / "runtime").exists()
    assert not (PRIMARY_ROOT / "guard-model/verify.py").exists()
    requirement = json.loads(
        (PRIMARY_ROOT / "runtime-requirements.json").read_text(encoding="utf-8")
    )
    assert requirement["package_name"] == "physicsguard"
    assert requirement["package_version"] == physicsguard.__version__
    assert requirement["missing_dependency_behavior"] == "fail_visible"
    assert requirement["fallback"] is False
    assert not {
        "calibration",
    }.intersection(contract)
    guard = json.loads(
        (PRIMARY_ROOT / "guard-model/contract.json").read_text(encoding="utf-8")
    )
    owner = str(guard["native_owner_id"])
    route = str(guard["native_route_id"])
    check_ids = [str(row["check_id"]) for row in contract["checks"]]
    assert contract["integration_mode"] == "native-integrated"
    assert contract["native_route_owner"] == owner
    assert contract["default_route_id"] == route
    assert contract["native_route_bindings"] == [
        {
            "binding_id": "native:physicsguard-model-dataset-validation:current",
            "native_route_id": route,
            "required_before_closure": True,
            "source": "guard-model/contract.json",
        }
    ]
    assert contract["may_define_parallel_execution_route"] is False
    assert contract["may_define_skillguard_runtime_route"] is False
    assert contract["native_check_bindings"] == [
        {
            "binding_id": (
                "native-check:physicsguard-model-dataset-validation:"
                f"{check_id.replace(':', '-')}"
            ),
            "evidence_source": "physicsguard.guard_model_contract",
            "native_check_id": check_id,
            "required": True,
        }
        for check_id in check_ids
    ]
    depth = contract["depth_profile"]
    assert depth["native_owner_id"] == owner
    assert depth["native_route_ids"] == [route]
    assert depth["native_check_ids"] == check_ids
    assert depth["enforcement_level"] == "enforced"
    assert depth["required_closure_profiles"] == ["enforced"]
    skill_prefix = "skill/physicsguard-model-dataset-validation"
    contract_paths = {
        f"{skill_prefix}/guard-model/contract.json",
        f"{skill_prefix}/guard-model/oracles.json",
        f"{skill_prefix}/guard-model/known-good.json",
        f"{skill_prefix}/guard-model/known-bad.json",
    }
    candidate_path = f"{skill_prefix}/guard-model/candidate.json"
    guard_paths = {*contract_paths, candidate_path}
    assert guard_paths <= set(contract["implementation_paths"])
    for check in contract["checks"]:
        assert not {
            "depth_evidence_protocol",
            "calibration_evidence_protocol",
            "depth_evidence_output",
            "calibration_evidence_output",
        }.intersection(check)
        selectors = {
            str(item.get("path"))
            for item in check.get("input_selectors", [])
            if isinstance(item, dict) and item.get("kind") == "path"
        }
        assert contract_paths <= selectors
        if str(check["check_id"]).endswith(":family-baseline-contract"):
            assert candidate_path not in selectors
        else:
            assert guard_paths <= selectors
        assert runtime_authority_paths <= selectors
        assert check["args"][:2] == ["-m", "physicsguard.guard_model_contract"]
