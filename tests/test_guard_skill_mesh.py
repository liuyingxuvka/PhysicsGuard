from __future__ import annotations
import json
from pathlib import Path
import shutil
from scripts.report_physicsguard_skill_suite import build_report
ROOT = Path(__file__).resolve().parents[1]

def test_source_structure_report_is_non_authoritative_and_receipt_free() -> None:
    before = {str(p): p.stat().st_mtime_ns for p in (ROOT / "skill").rglob("*") if p.is_file()}
    report = build_report(ROOT)
    assert report["structure_status"] == "pass", report["findings"]
    assert report["member_count"] == 10
    assert report["authoritative"] is False
    assert before == {str(p): p.stat().st_mtime_ns for p in (ROOT / "skill").rglob("*") if p.is_file()}

def test_source_structure_report_blocks_inventory_tamper_without_run_store(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "skill", tmp_path / "skill")
    path = tmp_path / "skill/physicsguard-ai-debugging/references/route-capsule.json"
    data = json.loads(path.read_text())
    data["target_skill_id"] = "foreign-route"
    path.write_text(json.dumps(data))
    report = build_report(tmp_path)
    assert report["structure_status"] == "blocked"
    assert any("capsule_skill_mismatch" in f for f in report["findings"])
