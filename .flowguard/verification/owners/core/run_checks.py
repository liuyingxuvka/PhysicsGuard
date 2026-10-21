"""Run the PhysicsGuard Core FlowGuard lifecycle checks and replay them on the real code."""

from __future__ import annotations

from contextlib import contextmanager
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "models/owners"))

from flowguard.explorer import Explorer

from core import physicsguard_core_model as model

ROOT = Path(__file__).resolve().parents[4]
IMPLEMENTED_BY = {
    "ValidateSystem": "src/physicsguard/io/yaml_loader.py:load_system_spec",
    "AssembleResiduals": "src/physicsguard/core/residual.py:ResidualBuilder",
    "ExecuteMode.solve": "src/physicsguard/core/solver.py:BoundedSolver.solve",
    "ExecuteMode.evaluate": "src/physicsguard/core/evaluator.py:AuditEvaluator.evaluate_observed",
    "ExecuteMode.hierarchy": "src/physicsguard/core/hierarchy.py:HierarchicalAuditRunner",
    "ExecuteMode.inspect": "src/physicsguard/core/hierarchy.py:inspect_hierarchy",
    "GenerateDiagnostics": "src/physicsguard/core/diagnostics.py:DiagnosticReporter.generate",
}
TESTED_BY = {
    "audit_pass_and_failure_are_disjoint": [
        "tests/test_diagnostics.py:test_report_distinguishes_optimization_success_from_audit_pass",
    ],
    "observed_evaluation_does_not_solve": [
        "tests/test_evaluator.py:test_evaluate_observed_does_not_call_solver",
        "tests/test_hierarchy_runner.py:test_hierarchy_evaluate_observed_clean_does_not_solve_and_passes",
    ],
    "variable_assumptions_are_fixed_residuals": [
        "tests/test_assumption_residuals.py:test_variable_assumption_creates_active_assumption_residual",
    ],
    "assumption_overrides_are_warned": [
        "tests/test_assumption_manager.py:test_explicit_parameter_override_requires_allow_override_and_warns",
    ],
}
ASSUMPTION_LABELS = {
    "parameter_fill": "parameter_assumption_filled",
    "parameter_override": "assumption_override_warned",
    "not_applied_proposed": "proposed_assumption_not_applied",
    "not_applied_rejected": "rejected_assumption_not_applied",
    "boundary_residual": "variable_assumption_boundary_ready",
}


@contextmanager
def _solver_counted():
    from physicsguard.core.solver import BoundedSolver

    calls = []
    original = BoundedSolver.solve

    def counting(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)

    BoundedSolver.solve = counting
    try:
        yield calls
    finally:
        BoundedSolver.solve = original


def _solve(relative: str) -> tuple[str, bool]:
    from physicsguard.core.diagnostics import DiagnosticReporter
    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.core.solver import BoundedSolver
    from physicsguard.io.yaml_loader import load_system_spec

    system = load_system_spec(ROOT / relative)
    builder = ResidualBuilder(system)
    result = BoundedSolver(builder, system.solver).solve()
    report = DiagnosticReporter().generate(system, builder, result)
    if report.optimization_success and not report.audit_pass:
        return "optimizer_converged_audit_failed", report.audit_pass
    return "solver_attempted", report.audit_pass


def _evaluate(system_file: str, observed_file: str, keep: int | None = None) -> tuple[str, bool | None]:
    from physicsguard.core.evaluator import AuditEvaluator
    from physicsguard.io.observation_loader import load_observed_values
    from physicsguard.io.yaml_loader import load_system_spec

    observed = load_observed_values(ROOT / observed_file)
    if keep is not None:
        observed = observed.model_copy(update={"variables": dict(list(observed.variables.items())[:keep])})
    with _solver_counted() as calls:
        try:
            report = AuditEvaluator(load_system_spec(ROOT / system_file)).evaluate_observed(observed)
        except ValueError as exc:
            if "observed values missing required registered variables" in str(exc):
                return "missing_observed_values_failed", None
            raise
    return ("observed_evaluated_without_solver" if not calls else "solver_attempted"), report.audit_pass


def _hierarchy(mode: str, audit_file: str, observed_file: str | None = None, keep: int | None = None):
    from physicsguard.core.hierarchy import HierarchicalAuditRunner, inspect_hierarchy
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    spec = load_hierarchical_audit_spec(ROOT / audit_file)
    with _solver_counted() as calls:
        if mode == "inspect":
            inspect_hierarchy(spec)
            return ("hierarchy_inspected_without_solver" if not calls else "solver_attempted"), None
        if mode == "run":
            report = HierarchicalAuditRunner(spec).run()
            return ("hierarchy_run_solved_and_reported" if calls else "no_solver_call"), report.audit_pass
        observed = load_observed_values(ROOT / observed_file)
        if keep is not None:
            observed = observed.model_copy(update={"variables": dict(list(observed.variables.items())[:keep])})
        try:
            report = HierarchicalAuditRunner(spec).evaluate_observed(observed)
        except ValueError as exc:
            if "observed values missing required registered variables" in str(exc):
                return "missing_observed_values_failed", None
            raise
    return ("hierarchy_observed_evaluated_without_solver" if not calls else "solver_attempted"), report.audit_pass


