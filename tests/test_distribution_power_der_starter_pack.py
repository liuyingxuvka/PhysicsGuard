from __future__ import annotations

from pathlib import Path

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "examples" / "hierarchical" / "distribution_power_der"


def run_template(name: str):
    spec = load_hierarchical_audit_spec(DER / name)
    return HierarchicalAuditRunner(spec).run(top_n_residuals=20, top_n_blocks=10)


def test_distribution_power_der_level_0_template_passes() -> None:
    report = run_template("level_0_feeder_balance.yaml")
    assert report.optimization_success
    assert report.audit_pass
    assert report.top_blocks[0].block_id == "distribution_power_der"


def test_distribution_power_der_level_0_conflict_recommends_refinement() -> None:
    report = run_template("conflict_level_0_missing_line_loss.yaml")
    assert report.optimization_success
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == "distribution_power_der"
    assert report.top_residuals[0].diagnostic_key == "aggregate_electrical_bus_balance_mismatch"
    assert report.recommended_refinements[0].next_template_ids == [
        "distribution_power_der/level_1_feeder_der_power_quality"
    ]


def test_distribution_power_der_level_1_template_passes() -> None:
    report = run_template("level_1_feeder_der_power_quality.yaml")
    assert report.optimization_success
    assert report.audit_pass
    block_ids = {block.block_id for block in report.top_blocks}
    assert {
        "substation_transformer",
        "feeder_section_a",
        "feeder_section_b",
        "der_interface",
        "power_quality_voltage",
    }.issubset(block_ids)


def test_distribution_power_der_templates_use_mapped_signals_not_dummy_placeholders() -> None:
    for path in DER.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        assert "MappedSignalModule" in text
        assert "DummyResidualModule" not in text
