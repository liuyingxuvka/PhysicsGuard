from __future__ import annotations

import ast
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill"
TEST_MESH_CHECKER_PATH = ROOT / "scripts" / "check_physicsguard_test_mesh.py"
UPGRADE_GENERATOR_PATH = ROOT / "scripts" / "upgrade_purpose_contracts.py"






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
