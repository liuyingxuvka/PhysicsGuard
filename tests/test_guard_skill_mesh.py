from __future__ import annotations

import copy
import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / ".flowguard/check_physicsguard_skill_suite_mesh.py"
MESH = ROOT / ".flowguard/physicsguard_skill_suite_mesh.json"
SKILL_ROOT = ROOT / "skill"
PARENT_INVENTORY = ROOT / ".flowguard/physicsguard_suite_parent_inventory.json"
PARENT_MANIFEST = ROOT / ".flowguard/skillguard-parent/.skillguard/check-manifest.json"
PARENT_VERIFY = ROOT / "scripts/verify_physicsguard_suite_parent.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("guard_skill_mesh_checker_under_test", CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_hash(value: object) -> str:
    body = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return hashlib.sha256(body).hexdigest().upper()


def test_current_mesh_and_identity_known_bads() -> None:
    checker = _load_checker()
    mesh = json.loads(MESH.read_text(encoding="utf-8"))
    result = checker.check_mesh(mesh)
    assert result["status"] == "pass"
    known_bads = checker.known_bad_results(mesh)
    assert known_bads
    assert set(known_bads.values()) == {"blocked"}
    assert known_bads["skillguard_owns_semantics"] == "blocked"
    assert known_bads["selectable_mode"] == "blocked"
    assert known_bads["candidate_before_purpose"] == "blocked"
    assert known_bads["missing_child"] == "blocked"
    assert known_bads["missing_primary"] == "blocked"


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
        ("native_default_route_wrong", lambda value: value.update(default_route_id="route:foreign")),
        ("depth_profile_identity_wrong", lambda value: value["depth_profile"]["native_check_ids"].pop()),
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


def test_parent_inventory_consumes_all_ten_children_without_child_execution() -> None:
    inventory = json.loads(PARENT_INVENTORY.read_text(encoding="utf-8"))
    manifest = json.loads(PARENT_MANIFEST.read_text(encoding="utf-8"))
    child_ids = [row["skill_id"] for row in inventory["children"]]
    assert len(child_ids) == 10
    assert len(set(child_ids)) == 10
    assert "physicsguard-model-dataset-validation" in child_ids
    assert len(manifest["checks"]) == 11
    commands = [" ".join([row["command"], *row["args"]]) for row in manifest["checks"]]
    assert all("guard-model/verify.py" not in command for command in commands)
    for skill_id in child_ids:
        assert sum(skill_id in command for command in commands) == 1


def test_parent_inventory_tamper_blocks_without_execution(tmp_path: Path) -> None:
    inventory = json.loads(PARENT_INVENTORY.read_text(encoding="utf-8"))
    inventory["children"] = inventory["children"][:-1]
    unsigned = {key: value for key, value in inventory.items() if key != "inventory_hash"}
    inventory["inventory_hash"] = _canonical_hash(unsigned)
    tampered = tmp_path / "tampered-parent-inventory.json"
    tampered.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(PARENT_VERIFY),
            "verify-suite",
            "--repository-root",
            str(ROOT),
            "--inventory",
            str(tampered),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    result = json.loads(completed.stdout)
    assert result["status"] == "blocked"
    assert result["execution_count"] == 0
    assert result["findings"] == ["parent_inventory_child_set_mismatch"]


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
        assert "`guard-model/verify.py` is the PhysicsGuard-native verifier" in prompt, path
        assert "never replaces current task evidence or PhysicsGuard domain judgment" in prompt, path
        assert "SkillGuard" not in raw_prompt, path
