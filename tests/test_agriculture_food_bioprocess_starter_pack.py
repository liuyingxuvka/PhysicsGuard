from __future__ import annotations

from pathlib import Path

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec


ROOT = Path(__file__).resolve().parents[1]
AGRI = ROOT / "examples" / "hierarchical" / "agriculture_food_bioprocess"


def run_template(name: str):
    spec = load_hierarchical_audit_spec(AGRI / name)
    return HierarchicalAuditRunner(spec).run(top_n_residuals=20, top_n_blocks=10)


def test_agriculture_food_bioprocess_level_0_template_passes() -> None:
    report = run_template("level_0_agri_food_bioprocess_balance.yaml")
    assert report.optimization_success
    assert report.audit_pass
    assert report.top_blocks[0].block_id == "agriculture_food_bioprocess"


def test_agriculture_food_bioprocess_level_0_conflict_recommends_refinement() -> None:
    report = run_template("conflict_level_0_missing_irrigation_drainage.yaml")
    assert report.optimization_success
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == "agriculture_food_bioprocess"
    assert report.top_residuals[0].diagnostic_key == "aggregate_mass_balance_mismatch"
    assert report.recommended_refinements[0].next_template_ids == [
        "agriculture_food_bioprocess/level_1_greenhouse_irrigation_fermentation_drying_cold_chain"
    ]


def test_agriculture_food_bioprocess_level_1_template_passes() -> None:
    report = run_template("level_1_greenhouse_irrigation_fermentation_drying_cold_chain.yaml")
    assert report.optimization_success
    assert report.audit_pass
    block_ids = {block.block_id for block in report.top_blocks}
    assert {
        "irrigation_crop_water",
        "greenhouse_climate",
        "greenhouse_co2",
        "fermentation_bioreactor",
        "drying_process",
        "cold_chain_storage",
    }.issubset(block_ids)


def test_agriculture_food_bioprocess_templates_use_mapped_signals_not_dummy_placeholders() -> None:
    for path in AGRI.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        assert "MappedSignalModule" in text
        assert "DummyResidualModule" not in text
