from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = ROOT / "scripts" / "verify_guard_simulation_readiness.py"
CURRENT_INVENTORY = ROOT / ".flowguard" / "physicsguard_v1_retirement_inventory.json"
STRUCTURE_REPORT = ROOT / "scripts" / "report_physicsguard_skill_suite.py"
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


def test_retired_parent_authority_is_absent_and_summary_is_source_only() -> None:
    retired = (
        ROOT / ".flowguard" / "skillguard-parent",
        ROOT / ".flowguard" / "physicsguard_suite_parent_inventory.json",
        ROOT / "scripts" / "generate_physicsguard_suite_parent_contract.py",
        ROOT / "scripts" / "verify_physicsguard_suite_parent.py",
    )
    assert all(not path.exists() for path in retired)

    spec = importlib.util.spec_from_file_location(
        "physicsguard_structure_report_under_test", STRUCTURE_REPORT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.build_report(ROOT)

    assert report["structure_status"] == "pass"
    assert report["authoritative"] is False
    assert report["maintenance_unit_id"] == "unit:physicsguard-family"
    assert report["member_count"] == 10
    assert report["declared_check_count"] == 74


def test_post_archive_source_retirement_audit_is_current_without_install_claim() -> None:
    audit = _load_audit_module()
    source_rows = [
        audit._authority_status(
            ROOT / source_relative,
            target_skill_id,
            audit.retirement_receipt_path(target_skill_id),
        )
        for target_skill_id, source_relative, _installed_name in audit.SKILLS
    ]
    assert all(row["ok"] for row in source_rows), json.dumps(
        source_rows,
        ensure_ascii=False,
        indent=2,
    )
