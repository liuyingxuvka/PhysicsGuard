"""Independent solver audit domain facts and production contracts."""
from __future__ import annotations
from dataclasses import dataclass, replace
from ._audit_cases import AuditInput, EXTERNAL_INPUTS, stage_facts, replay_case
READS_PARENT = ('residuals_normalized', 'solve_attempted')
OUTPUTS = {'audit': ('passed', 'failed', 'not_run')}
MUTATIONS = {'failed_audit_also_passes': 'audit_pass_and_failure_are_disjoint', 'post_checks_enter_solver': 'post_checks_never_block_valid_solver_selection'}
REAL_CASE_IDS = ('converged_bad_audit',)
LABELS = {'growth_coarse_bad_audit': 'coarse_failure_consistency_reported', 'growth_planned_bad_audit': 'planned_template_reported_not_executed', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'tree_view_rendered_with_block_verdicts', 'hierarchy_evaluate_derived_child_bad_audit': 'child_failure_propagated', 'hierarchy_evaluate_derived_bad_audit': 'derived_relations_excluded_from_checks', 'hierarchy_evaluate_partial_unresolved': 'unobserved_residuals_skipped', 'clean': 'hierarchy_run_solved_and_reported', 'converged_bad_audit': 'optimizer_converged_audit_failed', 'bad_schema': 'schema_failed', 'evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'evaluate_missing_observed': 'derived_relations_excluded_from_checks', 'compare_bad_audit': 'hierarchy_compare_solved_and_evaluated', 'hierarchy_clean': 'hierarchy_run_solved_and_reported', 'hierarchy_bad_audit': 'optimizer_converged_audit_failed', 'hierarchy_evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_missing_observed': 'no_independent_observed_check_failed', 'hierarchy_evaluate_zero_product': 'no_independent_observed_check_failed', 'hierarchy_evaluate_partial_snapshot': 'unobserved_values_derived', 'hierarchy_describe': 'hierarchy_described_without_solver', 'assumption_parameter_fill': 'parameter_assumption_filled', 'assumption_parameter_override': 'assumption_override_warned', 'assumption_proposed': 'proposed_assumption_not_applied', 'assumption_rejected': 'rejected_assumption_not_applied', 'assumption_variable_boundary': 'variable_assumption_boundary_ready', 'hierarchy_evaluate_partial_tree_view_not_checked': 'tree_view_rendered_with_block_verdicts'}
PORT_VALUES = {'growth_coarse_bad_audit': 'not_run', 'growth_planned_bad_audit': 'not_run', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'not_run', 'hierarchy_evaluate_derived_child_bad_audit': 'not_run', 'hierarchy_evaluate_derived_bad_audit': 'not_run', 'hierarchy_evaluate_partial_unresolved': 'not_run', 'clean': 'passed', 'converged_bad_audit': 'failed', 'bad_schema': 'not_run', 'evaluate_clean': 'not_run', 'evaluate_bad_audit': 'not_run', 'evaluate_missing_observed': 'not_run', 'compare_bad_audit': 'passed', 'hierarchy_clean': 'passed', 'hierarchy_bad_audit': 'failed', 'hierarchy_evaluate_clean': 'not_run', 'hierarchy_evaluate_bad_audit': 'not_run', 'hierarchy_evaluate_missing_observed': 'not_run', 'hierarchy_evaluate_zero_product': 'not_run', 'hierarchy_evaluate_partial_snapshot': 'not_run', 'hierarchy_describe': 'not_run', 'assumption_parameter_fill': 'not_run', 'assumption_parameter_override': 'not_run', 'assumption_proposed': 'not_run', 'assumption_rejected': 'not_run', 'assumption_variable_boundary': 'not_run', 'hierarchy_evaluate_partial_tree_view_not_checked': 'not_run'}

@dataclass(frozen=True)
class State:
    audit_passes: tuple[str, ...] = ()
    audit_failures: tuple[str, ...] = ()
    optimization_successes: tuple[str, ...] = ()
    post_checks_diagnostic_only: tuple[str, ...] = ()
    post_checks_in_solver: tuple[str, ...] = ()
    residuals_normalized: tuple[str, ...] = ()
    solve_attempted: tuple[str, ...] = ()
    audit: str = ''

def expected(q, state, mutation=''):
    key = q.case_id
    facts = stage_facts(q)
    incoming = {name: facts[name] for name in READS_PARENT}
    state = replace(state, **incoming)
    values = {}

    def put(name, condition):
        if condition:
            values[name] = (key,)
    normalized = key in state.residuals_normalized
    ran = normalized and q.mode in ('hierarchy_evaluate', 'hierarchy_compare', 'hierarchy_run')
    passed = 'bad_audit' not in key
    put('audit_passes', ran and passed)
    put('audit_failures', ran and (not passed))
    put('optimization_successes', key in state.solve_attempted and 'no_converge' not in key)
    put('post_checks_diagnostic_only', normalized and q.has_post_check_residuals)
    if mutation == 'failed_audit_also_passes' and values.get('audit_failures'):
        values['audit_passes'] = (key,)
    if mutation == 'post_checks_enter_solver' and q.has_post_check_residuals:
        values['post_checks_in_solver'] = (key,)
    values['audit'] = PORT_VALUES.get(key, 'not_run')
    result = replace(state, **incoming, **values)
    return result

def audit_pass_and_failure_are_disjoint(state: State, trace) -> bool:
    del trace
    bad = tuple(sorted(set(state.audit_passes) & set(state.audit_failures)))
    if bad:
        return False
    return True

def post_checks_never_block_valid_solver_selection(state: State, trace) -> bool:
    del trace
    bad = tuple(sorted(set(state.post_checks_diagnostic_only) - set(state.residuals_normalized)))
    if bad:
        return False
    if state.post_checks_in_solver:
        return False
    return True
RULE_NAMES = ('audit_pass_and_failure_are_disjoint', 'post_checks_never_block_valid_solver_selection')
RULES = (audit_pass_and_failure_are_disjoint, post_checks_never_block_valid_solver_selection)

def assert_native_contract():
    mismatches = []
    cases = {case.case_id: case for case in EXTERNAL_INPUTS}
    for key in REAL_CASE_IDS:
        q = cases[key]
        modeled = expected(q, State())
        label, audit, ports, report, assumptions = replay_case(key)
        if label != LABELS[key]:
            mismatches.append(f'{key}: native label {label!r}, model {LABELS[key]!r}')
        if audit is not None and audit != q.residual_within_threshold:
            mismatches.append(f'{key}: audit_pass differs')
        if ports[3] != modeled.audit:
            mismatches.append(f'{key}: native audit {ports[3]!r}, model {modeled.audit!r}')
    assert not mismatches, mismatches
