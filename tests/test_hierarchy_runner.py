from __future__ import annotations

from pathlib import Path

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver


ROOT = Path(__file__).resolve().parents[1]
FC = ROOT / "examples" / "hierarchical" / "fuel_cell_system"
PID = ROOT / "examples" / "hierarchical" / "pid_actuator_loop"
OBSERVED = ROOT / "examples" / "hierarchical" / "observed_debugging"


def run(path: Path):
    spec = load_hierarchical_audit_spec(path)
    return HierarchicalAuditRunner(spec).run(top_n_residuals=20, top_n_blocks=10)


def test_clean_hierarchical_example_audit_pass_true() -> None:
    report = run(FC / "level_0_system_balance.yaml")
    assert report.optimization_success
    assert report.audit_pass
    assert report.top_blocks[0].block_id == "fc_system"
    assert report.top_blocks[0].confidence == 1.0


def test_conflict_hierarchical_example_identifies_top_block_and_refinement() -> None:
    report = run(FC / "conflict_level_0_h2_power.yaml")
    assert report.optimization_success
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == "fc_system"
    assert not report.top_blocks[0].audit_pass
    assert report.recommended_refinements[0].next_template_ids
    assert "aggregate_efficiency_mismatch" in report.recommended_refinements[0].trigger_diagnostic_keys


def test_level_1_cathode_conflict_recommends_cathode_template() -> None:
    report = run(FC / "conflict_level_1_cathode_air_path.yaml")
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == "cathode_air_path"
    assert report.recommended_refinements[0].next_template_ids == ["fuel_cell_system/level_2_cathode_air_path"]


def test_pid_actuator_conflict_identifies_actuator_block() -> None:
    report = run(PID / "conflict_actuator_feedback.yaml")
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == "actuator"
    assert report.recommended_refinements[0].rule_id == "refine_actuator_feedback"


def test_hierarchy_evaluate_observed_clean_does_not_solve_and_passes() -> None:
    spec = load_hierarchical_audit_spec(OBSERVED / "pitch_feedback_level_0.yaml")
    observed = load_observed_values(OBSERVED / "pitch_feedback_observed_clean.yaml")
    report = HierarchicalAuditRunner(spec).evaluate_observed(observed)
    assert report.audit_pass
    assert report.metadata["mode"] == "hierarchy_evaluate"
    assert report.metadata["solver_attempted"] is False
    assert report.top_residuals[0].diagnostic_key == "linear_relation_mismatch"


def test_hierarchy_evaluate_observed_fault_identifies_block_and_recommends_refinement() -> None:
    spec = load_hierarchical_audit_spec(OBSERVED / "pitch_feedback_level_0.yaml")
    observed = load_observed_values(OBSERVED / "pitch_feedback_observed_fault.yaml")
    report = HierarchicalAuditRunner(spec).evaluate_observed(observed)
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == "pitch_rate_feedback"
    assert report.top_blocks[0].score > 10
    assert report.recommended_refinements[0].rule_id == "inspect_pitch_rate_feedback_mapping_or_gain"
    assert report.recommended_refinements[0].next_required_parameters == ["actual feedback gain parameter"]


def test_hierarchy_compare_observed_fault_includes_variable_deviations() -> None:
    spec = load_hierarchical_audit_spec(OBSERVED / "pitch_feedback_level_0.yaml")
    observed = load_observed_values(OBSERVED / "pitch_feedback_observed_fault.yaml")
    report = HierarchicalAuditRunner(spec).compare_observed(observed)
    assert report.reference_optimization_success
    assert report.reference_audit_pass
    assert not report.observed_audit_pass
    assert report.top_variable_deviations[0].variable == "controller_q_gain.y"
    assert report.observed_hierarchy.top_blocks[0].block_id == "pitch_rate_feedback"


def test_hierarchical_report_is_json_serializable() -> None:
    spec = load_hierarchical_audit_spec(FC / "conflict_level_0_h2_power.yaml")
    runner = HierarchicalAuditRunner(spec)
    report = runner.run()
    data = runner.to_json(report, pretty=True)
    assert '"top_blocks"' in data
    assert '"recommended_refinements"' in data


def test_existing_normal_run_path_remains_unchanged() -> None:
    system = load_system_spec(ROOT / "examples" / "dummy_system.yaml")
    builder = ResidualBuilder(system)
    result = BoundedSolver(builder, system.solver).solve()
    report = DiagnosticReporter().generate(system, builder, result)
    assert report.system_name == "dummy_clean_system"
    assert report.audit_pass


