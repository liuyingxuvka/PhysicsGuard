from __future__ import annotations

import ast
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill"
TEST_MESH_CHECKER_PATH = ROOT / "scripts" / "check_physicsguard_test_mesh.py"
UPGRADE_GENERATOR_PATH = ROOT / "scripts" / "upgrade_purpose_contracts.py"


def _load_test_mesh_checker():
    spec = importlib.util.spec_from_file_location(
        "physicsguard_test_mesh_checker_under_test", TEST_MESH_CHECKER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_family_test_mesh_has_one_complete_static_eligibility_audit() -> None:
    checker = _load_test_mesh_checker()
    generator = checker._load_generator()
    result = checker.audit(ROOT)

    assert result["status"] == "pass", result["findings"]
    assert result["maintenance_unit_id"] == "unit:physicsguard-family"
    assert result["member_count"] == 10
    assert result["check_owner_count"] == 85
    assert result["execution_count"] == 0
    assert result["plan_only_execution_status"] == "not_run"
    assert result["unknown_mapping_disposition"] == "block"
    assert {
        row["member_skill_id"]: row["check_owner_count"]
        for row in result["member_results"]
    } == checker.EXPECTED_OWNER_COUNTS
    assert all(
        row["plan_only_static_eligibility"] == "eligible"
        for row in result["member_results"]
    )

    projection = result["source_maintenance_projection"]
    assert set(projection["paths"]) == set(generator.FAMILY_MAINTENANCE_INPUTS)
    assert projection["semantic_owner_selection"] == [
        generator.FAMILY_MAINTENANCE_OWNER_ID
    ]
    assert result["family_maintenance_impact"]["direct_semantic_owner_ids"] == [
        generator.FAMILY_MAINTENANCE_OWNER_ID
    ]
    assert not list(SKILL_ROOT.glob("*/.skillguard/test-mesh.json"))


def test_skill_projection_generator_has_one_direct_current_target_writer() -> None:
    source = UPGRADE_GENERATOR_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    writer_definitions = sorted(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("upgrade_target")
    )
    writer_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "upgrade_target_current"
    ]

    assert writer_definitions == ["upgrade_target_current"]
    assert len(writer_calls) == 1
    assert ".skillguard/authority-templates" not in source
    assert "BEGIN MANAGED PURPOSE AND BLOCKABILITY" not in source
