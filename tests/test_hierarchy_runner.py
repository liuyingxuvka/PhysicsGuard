from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
from physicsguard.schema.observation_spec import ObservedValuesSpec

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
    assert report.audit_pass
    assert report.missing_required_variables == []
    assert "cool.Q_stack_heat_W" in report.derived_variables
    producer = report.derived_variables["cool.Q_stack_heat_W"]["residual"]
    assert producer not in report.checked_residuals
    assert report.metadata["skipped_residuals"] == {}
    assert HierarchicalAuditRunner(spec).evaluate_observed(observed).audit_pass


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
            {"id": "unknown", "type": "LinearRelationModule", "parameters": _unseen_linear_parameters()},
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
    assert report.missing_required_variables == ["unknown.x", "unknown.y"]
    assert "unknown.x" not in report.derived_variables
    assert report.audit_pass


def test_unclassified_custom_residual_is_not_licensed_by_finite_probes() -> None:
    from dataclasses import replace
    from physicsguard.core.hierarchy import _derive_unobserved
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
    known, missing, derived, checked, skipped, provenance = _derive_unobserved(builder, builder.build_registry(), values)
    assert known == {} and missing == ["custom.x"] and not derived and not checked
    assert skipped == {"custom.dummy_target": ["custom.x"]}
    assert provenance["unresolved_dependency_residuals"] == ["custom.dummy_target"]
    assert values == {}


def _unseen_linear_parameters():
    return {"a": 1., "b": 0., **{f"{axis}_{name}": value for axis in ("x", "y")
            for name, value in (("lower_bound", -100.), ("upper_bound", 100.), ("initial_guess", 0.), ("scale", 1.))}}


def _partial_spec(components, connections=()):
    return HierarchicalAuditSpec.model_validate({
        "audit_name": "partial", "system": {"system_name": "partial", "components": components,
                                               "connections": list(connections)},
        "hierarchy": {"blocks": [{"id": "plant", "level": 0,
                                    "components": [item["id"] for item in components]}]},
    })


def test_partial_affinity_keeps_pressure_and_power_checks(monkeypatch) -> None:
    spec = _partial_spec([{"id": "rot", "type": "RotatingMachineAffinityModule", "parameters": {
        "nominal_speed_rad_s": 1., "nominal_m_dot_kg_s": 1.,
        "nominal_delta_p_Pa": 1., "nominal_P_shaft_W": 1.,
    }}])
    observed = ObservedValuesSpec(variables={f"rot.{name}": {"value": 1.}
                                            for name in ("speed_rad_s", "delta_p_Pa", "P_shaft_W")})
    before = observed.model_dump(mode="json")
    monkeypatch.setattr(BoundedSolver, "solve", lambda *a, **kw: pytest.fail("observed evaluation must not solve"))
    report = HierarchicalAuditRunner(spec).evaluate_observed(observed)
    assert report.audit_pass
    assert report.derived_variables["rot.m_dot_kg_s"]["value"] == pytest.approx(1.)
    assert set(report.checked_residuals) == {"rot.affinity_pressure", "rot.affinity_power"}
    assert report.metadata["residual_dependencies"]["rot.affinity_pressure"] == ["rot.delta_p_Pa", "rot.speed_rad_s"]
    assert observed.model_dump(mode="json") == before


def test_partial_mixer_mass_check_does_not_need_temperatures() -> None:
    components = [{"id": name, "type": "DummyResidualModule", "parameters": {
        "target": value, "initial_guess": value, "lower_bound": -1000., "upper_bound": 1000.,
    }} for name, value in (("a", 1.), ("b", 1.), ("out", 2.), ("tout", 300.))]
    components.extend([
        {"id": "temperatures", "type": "LinearRelationModule", "parameters": _unseen_linear_parameters()},
        {"id": "mix", "type": "MixerEnergyBalanceModule", "parameters": {
            "inlet_m_dot_variables": ["a.x", "b.x"], "inlet_T_variables": ["temperatures.x", "temperatures.y"],
            "outlet_m_dot_variable": "out.x", "outlet_T_variable": "tout.x",
        }},
    ])
    observed = ObservedValuesSpec(variables={f"{name}.x": {"value": value}
                                            for name, value in (("a", 1.), ("b", 1.), ("out", 2.), ("tout", 300.))})
    report = HierarchicalAuditRunner(_partial_spec(components)).evaluate_observed(observed, skip_unobserved=True)
    assert report.audit_pass
    assert "mix.mixer_mass_balance" in report.checked_residuals
    assert report.metadata["residual_dependencies"]["mix.mixer_mass_balance"] == ["a.x", "b.x", "out.x"]
    assert report.unchecked_residuals["mix.mixer_energy_balance"] == ["temperatures.x", "temperatures.y"]


