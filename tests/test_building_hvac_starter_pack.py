from __future__ import annotations

from pathlib import Path

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec


ROOT = Path(__file__).resolve().parents[1]
HVAC = ROOT / "examples" / "hierarchical" / "building_hvac"


def run_template(name: str):
    spec = load_hierarchical_audit_spec(HVAC / name)
    return HierarchicalAuditRunner(spec).run(top_n_residuals=20, top_n_blocks=10)


def test_building_hvac_level_0_template_passes() -> None:
    report = run_template("level_0_building_plant_balance.yaml")
    assert report.optimization_success
    assert report.audit_pass
    assert report.top_blocks[0].block_id == "building_hvac"


def test_building_hvac_level_0_conflict_recommends_refinement() -> None:
    report = run_template("conflict_level_0_unmet_cooling_load.yaml")
    assert report.optimization_success
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == "building_hvac"
    assert report.top_residuals[0].diagnostic_key == "aggregate_thermal_balance_mismatch"
    assert report.recommended_refinements[0].next_template_ids == [
        "building_hvac/level_1_hvac_plant_loop"
    ]


def test_building_hvac_level_1_template_passes() -> None:
    report = run_template("level_1_hvac_plant_loop.yaml")
    assert report.optimization_success
    assert report.audit_pass
    block_ids = {block.block_id for block in report.top_blocks}
    assert {
        "zone_loads",
        "chilled_water_loop",
        "chiller_condenser",
        "air_handler",
        "plant_electrical",
        "district_energy_interface",
    }.issubset(block_ids)


def test_building_hvac_templates_use_mapped_signals_not_dummy_placeholders() -> None:
    for path in HVAC.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        assert "MappedSignalModule" in text
        assert "DummyResidualModule" not in text
