from __future__ import annotations

from pathlib import Path

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec


ROOT = Path(__file__).resolve().parents[1]
MOB = ROOT / "examples" / "hierarchical" / "mobility_extensions"


def run_template(name: str):
    spec = load_hierarchical_audit_spec(MOB / name)
    return HierarchicalAuditRunner(spec).run(top_n_residuals=20, top_n_blocks=10)


def test_mobility_extensions_level_0_template_passes() -> None:
    report = run_template("level_0_mobility_energy_balance.yaml")
    assert report.optimization_success
    assert report.audit_pass
    assert report.top_blocks[0].block_id == "mobility_extensions"


def test_mobility_extensions_level_0_conflict_recommends_refinement() -> None:
    report = run_template("conflict_level_0_missing_charger_loss.yaml")
    assert report.optimization_success
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == "mobility_extensions"
    assert report.top_residuals[0].diagnostic_key == "aggregate_power_balance_mismatch"
    assert report.recommended_refinements[0].next_template_ids == [
        "mobility_extensions/level_1_charging_rail_marine_aviation_offroad"
    ]


def test_mobility_extensions_level_1_template_passes() -> None:
    report = run_template("level_1_charging_rail_marine_aviation_offroad.yaml")
    assert report.optimization_success
    assert report.audit_pass
    block_ids = {block.block_id for block in report.top_blocks}
    assert {
        "charging_infrastructure",
        "rail_traction",
        "marine_propulsion",
        "aviation_power",
        "offroad_hydraulics",
    }.issubset(block_ids)


def test_mobility_extensions_templates_use_mapped_signals_not_dummy_placeholders() -> None:
    for path in MOB.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        assert "MappedSignalModule" in text
        assert "DummyResidualModule" not in text