def test_partial_map_axes_keep_loop_iterations_separate() -> None:
    spec = _partial_spec([
        {"id": "unknown", "type": "LinearRelationModule", "parameters": _unseen_linear_parameters()},
        {"id": "known", "type": "DummyResidualModule", "parameters": {"target": 0.}},
        {"id": "axes", "type": "MapAxisBoundsCheckModule", "parameters": {
            "variables": ["unknown.x", "known.x"], "lower_bounds": [-10., -10.], "upper_bounds": [10., 10.],
        }},
    ])
    report = HierarchicalAuditRunner(spec).evaluate_observed(
        ObservedValuesSpec(variables={"known.x": {"value": 0.}}), skip_unobserved=True,
    )
    assert report.audit_pass
    assert report.unchecked_residuals["axes.map_axis_bounds:unknown.x"] == ["unknown.x"]
    assert "axes.map_axis_bounds:known.x" in report.checked_residuals
    assert report.metadata["residual_dependencies"]["axes.map_axis_bounds:known.x"] == ["known.x"]
    assert not report.derived_variables


@pytest.mark.parametrize(("module_type", "parameters", "residual_name"), [
    ("ConservationSumModule", {"input_variables": ["unknown.x", "unknown.y"], "output_variables": ["known.x"]}, "balance.conservation_sum"),
    ("SumModule", {"input_variables": ["unknown.x", "unknown.y"], "output_variable": "known.x"}, "balance.sum_relation"),
])
def test_partial_sum_tracks_external_reads_when_it_declares_no_variables(module_type, parameters, residual_name) -> None:
    spec = _partial_spec([
        {"id": "unknown", "type": "LinearRelationModule", "parameters": _unseen_linear_parameters()},
        {"id": "known", "type": "DummyResidualModule", "parameters": {"target": 0.}},
        {"id": "balance", "type": module_type, "parameters": parameters},
    ])
    report = HierarchicalAuditRunner(spec).evaluate_observed(
        ObservedValuesSpec(variables={"known.x": {"value": 0.}}), skip_unobserved=True,
    )
    assert report.audit_pass
    assert not report.derived_variables
    assert report.unchecked_residuals[residual_name] == ["unknown.x", "unknown.y"]
    assert report.metadata["residual_dependencies"][residual_name] == ["known.x", "unknown.x", "unknown.y"]


def test_partial_heat_zero_product_cannot_supply_a_check() -> None:
    spec = _partial_spec([{"id": "heat", "type": "CoolantHeatBalanceModule", "parameters": {
        "m_dot_initial_guess": 0., "T_in_initial_guess": 300., "T_out_initial_guess": 300.,
        "Q_dot_initial_guess": 0.,
    }}])
    with pytest.raises(ValueError, match="no residual can be evaluated without them"):
        HierarchicalAuditRunner(spec).evaluate_observed(
            ObservedValuesSpec(variables={"heat.Q_dot_W": {"value": 0.}}), skip_unobserved=True,
        )


def test_run_and_complete_compare_do_not_capture_observed_dependencies(monkeypatch) -> None:
    monkeypatch.setattr("physicsguard.core.residual.module_residual_dependencies",
                        lambda *a, **kw: pytest.fail("ordinary solve/complete compare must not start provenance capture"))
    assert run(FC / "level_0_system_balance.yaml").audit_pass
    spec = load_hierarchical_audit_spec(OBSERVED / "pitch_feedback_level_0.yaml")
    observed = load_observed_values(OBSERVED / "pitch_feedback_observed_clean.yaml")
    assert HierarchicalAuditRunner(spec).compare_observed(observed).observed_audit_pass


