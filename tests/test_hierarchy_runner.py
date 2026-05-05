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
