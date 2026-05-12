from __future__ import annotations

from pathlib import Path

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec


ROOT = Path(__file__).resolve().parents[1]
UTIL = ROOT / "examples" / "hierarchical" / "industrial_utilities"


def run_template(name: str):
    spec = load_hierarchical_audit_spec(UTIL / name)
    return HierarchicalAuditRunner(spec).run(top_n_residuals=20, top_n_blocks=10)


def test_industrial_utilities_level_0_template_passes() -> None:
    report = run_template("level_0_utility_hub_balance.yaml")
    assert report.optimization_success
    assert report.audit_pass
    assert report.top_blocks[0].block_id == "industrial_utilities"


def test_industrial_utilities_level_0_conflict_recommends_refinement() -> None:
    report = run_template("conflict_level_0_missing_air_leak.yaml")
    assert report.optimization_success
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == "industrial_utilities"
    assert report.top_residuals[0].diagnostic_key == "aggregate_mass_balance_mismatch"
    assert report.recommended_refinements[0].next_template_ids == [
        "industrial_utilities/level_1_steam_air_refrigeration_cooling_water"
    ]


def test_industrial_utilities_level_1_template_passes() -> None:
    report = run_template("level_1_steam_air_refrigeration_cooling_water.yaml")
    assert report.optimization_success
    assert report.audit_pass
    block_ids = {block.block_id for block in report.top_blocks}
    assert {
        "steam_condensate",
        "compressed_air",
        "refrigeration_chilled_water",
        "cooling_water",
        "utility_power",
    }.issubset(block_ids)


def test_industrial_utilities_templates_use_mapped_signals_not_dummy_placeholders() -> None:
    for path in UTIL.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        assert "MappedSignalModule" in text
        assert "DummyResidualModule" not in text