@pytest.mark.parametrize("reverse", [False, True])
def test_conflicting_connection_endpoints_stay_observed(reverse) -> None:
    edges = [{"from_variable": "a.x", "to_variable": "c.x", "scale": 1.},
             {"from_variable": "c.x", "to_variable": "b.x", "scale": 1.}]
    if reverse:
        edges.reverse()
    spec = _partial_spec([{"id": name, "type": "DummyResidualModule", "parameters": {"target": value}}
                          for name, value in (("a", 1.), ("b", 3.), ("c", 1.))], edges)
    observed = ObservedValuesSpec(variables={"a.x": {"value": 1.}, "b.x": {"value": 3.}})
    before = observed.model_dump(mode="json")
    runner = HierarchicalAuditRunner(spec)
    report = runner.evaluate_observed(observed)
    expected = 3. if reverse else 1.
    assert report.derived_variables["c.x"]["value"] == expected
    assert observed.model_dump(mode="json") == before
    producer = report.derived_variables["c.x"]["residual"]
    assert producer not in report.checked_residuals
    checked_edge = "connection:a.x=c.x" if reverse else "connection:c.x=b.x"
    assert checked_edge in report.checked_residuals
    assert not report.audit_pass
    assert runner.to_dict(report) == runner.to_dict(runner.evaluate_observed(observed))


def test_repeated_connection_names_keep_distinct_producing_and_checked_occurrences() -> None:
    edge = {"from_variable": "a.x", "to_variable": "b.x", "scale": 1.}
    spec = _partial_spec([
        {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 0.}},
        {"id": "b", "type": "DummyResidualModule", "parameters": {"target": 0.}},
    ], [edge, {**edge, "scale": 2.}])
    report = HierarchicalAuditRunner(spec).evaluate_observed(ObservedValuesSpec(variables={"b.x": {"value": 0.}}))
    assert report.audit_pass
    producer = report.derived_variables["a.x"]["residual_occurrence"]
    assert producer == 2
    assert report.metadata["derivation_residual_occurrences"] == [2]
    assert report.metadata["checked_residual_occurrences"] == [0, 1, 3]
    # The names deliberately coincide; only occurrence 2 produced a value.
    assert report.derived_variables["a.x"]["residual"] in report.checked_residuals
    assert set(report.metadata["derivation_residual_occurrences"]).isdisjoint(report.metadata["checked_residual_occurrences"])


def test_fully_known_custom_failure_survives_a_same_name_derivation(monkeypatch) -> None:
    from dataclasses import replace
    from physicsguard.modules.dummy import DummyResidualModule
    from physicsguard.modules.registry import ModuleRegistry

    class SameName(DummyResidualModule):
        def residuals(self, x, registry):
            return [replace(record, name="a.dummy_target") for record in super().residuals(x, registry)]

    modules = ModuleRegistry()
    modules.register("DummyResidualModule", lambda identifier, parameters: DummyResidualModule(identifier, parameters))
    modules.register("SameName", lambda identifier, parameters: SameName(identifier, parameters))
    monkeypatch.setattr("physicsguard.core.hierarchy.ResidualBuilder", lambda system: ResidualBuilder(system, module_registry=modules))
    spec = _partial_spec([
        {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 1.}},
        {"id": "b", "type": "SameName", "parameters": {"target": 0.}},
        {"id": "c", "type": "DummyResidualModule", "parameters": {"target": 0.}},
    ])
    report = HierarchicalAuditRunner(spec).evaluate_observed(
        ObservedValuesSpec(variables={"b.x": {"value": 5.}, "c.x": {"value": 0.}}),
    )
    assert not report.audit_pass
    assert report.top_residuals[0].source == "b" and report.top_residuals[0].normalized_value == 5.
    assert report.metadata["derivation_residual_occurrences"] == [0]
    assert report.metadata["checked_residual_occurrences"] == [1, 2]
    assert report.metadata["checked_without_dependency_claim"] == [1]
    assert report.top_blocks[0].score == 5.


def test_a_derivation_without_remaining_checks_cannot_pass() -> None:
    spec = _partial_spec([{"id": "a", "type": "DummyResidualModule", "parameters": {"target": 1.}}])
    with pytest.raises(ValueError, match="no residual can be evaluated without them"):
        HierarchicalAuditRunner(spec).evaluate_observed(
            ObservedValuesSpec(variables={"external.x": {"value": 1.}}), skip_unobserved=True,
        )


@pytest.mark.parametrize(("function", "expected"), [
    (lambda x: x - .25, .25), (lambda x: x + 2., -2.),
    (lambda x: (x - .3) * (x + .7), None), (lambda x: x * 0., None),
    (lambda x: x * x + 1., None), (lambda x: 1. / x, None),
])
def test_bounded_derivation_rejects_ambiguous_or_undefined_roots(function, expected) -> None:
    from physicsguard.core.hierarchy import _bounded_root
    from physicsguard.core.registry import VariableRecord

    root = _bounded_root(function, VariableRecord("a.x", None, -2., 2., 0., 1.))
    assert root == pytest.approx(expected) if expected is not None else root is None
