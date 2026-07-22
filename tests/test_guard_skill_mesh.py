from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / ".flowguard/check_physicsguard_skill_suite_mesh.py"
MESH = ROOT / ".flowguard/physicsguard_skill_suite_mesh.json"
SKILL_ROOT = ROOT / "skill"
REPORT = ROOT / "scripts/report_physicsguard_skill_suite.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("guard_skill_mesh_checker_under_test", CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_report():
    spec = importlib.util.spec_from_file_location(
        "physicsguard_skill_suite_report_under_test", REPORT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_mesh_and_identity_known_bads() -> None:
    checker = _load_checker()
    mesh = json.loads(MESH.read_text(encoding="utf-8"))
    result = checker.check_mesh(mesh)
    assert result["structure_status"] == "pass"
    known_bads = checker.known_bad_results(mesh)
    assert known_bads
    assert set(known_bads.values()) == {"blocked"}
    assert known_bads["skillguard_owns_semantics"] == "blocked"
    assert known_bads["selectable_mode"] == "blocked"
    assert known_bads["candidate_before_purpose"] == "blocked"
    assert known_bads["missing_member"] == "blocked"
    assert known_bads["receipt_consuming_summary"] == "blocked"
    assert known_bads["copied_editable_simulator"] == "blocked"


def test_native_integration_identity_mutations_block(tmp_path: Path) -> None:
    checker = _load_checker()
    target = "physicsguard-project-adoption"
    target_root = tmp_path / "skill" / target
    shutil.copytree(SKILL_ROOT / target, target_root)
    checker.ROOT = tmp_path
    source_path = target_root / ".skillguard/contract-source.json"
    original = json.loads(source_path.read_text(encoding="utf-8"))
    cases = (
        ("native_check_binding_inventory_wrong", lambda value: value["native_check_bindings"][0].update(required=False)),
        ("native_route_binding_wrong", lambda value: value["native_route_bindings"][0].update(required_before_closure=False)),
        ("parallel_execution_route_not_forbidden", lambda value: value.update(may_define_parallel_execution_route=True)),
        ("native_route_identity_wrong", lambda value: value.update(default_route_id="route:foreign")),
        ("depth_profile_check_inventory_wrong", lambda value: value["depth_profile"]["native_check_ids"].pop()),
    )
    for expected_code, mutate in cases:
        source = copy.deepcopy(original)
        mutate(source)
        source_path.write_text(
            json.dumps(source, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        findings: list[dict[str, str]] = []
        checker._check_target_contract(target, findings)
        assert expected_code in {row["code"] for row in findings}


def test_source_structure_report_is_non_authoritative_and_receipt_free() -> None:
    report = _load_report().build_report(ROOT)
    assert report["structure_status"] == "pass"
    assert report["authoritative"] is False
    assert report["maintenance_unit_id"] == "unit:physicsguard-family"
    assert report["member_count"] == 10
    assert report["declared_check_count"] == 74
    assert report["findings"] == []
    assert set(report) == {
        "artifact_kind",
        "authoritative",
        "structure_status",
        "maintenance_unit_id",
        "member_count",
        "declared_check_count",
        "members",
        "findings",
        "claim_boundary",
    }
    assert all(row["maintenance_unit_id"] == "unit:physicsguard-family" for row in report["members"])
    assert all(row["declared_check_count"] == row["execution_owner_count"] for row in report["members"])


def test_source_structure_report_blocks_inventory_tamper_without_run_store(
    tmp_path: Path,
) -> None:
    (tmp_path / ".skillguard").mkdir()
    (tmp_path / ".flowguard").mkdir()
    shutil.copyfile(ROOT / ".skillguard/author-project.json", tmp_path / ".skillguard/author-project.json")
    shutil.copyfile(MESH, tmp_path / ".flowguard/physicsguard_skill_suite_mesh.json")
    for source in SKILL_ROOT.glob("physicsguard-*/.skillguard/contract-source.json"):
        target = tmp_path / source.relative_to(ROOT)
        target.parent.mkdir(parents=True)
        shutil.copyfile(source, target)
    manifest_path = tmp_path / ".skillguard/author-project.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["managed_skills"] = manifest["managed_skills"][:-1]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = _load_report().build_report(tmp_path)

    assert report["structure_status"] == "blocked"
    assert report["authoritative"] is False
    assert "author_member_inventory_mismatch" in report["findings"]
    assert not (tmp_path / "work").exists()


def test_every_physics_skill_prompt_requires_exact_per_obligation_evidence() -> None:
    skill_files = sorted(SKILL_ROOT.glob("*/SKILL.md"))
    assert len(skill_files) == 10
    for path in skill_files:
        raw_prompt = path.read_text(encoding="utf-8")
        assert "\n+Keep only" not in raw_prompt, path
        prompt = " ".join(raw_prompt.split())
        assert "not per-obligation evidence" in prompt, path
        assert "family baseline regression" in prompt, path
        assert "AI must choose the purpose and one or more concrete prevented" in prompt, path
        assert ".physicsguard/model-purpose/<model-id>/contract.json" in prompt, path
        assert "There is one mandatory route and no selectable mode" in prompt, path
        assert "`physicsguard.guard_model_contract` is the PhysicsGuard-native verifier" in prompt, path
        assert "python -m physicsguard.skill_execution_depth" in prompt, path
        assert "a missing package is a visible blocker and there is no bundled fallback" in prompt, path
        assert "never replaces current task evidence or PhysicsGuard domain judgment" in prompt, path
        assert "SkillGuard" not in raw_prompt, path