def _bad_schema() -> tuple[str, None]:
    from pydantic import ValidationError

    from physicsguard.schema.system_spec import SystemSpec

    try:
        SystemSpec.model_validate({"system_name": "missing_components"})
    except ValidationError:
        return "schema_failed", None
    return "schema_valid", None


def _assumption(relative: str) -> tuple[str, None]:
    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.io.yaml_loader import load_system_spec

    summary = ResidualBuilder(load_system_spec(ROOT / relative)).assumption_summary()
    return ASSUMPTION_LABELS.get(summary.cards[0].application, summary.cards[0].application), None


PITCH = "examples/hierarchical/observed_debugging"
REAL_CASES = {
    "clean": lambda: _solve("examples/dummy_system.yaml"),
    "converged_bad_audit": lambda: _solve("examples/dummy_conflict_system.yaml"),
    "bad_schema": _bad_schema,
    "evaluate_clean": lambda: _evaluate("examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_clean.yaml"),
    "evaluate_bad_audit": lambda: _evaluate("examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_conflict.yaml"),
    "evaluate_missing_observed": lambda: _evaluate("examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_clean.yaml", keep=1),
    "hierarchy_clean": lambda: _hierarchy("run", "examples/hierarchical/coolant_loop/level_0_cooling_balance.yaml"),
    "hierarchy_bad_audit": lambda: _hierarchy("run", "examples/hierarchical/coolant_loop/conflict_level_0_heat_rejection.yaml"),
    "hierarchy_evaluate_clean": lambda: _hierarchy("evaluate", f"{PITCH}/pitch_feedback_level_0.yaml", f"{PITCH}/pitch_feedback_observed_clean.yaml"),
    "hierarchy_evaluate_bad_audit": lambda: _hierarchy("evaluate", f"{PITCH}/pitch_feedback_level_0.yaml", f"{PITCH}/pitch_feedback_observed_fault.yaml"),
    "hierarchy_evaluate_missing_observed": lambda: _hierarchy("evaluate", f"{PITCH}/pitch_feedback_level_0.yaml", f"{PITCH}/pitch_feedback_observed_clean.yaml", keep=1),
    "hierarchy_inspect": lambda: _hierarchy("inspect", f"{PITCH}/pitch_feedback_level_0.yaml"),
    "assumption_parameter_fill": lambda: _assumption("examples/assumptions/parameter_assumption.yaml"),
    "assumption_parameter_override": lambda: _assumption("examples/assumptions/parameter_override_warning.yaml"),
    "assumption_proposed": lambda: _assumption("examples/assumptions/proposed_assumption.yaml"),
    "assumption_rejected": lambda: _assumption("examples/assumptions/rejected_assumption.yaml"),
    "assumption_variable_boundary": lambda: _assumption("examples/assumptions/variable_assumption.yaml"),
}


def conformance() -> list[str]:
    """Run each mapped model case through the real code; return the mismatches."""

    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    workflow = model.build_workflow()
    inputs = {item.case_id: item for item in model.EXTERNAL_INPUTS}
    mismatches = []
    for case_id, real in REAL_CASES.items():
        run = workflow.execute(model.initial_state(), inputs[case_id], terminal_predicate=model.terminal_predicate)
        model_labels = [step.label for step in run.completed_paths[0].trace.steps]
        real_label, real_audit_pass = real()
        if real_label not in model_labels:
            mismatches.append(f"{case_id}: real code gave {real_label!r}, model labels {model_labels}")
        expected_pass = inputs[case_id].residual_within_threshold
        if real_audit_pass is not None and real_audit_pass != expected_pass:
            mismatches.append(f"{case_id}: real audit_pass={real_audit_pass}, model expects {expected_pass}")
    return mismatches


def main() -> int:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        required_labels=(
            "schema_valid",
            "registry_ready",
            "residuals_ready",
            "solver_attempted",
            "optimizer_converged_audit_failed",
            "diagnostics_after_solver",
            "observed_evaluated_without_solver",
            "diagnostics_after_observed_evaluation",
            "compare_solved_and_evaluated",
            "diagnostics_after_comparison",
            "hierarchy_index_ready",
            "hierarchy_run_solved_and_reported",
            "hierarchy_plan_solved_and_recommended",
            "hierarchy_observed_evaluated_without_solver",
            "hierarchy_compare_solved_and_evaluated",
            "hierarchy_inspected_without_solver",
            "diagnostics_after_hierarchy_run",
            "diagnostics_after_hierarchy_plan",
            "diagnostics_after_hierarchy_evaluate",
            "diagnostics_after_hierarchy_compare",
            "diagnostics_after_hierarchy_inspect",
            "parameter_assumption_filled",
            "variable_assumption_boundary_ready",
            "assumption_override_warned",
            "proposed_assumption_not_applied",
            "rejected_assumption_not_applied",
            "assumption_free_variable_failed",
            "schema_failed",
            "registry_failed",
            "residual_reference_failed",
            "residual_normalization_failed",
            "post_check_solver_selection_failed",
            "missing_observed_values_failed",
        ),
    ).explore()
    print(report.format_text())
    mismatches = conformance()
    print(f"conformance: {len(REAL_CASES) - len(mismatches)}/{len(REAL_CASES)} model cases match the real code")
    for line in mismatches:
        print(f"  mismatch: {line}")
    return 0 if report.ok and not mismatches else 1


if __name__ == "__main__":
    from flowguard.map.runner import run_owner
    raise SystemExit(run_owner(main))
