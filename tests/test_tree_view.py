from __future__ import annotations

import copy
from pathlib import Path

from physicsguard.core.hierarchy import HierarchicalAuditRunner, describe_hierarchy
from physicsguard.core.tree_view import render_tree_view
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values


SHOWER = Path(__file__).resolve().parents[1] / "examples/hierarchical/shower_mix"


def _shower_report(observation: str):
    spec = load_hierarchical_audit_spec(SHOWER / "audit.yaml")
    runner = HierarchicalAuditRunner(spec, base_dir=SHOWER)
    report = runner.to_dict(runner.evaluate_observed(load_observed_values(SHOWER / observation)))
    return describe_hierarchy(spec, base_dir=SHOWER), report


def test_unit_hint_line() -> None:
    description, report = _shower_report("observed_q_kw.yaml")
    before = copy.deepcopy(report)
    expected = "hint: unit_conversion heater.Q_dot_W multiply by 1000"
    for full in (False, True):
        lines = render_tree_view(description, report=report, full=full).splitlines()
        hints = [line for line in lines if line.startswith("hint:")]
        assert len(hints) == len(report["bug_family_followups"]) == 2
        assert hints[-1] == expected
        assert hints[0].startswith("hint: conservation_balance ")
    assert report == before

    # The report can also carry refinement and mapping advice around its hints.
    with_advice = copy.deepcopy(report)
    with_advice["recommended_refinements"] = [{
        "rule_id": "measure_power", "next_template_ids": ["heater_probe"],
        "template_status": {"heater_probe": "planned"},
        "next_required_variables": ["heater.Q_dot_W"],
    }]
    with_advice["signal_mapping_ledger"][0]["issue_codes"] = ["review_required"]
    lines = render_tree_view(description, report=with_advice).splitlines()
    next_line = next(i for i, line in enumerate(lines) if line.startswith("next:"))
    hint_lines = [i for i, line in enumerate(lines) if line.startswith("hint:")]
    mapping_line = next(i for i, line in enumerate(lines) if line.startswith("mapping:"))
    assert next_line < min(hint_lines) <= max(hint_lines) < mapping_line


def test_conservation_hint_without_unit_hint() -> None:
    description, report = _shower_report("observed_ai.yaml")
    before = copy.deepcopy(report)
    lines = render_tree_view(description, report=report).splitlines()
    hints = [line for line in lines if line.startswith("hint:")]
    assert hints == [
        "hint: conservation_balance mix.flow_merge_temperature_balance: "
        "Inspect sibling inflow/outflow, loss, storage, and boundary-condition variables "
        "before adding deeper component physics."
    ]
    assert not any(line.startswith("hint: unit_conversion") for line in lines)
    assert report == before
