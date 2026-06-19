"""Run the PhysicsGuard Core FlowGuard lifecycle checks."""

from __future__ import annotations

from flowguard.explorer import Explorer

import physicsguard_core_model as model


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
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

