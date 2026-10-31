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


def test_resolution_line_names_default_scale(monkeypatch) -> None:
    import pytest
    from physicsguard.core.solver import BoundedSolver

    def forbidden_solve(*args, **kwargs):
        pytest.fail("observed resolution must not solve a reference")

    monkeypatch.setattr(BoundedSolver, "solve", forbidden_solve)
    for audit, observation, expected, default_scale in [
        ("audit_default_scales.yaml", "observed_ai_half.yaml", 8.0, True),
        ("audit.yaml", "observed_ai.yaml", 0.2, False),
    ]:
        spec = load_hierarchical_audit_spec(SHOWER / audit)
        observed = load_observed_values(SHOWER / observation)
        before = observed.model_dump()
        runner = HierarchicalAuditRunner(spec, SHOWER)
        report = runner.to_dict(runner.evaluate_observed(observed))
        lines = render_tree_view(describe_hierarchy(spec, base_dir=SHOWER), report=report).splitlines()
        line = next((line for line in lines if line.startswith("resolution:") and "mix.T_out_K" in line), "")
        item = next((item for item in line.split(", ") if "mix.T_out_K" in item), "")
        assert f"mix.T_out_K +-{expected:g} K" in item
        assert ("(default scale)" in item) is default_scale
        entry = report["resolution"]["mix.T_out_K"]
        assert entry["value"] == pytest.approx(expected, rel=1e-4)
        assert entry["unit"] == "K" and entry["default_scale"] is default_scale
        assert entry["residual"] == "mix.flow_merge_temperature_balance"
        heater = report["resolution"]["heater.Q_dot_W"]
        assert heater["default_scale"] is default_scale
        assert heater["residual"] == "heater.coolant_heat_balance"
        assert observed.model_dump() == before
        if default_scale:
            flow = report["resolution"]["mix.m_dot_2_kg_s"]
            assert flow["value"] == pytest.approx(1 / 288.15, rel=1e-4)
            assert flow["unit"] == "kg/s"


def test_resolution_rederives_values_and_keeps_checked_occurrence_scales() -> None:
    import pytest

    spec = load_hierarchical_audit_spec(SHOWER / "audit.yaml")
    observed = load_observed_values(SHOWER / "observed_ai.yaml")
    del observed.variables["mix.m_dot_out_kg_s"]
    before = observed.model_dump()
    runner = HierarchicalAuditRunner(spec, SHOWER)
    report = runner.to_dict(runner.evaluate_observed(observed))
    assert report["derived_variables"]["mix.m_dot_out_kg_s"]["residual"] == "mix.flow_merge_mass_balance"
    assert "mix.flow_merge_mass_balance" not in report["checked_residuals"]
    temperature = report["resolution"]["mix.T_out_K"]
    assert temperature["value"] == pytest.approx(0.2, rel=1e-4)
    assert temperature["default_scale"] is False
    flow = report["resolution"]["mix.m_dot_2_kg_s"]
    assert flow["value"] == pytest.approx(0.05 / (310.65 - 288.15), rel=1e-4)
    assert flow["residual"] == "mix.flow_merge_temperature_balance"
    assert observed.model_dump() == before


def test_resolution_scale_origin_belongs_to_the_winning_residual() -> None:
    import pytest

    observed = load_observed_values(SHOWER / "observed_ai_half.yaml")
    for parameters, expected_default in [
        ({"mass_residual_scale_kg_s": 0.01}, True),
        ({"energy_residual_scale_kgK_s": 1.0}, False),
    ]:
        spec = load_hierarchical_audit_spec(SHOWER / "audit_default_scales.yaml")
        next(component for component in spec.system.components if component.id == "mix").parameters.update(parameters)
        runner = HierarchicalAuditRunner(spec, SHOWER)
        entry = runner.to_dict(runner.evaluate_observed(observed))["resolution"]["mix.T_out_K"]
        assert entry["value"] == pytest.approx(8.0, rel=1e-4)
        assert entry["default_scale"] is expected_default


def test_native_lookup_numeric_tables_keep_a_real_resolution() -> None:
    import pytest
    from physicsguard.schema.observation_spec import ObservedValuesSpec

    path = SHOWER.parents[1] / "components/maps/lookup_table_2d.yaml"
    spec = load_hierarchical_audit_spec(path)
    observed = ObservedValuesSpec.model_validate({"variables": {
        "map.x": {"value": 0.5}, "map.y": {"value": 0.5}, "map.z": {"value": 1.0},
    }})
    report = HierarchicalAuditRunner(spec).evaluate_observed(observed)
    entry = report.resolution["map.z"]
    assert entry["value"] == pytest.approx(1.0, rel=1e-4)
    assert entry["residual"] == "map.lookup_table_2d" and entry["default_scale"] is True


def test_resolution_tree_order_empty_block_and_unknown_scale_source(monkeypatch) -> None:
    import pytest
    from physicsguard.core.residual import ResidualBuilder

    description, report = _shower_report("observed_ai.yaml")
    report["block_verdicts"].reverse()
    report["signal_mapping_ledger"][0]["issue_codes"] = ["review_required"]
    lines = render_tree_view(description, report=report).splitlines()
    resolutions = [line for line in lines if line.startswith("resolution:")]
    assert resolutions[0] == "resolution: supply no observed variables"
    assert resolutions[1].startswith("resolution: heater.")
    assert resolutions[2].startswith("resolution: mix.")
    assert max(i for i, line in enumerate(lines) if line.startswith("hint:")) < lines.index(resolutions[0])
    assert lines.index(resolutions[-1]) < next(i for i, line in enumerate(lines) if line.startswith("mapping:"))

    monkeypatch.setattr(ResidualBuilder, "residual_scale_defaults", lambda self, x, records, locations: [None] * len(records))
    spec = load_hierarchical_audit_spec(SHOWER / "audit_default_scales.yaml")
    observed = load_observed_values(SHOWER / "observed_ai_half.yaml")
    runner = HierarchicalAuditRunner(spec, SHOWER)
    unknown = runner.to_dict(runner.evaluate_observed(observed))
    assert unknown["resolution"]["mix.T_out_K"]["value"] == pytest.approx(8.0, rel=1e-4)
    assert unknown["resolution"]["mix.T_out_K"]["default_scale"] is None
    text = render_tree_view(describe_hierarchy(spec, base_dir=SHOWER), report=unknown)
    assert "mix.T_out_K +-8 K (scale source unavailable)" in text


def test_resolution_is_optional_for_projectors_and_zero_sensitivity_is_unchecked(monkeypatch) -> None:
    from physicsguard.core.residual import ResidualBuilder

    spec = load_hierarchical_audit_spec(SHOWER / "audit.yaml")
    observed = load_observed_values(SHOWER / "observed_ai.yaml")
    observed.variables["heater.m_dot_kg_s"].value = 0.0
    runner = HierarchicalAuditRunner(spec, SHOWER)
    report = runner.to_dict(runner.evaluate_observed(observed))
    assert report["resolution"]["heater.T_out_K"] is None
    assert "heater.T_out_K unchecked" in render_tree_view(describe_hierarchy(spec, base_dir=SHOWER), report=report)

    def unused(*args, **kwargs):
        raise AssertionError("internal projector requested unused resolution work")

    monkeypatch.setattr(ResidualBuilder, "residual_scale_defaults", unused)
    projected = runner.to_dict(runner.evaluate_observed(observed, _resolution=False))
    assert "resolution" not in projected
