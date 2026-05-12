from __future__ import annotations

from pathlib import Path

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec


ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "examples" / "hierarchical" / "process_industry"


def run_template(name: str):
    spec = load_hierarchical_audit_spec(PROC / name)
    return HierarchicalAuditRunner(spec).run(top_n_residuals=20, top_n_blocks=10)


def test_process_industry_level_0_template_passes() -> None:
    report = run_template("level_0_unit_operations_balance.yaml")
    assert report.optimization_success
    assert report.audit_pass
    assert report.top_blocks[0].block_id == "process_industry"


def test_process_industry_level_0_conflict_recommends_refinement() -> None:
    report = run_template("conflict_level_0_missing_cooling_duty.yaml")
    assert report.optimization_success
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == "process_industry"
    assert report.top_residuals[0].diagnostic_key == "aggregate_thermal_balance_mismatch"
    assert report.recommended_refinements[0].next_template_ids == [
        "process_industry/level_1_reactor_separator_utility"
    ]


def test_process_industry_level_1_template_passes() -> None:
    report = run_template("level_1_reactor_separator_utility.yaml")
    assert report.optimization_success
    assert report.audit_pass
    block_ids = {block.block_id for block in report.top_blocks}
    assert {
        "reactor_conversion",
        "separator_split",
        "heat_exchange_utility",
        "rotating_equipment",
    }.issubset(block_ids)


def test_process_industry_templates_use_mapped_signals_not_dummy_placeholders() -> None:
    for path in PROC.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        assert "MappedSignalModule" in text
        assert "DummyResidualModule" not in text
