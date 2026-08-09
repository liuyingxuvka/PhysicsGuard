from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import sys

import physicsguard
import pytest

from scripts.check_installed_physicsguard_skills import _consumer_projection_status
from scripts.physicsguard_skill_install_authority import load_skillguard_consumer_api
from scripts import upgrade_purpose_contracts as purpose_contract_generator


ROOT = Path(__file__).resolve().parents[1]
FULL_TOOLCHAIN_IDENTITY = {
    "physicsguard_version": "0.15.2",
    "physicsguard_authority_sha256": "sha256:physicsguard-authority",
    "flowguard_version": "0.68.7",
    "flowguard_schema_version": "1.0",
    "flowguard_package_tree_sha256": "sha256:flowguard-tree",
    "flowguard_direct_url_sha256": "sha256:flowguard-direct-url",
    "flowguard_authority_sha256": "sha256:flowguard-authority",
    "skillguard_version": "0.7.2",
    "skillguard_api_tree_sha256": "sha256:skillguard-api-tree",
    "skillguard_distribution_tree_sha256": "sha256:skillguard-distribution-tree",
    "skillguard_direct_url_sha256": "sha256:skillguard-direct-url",
    "skillguard_authority_sha256": "sha256:skillguard-authority",
}


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
    api = load_skillguard_consumer_api()
    assert _consumer_projection_status(
        PRIMARY_ROOT.name, PRIMARY_ROOT, installed, api
    )["ok"] is True

    installed.joinpath("SKILL.md").write_text("changed prompt\n", encoding="utf-8")
    assert _consumer_projection_status(
        PRIMARY_ROOT.name, PRIMARY_ROOT, installed, api
    )["ok"] is False
    assert not hasattr(audit, "_consumer_status")

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
    entry_governed_paths = {
        ".flowguard/check_physicsguard_skill_suite_mesh.py",
        ".flowguard/model-regression-manifest.json",
        ".flowguard/physicsguard_skill_prompt_load_graph.json",
        ".flowguard/physicsguard_skill_suite_mesh.json",
        "VERSION",
        "pyproject.toml",
        "src/physicsguard/__init__.py",
        "scripts/check_installed_physicsguard_skills.py",
        "scripts/verify_guard_simulation_readiness.py",
        "tests/test_guard_skill_mesh.py",
        "tests/test_installed_skill_sync.py",
        "tests/test_physicsguard_skill_entry_loading.py",
        "tests/test_post_archive_retirement_authority.py",
        "tests/test_skillguard_v2_runtime_authority_audit.py",
        "tests/test_version_consistency.py",
    }
    assert runtime_authority_paths <= set(contract["implementation_paths"])
    assert entry_governed_paths <= set(contract["implementation_paths"])
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
            "evidence_source": (
                "physicsguard.task_local_revision"
                if check_id.endswith(":task-local-model-deepening")
                else "physicsguard.guard_model_contract"
            ),
            "native_check_id": check_id,
            "required": True,
        }
        for check_id in check_ids
    ]
    depth = contract["depth_profile"]
    assert depth["native_owner_id"] == owner
    assert depth["native_route_ids"] == [route]
    assert depth["native_check_ids"] == check_ids
    assert depth["model_deepening_check_id"] == (
        "check:physicsguard-model-dataset-validation:task-local-model-deepening"
    )
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
        is_task_model = str(check["check_id"]).endswith(
            ":task-local-model-deepening"
        )
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
        if is_task_model:
            assert {
                f"{skill_prefix}/SKILL.md",
                "src/physicsguard/schema/task_local_revision.py",
                "src/physicsguard/core/task_local_revision.py",
                "src/physicsguard/cli.py",
                "tests/test_task_local_revision.py",
                "tests/test_physicsguard_skill_prompts.py",
            } <= selectors
            assert entry_governed_paths <= selectors
            assert check["args"][:2] == ["-m", "pytest"]
        else:
            assert contract_paths <= selectors
            if str(check["check_id"]).endswith(":family-baseline-contract"):
                assert candidate_path not in selectors
            else:
                assert guard_paths <= selectors
            assert runtime_authority_paths <= selectors
            assert check["args"][:2] == ["-m", "physicsguard.guard_model_contract"]
            skill_root_index = check["args"].index("--skill-root") + 1
            assert check["args"][skill_root_index] == skill_prefix


def test_readiness_declares_the_generator_frozen_toolchain_identity() -> None:
    audit = _load_audit_module()
    expected = purpose_contract_generator.current_toolchain_identity(
        repository_root=ROOT,
        flowguard_project_path=ROOT / ".flowguard" / "project.toml",
    )
    assert audit._declared_toolchain_identity(expected) == expected


