"""Independent core domain facts and production contracts."""
from __future__ import annotations
from dataclasses import dataclass, replace
from ._audit_cases import AuditInput, EXTERNAL_INPUTS, stage_facts, replay_case
HANDOFF = {'observed_derivation': {'observed': 'observed_status'}, 'assumptions': {'disposition': 'assumption_status'}, 'tree_verdicts': {'tree_verdict': 'tree_verdict'}, 'solver_audit': {'audit': 'audit_status'}}
KEEPS = ('schema_valid',)
CHILD_RESULTS = {'bad_schema': ('not_observed', 'none', 'no checks', 'not_run'), 'assumption_variable_boundary': ('not_observed', 'applied', 'no checks', 'not_run'), 'assumption_proposed': ('not_observed', 'not_applied', 'no checks', 'not_run'), 'assumption_parameter_override': ('not_observed', 'override_warned', 'no checks', 'not_run'), 'evaluate_clean': ('evaluated', 'none', 'PASS', 'not_run'), 'converged_bad_audit': ('not_observed', 'none', 'FAIL', 'failed'), 'clean': ('not_observed', 'none', 'PASS', 'passed'), 'hierarchy_evaluate_partial_unresolved': ('unobserved_listed', 'none', 'PASS', 'not_run'), 'hierarchy_evaluate_partial_tree_view_not_checked': ('unobserved_listed', 'none', 'not checked', 'not_run')}
REAL_CASE_IDS = ('clean', 'bad_schema', 'hierarchy_describe')
MUTATIONS = {'invalid_registry_reaches_solver': 'no_solve_without_valid_registry', 'raw_residual_reaches_solver': 'no_solve_without_normalized_residuals', 'describe_solves': 'hierarchy_describe_does_not_solve'}
LABELS = {'growth_coarse_bad_audit': 'coarse_failure_consistency_reported', 'growth_planned_bad_audit': 'planned_template_reported_not_executed', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'tree_view_rendered_with_block_verdicts', 'hierarchy_evaluate_derived_child_bad_audit': 'child_failure_propagated', 'hierarchy_evaluate_derived_bad_audit': 'derived_relations_excluded_from_checks', 'hierarchy_evaluate_partial_unresolved': 'unobserved_residuals_skipped', 'clean': 'hierarchy_run_solved_and_reported', 'converged_bad_audit': 'optimizer_converged_audit_failed', 'bad_schema': 'schema_failed', 'evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'evaluate_missing_observed': 'derived_relations_excluded_from_checks', 'compare_bad_audit': 'hierarchy_compare_solved_and_evaluated', 'hierarchy_clean': 'hierarchy_run_solved_and_reported', 'hierarchy_bad_audit': 'optimizer_converged_audit_failed', 'hierarchy_evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_missing_observed': 'no_independent_observed_check_failed', 'hierarchy_evaluate_zero_product': 'no_independent_observed_check_failed', 'hierarchy_evaluate_partial_snapshot': 'unobserved_values_derived', 'hierarchy_describe': 'hierarchy_described_without_solver', 'assumption_parameter_fill': 'parameter_assumption_filled', 'assumption_parameter_override': 'assumption_override_warned', 'assumption_proposed': 'proposed_assumption_not_applied', 'assumption_rejected': 'rejected_assumption_not_applied', 'assumption_variable_boundary': 'variable_assumption_boundary_ready', 'hierarchy_evaluate_partial_tree_view_not_checked': 'tree_view_rendered_with_block_verdicts'}

@dataclass(frozen=True)
class State:
    schema_valid: tuple[str, ...] = ()
    registry_valid: tuple[str, ...] = ()
    residuals_normalized: tuple[str, ...] = ()
    solve_attempted: tuple[str, ...] = ()
    comparisons: tuple[str, ...] = ()
    hierarchy_reports: tuple[str, ...] = ()
    hierarchy_descriptions: tuple[str, ...] = ()
    diagnostics_emitted: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    observed_status: tuple[str, ...] = ()
    assumption_status: tuple[str, ...] = ()
    tree_verdict: tuple[str, ...] = ()
    audit_status: tuple[str, ...] = ()

def no_solve_without_valid_registry(state: State, trace) -> bool:
    del trace
    missing = tuple(sorted(set(state.solve_attempted) - set(state.registry_valid)))
    if missing:
        return False
    return True

def no_solve_without_normalized_residuals(state: State, trace) -> bool:
    del trace
    missing = tuple(sorted(set(state.solve_attempted) - set(state.residuals_normalized)))
    if missing:
        return False
    return True

def hierarchy_describe_does_not_solve(state: State, trace) -> bool:
    del trace
    bad = tuple(sorted(set(state.hierarchy_descriptions) & set(state.solve_attempted)))
    if bad:
        return False
    return True
RULE_NAMES = ('no_solve_without_valid_registry', 'no_solve_without_normalized_residuals', 'hierarchy_describe_does_not_solve')
RULES = (no_solve_without_valid_registry, no_solve_without_normalized_residuals, hierarchy_describe_does_not_solve)


def assert_native_contract():
    from ._audit_cases import replay_case
    for key in tuple(dict.fromkeys((*REAL_CASE_IDS,*CHILD_RESULTS))):
        label,audit,ports,report,assumptions=replay_case(key)
        assert label == LABELS[key],(key,label,LABELS[key])
        if key in REAL_CASE_IDS:
            expected_input=next(case for case in EXTERNAL_INPUTS if case.case_id==key)
            if audit is not None:
                assert audit is expected_input.residual_within_threshold,key
        if key in CHILD_RESULTS:
            assert tuple(ports)==CHILD_RESULTS[key],(key,ports,CHILD_RESULTS[key])