def test_hierarchy_evaluate_skips_residuals_that_need_unobserved_variables(monkeypatch) -> None:
    from physicsguard.schema.observation_spec import ObservedValuesSpec
    import pytest

    spec = load_hierarchical_audit_spec(ROOT / "examples" / "hierarchical" / "coolant_loop" / "level_1_components.yaml")
    solved = BoundedSolver(ResidualBuilder(spec.system), spec.system.solver).solve().variables
    observed = ObservedValuesSpec(
        variables={name: {"value": value} for name, value in solved.items() if name != "cool.Q_stack_heat_W"}
    )
    def forbidden_solve(*args, **kwargs):
        raise AssertionError("partial observed evaluation must not solve")

    monkeypatch.setattr(BoundedSolver, "solve", forbidden_solve)
    before = observed.model_dump(mode="json")
    report = HierarchicalAuditRunner(spec).evaluate_observed(observed, skip_unobserved=True)
    assert observed.model_dump(mode="json") == before
    skipped = {
        "boundary:cool.Q_stack_heat_W": ["cool.Q_stack_heat_W"],
        "cool.fc_coolant_heat_interface": ["cool.Q_stack_heat_W"],
    }
    assert report.audit_pass
    assert report.missing_required_variables == ["cool.Q_stack_heat_W"]
    assert report.metadata["skipped_residuals"] == skipped
    assert not {item.name for item in report.top_residuals} & set(skipped)
    stack = next(block for block in report.top_blocks if block.block_id == "stack_heat_interface")
    assert stack.missing_required_variables == ["cool.Q_stack_heat_W"]
    assert stack.confidence < 1.0
    with pytest.raises(ValueError, match="observed values missing required registered variables"):
        HierarchicalAuditRunner(spec).evaluate_observed(observed)


def test_partial_snapshot_does_not_invent_a_zero_product_residual(monkeypatch) -> None:
    import pytest
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
    from physicsguard.schema.observation_spec import ObservedValuesSpec

    spec = HierarchicalAuditSpec.model_validate({
        "audit_name": "zero_product",
        "system": {"system_name": "power", "components": [{
            "id": "power", "type": "ElectricalPowerModule",
            "parameters": {"V_initial_guess": 0.0, "current_initial_guess": 0.0, "P_initial_guess": 0.0},
        }]},
        "hierarchy": {"blocks": [{"id": "power_block", "name": "power", "level": 0,
            "components": ["power"], "required_variables": ["power.V_V", "power.current_A", "power.P_W"]}]},
    })
    observed = ObservedValuesSpec(variables={"power.P_W": {"value": 0.0, "unit": "W"}})
    before = observed.model_dump(mode="json")
    def forbidden_solve(*args, **kwargs):
        raise AssertionError("partial observations must not solve")
    monkeypatch.setattr(BoundedSolver, "solve", forbidden_solve)
    with pytest.raises(ValueError, match="no residual can be evaluated without them"):
        HierarchicalAuditRunner(spec).evaluate_observed(observed, skip_unobserved=True)
    assert observed.model_dump(mode="json") == before


def test_partial_snapshot_skips_a_range_check_with_a_flat_local_region() -> None:
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
    from physicsguard.schema.observation_spec import ObservedValuesSpec

    spec = HierarchicalAuditSpec.model_validate({
        "audit_name": "flat_range",
        "system": {"system_name": "checks", "components": [
            {"id": "unknown", "type": "DummyResidualModule", "parameters": {
                "target": 0.0, "initial_guess": 0.0, "scale": 1.0, "lower_bound": -100.0, "upper_bound": 100.0}},
            {"id": "known", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
            {"id": "limit", "type": "RangeCheckModule", "parameters": {
                "variable": "unknown.x", "lower_bound": -10.0, "upper_bound": 10.0}},
        ]},
        "hierarchy": {"blocks": [{"id": "checks", "name": "checks", "level": 0,
            "components": ["unknown", "known", "limit"], "required_variables": ["unknown.x", "known.x"]}]},
    })
    report = HierarchicalAuditRunner(spec).evaluate_observed(
        ObservedValuesSpec(variables={"known.x": {"value": 0.0}}), skip_unobserved=True,
    )
    assert report.metadata["skipped_residuals"]["limit.range_check"] == ["unknown.x"]
    assert {item.name for item in report.top_residuals} == {"known.dummy_target"}
    assert report.missing_required_variables == ["unknown.x"]
    assert report.audit_pass


def test_unclassified_custom_residual_is_not_licensed_by_finite_probes() -> None:
    from dataclasses import replace
    from physicsguard.core.hierarchy import _fill_unobserved
    from physicsguard.modules.dummy import DummyResidualModule
    from physicsguard.modules.registry import ModuleRegistry
    from physicsguard.schema.system_spec import SystemSpec

    class UnclassifiedResidual(DummyResidualModule):
        def residuals(self, x, registry):
            return [replace(record, value=0.0) for record in super().residuals(x, registry)]

    modules = ModuleRegistry()
    modules.register("UnclassifiedResidual", lambda identifier, parameters: UnclassifiedResidual(identifier, parameters))
    builder = ResidualBuilder(SystemSpec.model_validate({
        "system_name": "custom", "components": [{"id": "custom", "type": "UnclassifiedResidual", "parameters": {"target": 0.0}}],
    }), module_registry=modules)
    values: dict[str, float] = {}
    _, skipped = _fill_unobserved(builder, builder.build_registry(), values, ["custom.x"])
    assert skipped == {"custom.dummy_target": ["custom.x"]}
    assert values == {}
