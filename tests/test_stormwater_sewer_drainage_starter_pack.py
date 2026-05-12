from __future__ import annotations

from pathlib import Path

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec


ROOT = Path(__file__).resolve().parents[1]
STORM = ROOT / "examples" / "hierarchical" / "stormwater_sewer_drainage"


def run_template(name: str):
    spec = load_hierarchical_audit_spec(STORM / name)
    return HierarchicalAuditRunner(spec).run(top_n_residuals=20, top_n_blocks=10)


def test_stormwater_level_0_template_passes() -> None:
    report = run_template("level_0_network_balance.yaml")
    assert report.optimization_success
    assert report.audit_pass
    assert report.top_blocks[0].block_id == "stormwater_sewer_drainage"


def test_stormwater_level_0_conflict_recommends_refinement() -> None:
    report = run_template("conflict_level_0_unreported_overflow.yaml")
    assert report.optimization_success
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == "stormwater_sewer_drainage"
    assert report.top_residuals[0].diagnostic_key == "aggregate_mass_balance_mismatch"
    assert report.recommended_refinements[0].next_template_ids == [
        "stormwater_sewer_drainage/level_1_catchment_conveyance_storage_pump"
    ]


def test_stormwater_level_1_template_passes() -> None:
    report = run_template("level_1_catchment_conveyance_storage_pump.yaml")
    assert report.optimization_success
    assert report.audit_pass
    block_ids = {block.block_id for block in report.top_blocks}
    assert {
        "catchment_runoff",
        "sewer_conveyance",
        "detention_storage",
        "pump_station",
        "pollutant_load",
    }.issubset(block_ids)


def test_stormwater_templates_use_mapped_signals_not_dummy_placeholders() -> None:
    for path in STORM.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        assert "MappedSignalModule" in text
        assert "DummyResidualModule" not in text
