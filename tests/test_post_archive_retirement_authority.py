from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = ROOT / "scripts" / "verify_guard_simulation_readiness.py"
CURRENT_INVENTORY = ROOT / ".flowguard" / "physicsguard_v1_retirement_inventory.json"
PARENT_SOURCE = ROOT / ".flowguard" / "skillguard-parent" / ".skillguard" / "contract-source.json"
RETIRED_ACTIVE_INVENTORY = (
    ROOT
    / "openspec"
    / "changes"
    / "migrate-physicsguard-skill-suite-to-skillguard-v2"
    / "v1-retirement-inventory.json"
)


def _load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "physicsguard_post_archive_audit_under_test", AUDIT_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_inventory_is_project_owned_after_migration_archive() -> None:
    audit = _load_audit_module()
    inventory = json.loads(CURRENT_INVENTORY.read_text(encoding="utf-8"))

    assert audit.RETIREMENT_INVENTORY == CURRENT_INVENTORY
    assert RETIRED_ACTIVE_INVENTORY.exists() is False
    assert "openspec" not in audit.RETIREMENT_INVENTORY.parts
    assert inventory["fallback_allowed"] is False
    assert inventory["scope"] == [f"skill/{row[0]}" for row in audit.SKILLS]


def test_missing_current_inventory_blocks_without_archive_fallback(
    tmp_path: Path,
) -> None:
    audit = _load_audit_module()
    audit.RETIREMENT_INVENTORY = tmp_path / "missing-current-authority.json"
    receipt = ROOT / ".flowguard" / "retirement-receipts" / "physicsguard-ai-debugging.json"

    status = audit._retirement_receipt_status(
        ROOT / "skill" / "physicsguard-ai-debugging" / ".skillguard",
        "physicsguard-ai-debugging",
        receipt,
    )

    assert status["ok"] is False
    assert status["reason"] == "retirement_inventory_unreadable:FileNotFoundError"
    with pytest.raises(FileNotFoundError):
        audit.build_retirement_receipt(
            ROOT / "skill" / "physicsguard-ai-debugging",
            "physicsguard-ai-debugging",
        )


def test_parent_declares_every_transitive_retirement_input() -> None:
    source = json.loads(PARENT_SOURCE.read_text(encoding="utf-8"))
    required = {
        "scripts/verify_physicsguard_suite_parent.py",
        "scripts/verify_guard_simulation_readiness.py",
        ".flowguard/physicsguard_v1_retirement_inventory.json",
    }

    child_checks = [
        row
        for row in source["checks"]
        if row["check_id"].startswith("check:physicsguard-skill-suite-parent:consume:")
    ]
    assert len(child_checks) == 10
    for check in child_checks:
        selectors = {row["path"] for row in check["input_selectors"]}
        assert required <= selectors
    assert required <= set(source["implementation_paths"])
    assert "openspec/changes/" not in json.dumps(source)


def test_post_archive_runtime_retirement_audit_is_current() -> None:
    audit = _load_audit_module()
    skill_rows = [audit._skill_status(*row) for row in audit.SKILLS]
    assert all(row["ok"] for row in skill_rows), json.dumps(
        skill_rows,
        ensure_ascii=False,
        indent=2,
    )