def test_readiness_accepts_the_complete_generator_identity_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit = _load_audit_module()
    mesh_path = tmp_path / "suite-mesh.json"
    mesh_path.write_text(
        json.dumps({"toolchain_identity": FULL_TOOLCHAIN_IDENTITY}),
        encoding="utf-8",
    )
    audit.SUITE_MESH_PATH = mesh_path

    assert audit._declared_toolchain_identity(FULL_TOOLCHAIN_IDENTITY) == {
        key: FULL_TOOLCHAIN_IDENTITY[key]
        for key in sorted(FULL_TOOLCHAIN_IDENTITY)
    }
    monkeypatch.setattr(
        audit,
        "_current_toolchain_identity",
        lambda: dict(FULL_TOOLCHAIN_IDENTITY),
    )
    result = audit._check_toolchain_identity()
    assert result["ok"] is True
    assert result["status"] == "pass"
    assert result["declared"] == FULL_TOOLCHAIN_IDENTITY
    assert result["source"] == FULL_TOOLCHAIN_IDENTITY
    assert result["observed"] == FULL_TOOLCHAIN_IDENTITY


@pytest.mark.parametrize(
    ("mutate", "finding"),
    (
        (
            lambda value: value.pop("flowguard_authority_sha256"),
            "missing=.*flowguard_authority_sha256",
        ),
        (
            lambda value: value.update({"historical_version_alias": "retired"}),
            "extra=.*historical_version_alias",
        ),
    ),
)
def test_readiness_rejects_missing_or_unknown_identity_fields(
    tmp_path: Path,
    mutate,
    finding: str,
) -> None:
    audit = _load_audit_module()
    declared = dict(FULL_TOOLCHAIN_IDENTITY)
    mutate(declared)
    mesh_path = tmp_path / "suite-mesh.json"
    mesh_path.write_text(
        json.dumps({"toolchain_identity": declared}),
        encoding="utf-8",
    )
    audit.SUITE_MESH_PATH = mesh_path

    with pytest.raises(ValueError, match=finding):
        audit._declared_toolchain_identity(FULL_TOOLCHAIN_IDENTITY)


def test_readiness_blocks_project_import_drift_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit = _load_audit_module()

    def drifted_identity() -> dict[str, str]:
        raise RuntimeError(
            "flowguard_authority_mismatch:project=0.68.6:installed=0.68.7"
        )

    monkeypatch.setattr(audit, "_current_toolchain_identity", drifted_identity)

    result = audit._check_toolchain_identity()

    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert result["declared"] == {}
    assert result["findings"] == [
        "toolchain_identity_unreadable:RuntimeError:"
        "flowguard_authority_mismatch:project=0.68.6:installed=0.68.7"
    ]


def test_readiness_package_exception_is_one_canonical_blocked_result(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit = _load_audit_module()
    monkeypatch.setattr(
        audit,
        "_check_toolchain_identity",
        lambda: {
            "ok": True,
            "declared": {"physicsguard_version": physicsguard.__version__},
        },
    )

    def fail_package(_expected_version: str):
        raise RuntimeError("fixture-package-failure")

    monkeypatch.setattr(audit, "_check_package_identity", fail_package)
    monkeypatch.setattr(
        audit,
        "check_installed_skills",
        lambda _root: audit.blocked_installed_skill_audit(
            installed_root=audit.HOME_SKILLS,
            repository_root=audit.ROOT,
            finding_type="fixture_shared_block",
            detail="fixture",
        ),
    )

    exit_code = audit.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert captured.err == ""
    assert payload["ok"] is False
    assert payload["status"] == "blocked"
    assert payload["package"]["status"] == "blocked"
    assert payload["package"]["findings"] == [
        "package_identity_unavailable:RuntimeError:fixture-package-failure"
    ]


def test_readiness_shared_audit_exception_is_one_canonical_blocked_result(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit = _load_audit_module()
    monkeypatch.setattr(
        audit,
        "_check_toolchain_identity",
        lambda: {
            "ok": True,
            "declared": {"physicsguard_version": physicsguard.__version__},
        },
    )
    monkeypatch.setattr(
        audit,
        "_check_package_identity",
        lambda _expected_version: {
            "check": "canonical_package_identity",
            "ok": True,
        },
    )

    def fail_shared(_root: Path):
        raise RuntimeError("fixture-shared-audit-failure")

    monkeypatch.setattr(audit, "check_installed_skills", fail_shared)

    exit_code = audit.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert captured.err == ""
    assert payload["status"] == "blocked"
    shared = payload["consumer_installation_audit"]
    assert shared["schema_version"] == "physicsguard.installed_skill_audit.v1"
    assert shared["status"] == "blocked"
    assert shared["member_results"] == []
    assert shared["findings"] == [
        {
            "severity": "error",
            "type": "shared_installation_audit_unavailable",
            "detail": "RuntimeError:fixture-shared-audit-failure",
        }
    ]
