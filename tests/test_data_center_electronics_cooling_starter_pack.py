from __future__ import annotations

from pathlib import Path

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec


ROOT = Path(__file__).resolve().parents[1]
DC = ROOT / "examples" / "hierarchical" / "data_center_electronics_cooling"


def run_template(name: str):
    spec = load_hierarchical_audit_spec(DC / name)
    return HierarchicalAuditRunner(spec).run(top_n_residuals=20, top_n_blocks=10)


def test_data_center_electronics_cooling_level_0_template_passes() -> None:
    report = run_template("level_0_data_center_cooling_balance.yaml")
    assert report.optimization_success
    assert report.audit_pass
    assert report.top_blocks[0].block_id == "data_center_electronics_cooling"


def test_data_center_electronics_cooling_level_0_conflict_recommends_refinement() -> None:
    report = run_template("conflict_level_0_underreported_cooling_capacity.yaml")
    assert report.optimization_success
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == "data_center_electronics_cooling"
    assert report.top_residuals[0].diagnostic_key == "aggregate_thermal_balance_mismatch"
    assert report.recommended_refinements[0].next_template_ids == [
        "data_center_electronics_cooling/level_1_it_room_cooling_power_chain"
    ]


def test_data_center_electronics_cooling_level_1_template_passes() -> None:
    report = run_template("level_1_it_room_cooling_power_chain.yaml")
    assert report.optimization_success
    assert report.audit_pass
    block_ids = {block.block_id for block in report.top_blocks}
    assert {
        "it_load_rack_heat",
        "facility_power_chain",
        "room_air_cooling",
        "coolant_loop",
        "cooling_plant_efficiency",
    }.issubset(block_ids)


def test_data_center_electronics_cooling_templates_use_mapped_signals_not_dummy_placeholders() -> None:
    for path in DC.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        assert "MappedSignalModule" in text
        assert "DummyResidualModule" not in text
