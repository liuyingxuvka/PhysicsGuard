from __future__ import annotations

from pathlib import Path

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec


ROOT = Path(__file__).resolve().parents[1]
MG = ROOT / "examples" / "hierarchical" / "renewable_microgrid"


def run_template(name: str):
    spec = load_hierarchical_audit_spec(MG / name)
    return HierarchicalAuditRunner(spec).run(top_n_residuals=20, top_n_blocks=10)


def test_renewable_microgrid_level_0_template_passes() -> None:
    report = run_template("level_0_microgrid_balance.yaml")
    assert report.optimization_success
    assert report.audit_pass
    assert report.top_blocks[0].block_id == "renewable_microgrid"


def test_renewable_microgrid_level_0_conflict_recommends_refinement() -> None:
    report = run_template("conflict_level_0_unserved_load.yaml")
    assert report.optimization_success
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == "renewable_microgrid"
    assert report.top_residuals[0].diagnostic_key == "aggregate_electrical_bus_balance_mismatch"
    assert report.recommended_refinements[0].next_template_ids == [
        "renewable_microgrid/level_1_renewable_storage_dispatch"
    ]


def test_renewable_microgrid_level_1_template_passes() -> None:
    report = run_template("level_1_renewable_storage_dispatch.yaml")
    assert report.optimization_success
    assert report.audit_pass
    block_ids = {block.block_id for block in report.top_blocks}
    assert {"pv_system", "wind_system", "battery_storage", "load_dispatch"}.issubset(block_ids)


def test_renewable_microgrid_templates_use_mapped_signals_not_dummy_placeholders() -> None:
    for path in MG.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        assert "MappedSignalModule" in text
        assert "DummyResidualModule" not in text
