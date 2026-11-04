"""Independent assumptions domain facts and production contracts."""
from __future__ import annotations
from dataclasses import dataclass, replace
from ._audit_cases import AuditInput, EXTERNAL_INPUTS, stage_facts, replay_case
READS_PARENT = ('registry_valid', 'failures', 'residuals_normalized')
OUTPUTS = {'disposition': ('applied', 'override_warned', 'not_applied', 'none')}
MUTATIONS = {'diagnostics_drop_assumptions': 'assumptions_are_reported_in_diagnostics', 'variable_assumption_not_fixed': 'variable_assumptions_are_fixed_residuals', 'override_not_warned': 'assumption_overrides_are_warned'}
REAL_CASE_IDS = ('assumption_parameter_fill', 'assumption_parameter_override', 'assumption_proposed', 'assumption_rejected', 'assumption_variable_boundary')
LABELS = {'growth_coarse_bad_audit': 'coarse_failure_consistency_reported', 'growth_planned_bad_audit': 'planned_template_reported_not_executed', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'tree_view_rendered_with_block_verdicts', 'hierarchy_evaluate_derived_child_bad_audit': 'child_failure_propagated', 'hierarchy_evaluate_derived_bad_audit': 'derived_relations_excluded_from_checks', 'hierarchy_evaluate_partial_unresolved': 'unobserved_residuals_skipped', 'clean': 'hierarchy_run_solved_and_reported', 'converged_bad_audit': 'optimizer_converged_audit_failed', 'bad_schema': 'schema_failed', 'evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'evaluate_missing_observed': 'derived_relations_excluded_from_checks', 'compare_bad_audit': 'hierarchy_compare_solved_and_evaluated', 'hierarchy_clean': 'hierarchy_run_solved_and_reported', 'hierarchy_bad_audit': 'optimizer_converged_audit_failed', 'hierarchy_evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_missing_observed': 'no_independent_observed_check_failed', 'hierarchy_evaluate_zero_product': 'no_independent_observed_check_failed', 'hierarchy_evaluate_partial_snapshot': 'unobserved_values_derived', 'hierarchy_describe': 'hierarchy_described_without_solver', 'assumption_parameter_fill': 'parameter_assumption_filled', 'assumption_parameter_override': 'assumption_override_warned', 'assumption_proposed': 'proposed_assumption_not_applied', 'assumption_rejected': 'rejected_assumption_not_applied', 'assumption_variable_boundary': 'variable_assumption_boundary_ready', 'hierarchy_evaluate_partial_tree_view_not_checked': 'tree_view_rendered_with_block_verdicts'}
PORT_VALUES = {'growth_coarse_bad_audit': 'none', 'growth_planned_bad_audit': 'none', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'applied', 'hierarchy_evaluate_derived_child_bad_audit': 'applied', 'hierarchy_evaluate_derived_bad_audit': 'applied', 'hierarchy_evaluate_partial_unresolved': 'none', 'clean': 'none', 'converged_bad_audit': 'none', 'bad_schema': 'none', 'evaluate_clean': 'none', 'evaluate_bad_audit': 'none', 'evaluate_missing_observed': 'none', 'compare_bad_audit': 'none', 'hierarchy_clean': 'applied', 'hierarchy_bad_audit': 'applied', 'hierarchy_evaluate_clean': 'none', 'hierarchy_evaluate_bad_audit': 'none', 'hierarchy_evaluate_missing_observed': 'none', 'hierarchy_evaluate_zero_product': 'none', 'hierarchy_evaluate_partial_snapshot': 'applied', 'hierarchy_describe': 'none', 'assumption_parameter_fill': 'applied', 'assumption_parameter_override': 'override_warned', 'assumption_proposed': 'not_applied', 'assumption_rejected': 'not_applied', 'assumption_variable_boundary': 'applied', 'hierarchy_evaluate_partial_tree_view_not_checked': 'none'}

@dataclass(frozen=True)
class State:
    assumptions_seen: tuple[str, ...] = ()
    assumptions_reported: tuple[str, ...] = ()
    parameter_assumptions_applied: tuple[str, ...] = ()
    variable_assumptions_fixed: tuple[str, ...] = ()
    assumption_overrides_warned: tuple[str, ...] = ()
    proposed_assumptions_not_applied: tuple[str, ...] = ()
    rejected_assumptions_not_applied: tuple[str, ...] = ()
    variable_assumptions_expected: tuple[str, ...] = ()
    assumption_overrides_expected: tuple[str, ...] = ()
    registry_valid: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    residuals_normalized: tuple[str, ...] = ()
    disposition: str = ''

def expected(q, state, mutation=''):
    key = q.case_id
    facts = stage_facts(q)
    incoming = {name: facts[name] for name in READS_PARENT}
    state = replace(state, **incoming)
    values = {}

    def put(name, condition):
        if condition:
            values[name] = (key,)
    ready = key in state.registry_valid
    normalized = key in state.residuals_normalized
    put('assumptions_seen', ready and q.has_assumptions)
    put('assumptions_reported', ready and q.has_assumptions and (key not in state.failures))
    put('parameter_assumptions_applied', ready and q.parameter_assumption)
    put('variable_assumptions_fixed', normalized and q.variable_assumption)
    put('assumption_overrides_warned', ready and q.assumption_override)
    put('proposed_assumptions_not_applied', ready and q.proposed_assumption)
    put('rejected_assumptions_not_applied', ready and q.rejected_assumption)
    put('variable_assumptions_expected', ready and q.variable_assumption)
    put('assumption_overrides_expected', ready and q.assumption_override)
    if mutation == 'diagnostics_drop_assumptions':
        values['assumptions_reported'] = ()
    if mutation == 'variable_assumption_not_fixed':
        values['variable_assumptions_fixed'] = ()
    if mutation == 'override_not_warned':
        values['assumption_overrides_warned'] = ()
    values['disposition'] = PORT_VALUES.get(key, 'none')
    result = replace(state, **incoming, **values)
    return result

def assumptions_are_reported_in_diagnostics(state: State, trace) -> bool:
    del trace
    valid_assumption_cases = set(state.assumptions_seen) - set(state.failures)
    missing = tuple(sorted(valid_assumption_cases - set(state.assumptions_reported)))
    if missing:
        return False
    return True

def variable_assumptions_are_fixed_residuals(state: State, trace) -> bool:
    del trace
    bad = tuple(sorted(set(state.variable_assumptions_fixed) - set(state.residuals_normalized)))
    if bad:
        return False
    assembled = set(state.residuals_normalized) - set(state.failures)
    missing = (set(state.variable_assumptions_expected) & assembled) - set(state.variable_assumptions_fixed)
    if missing:
        return False
    return True

def assumption_overrides_are_warned(state: State, trace) -> bool:
    del trace
    bad = tuple(sorted(set(state.assumption_overrides_warned) - set(state.assumptions_seen)))
    if bad:
        return False
    ready = set(state.registry_valid) - set(state.failures)
    missing = (set(state.assumption_overrides_expected) & ready) - set(state.assumption_overrides_warned)
    if missing:
        return False
    return True
RULE_NAMES = ('assumptions_are_reported_in_diagnostics', 'variable_assumptions_are_fixed_residuals', 'assumption_overrides_are_warned')
RULES = (assumptions_are_reported_in_diagnostics, variable_assumptions_are_fixed_residuals, assumption_overrides_are_warned)

def assert_native_contract():
    mismatches = []
    cases = {case.case_id: case for case in EXTERNAL_INPUTS}
    for key in REAL_CASE_IDS:
        q = cases[key]
        modeled = expected(q, State())
        label, audit, ports, report, assumptions = replay_case(key)
        from ._audit_cases import replay_assumption_report
        replay_assumption_report(key)
        if label != LABELS[key]:
            mismatches.append(f'{key}: native label {label!r}, model {LABELS[key]!r}')
        if audit is not None and audit != q.residual_within_threshold:
            mismatches.append(f'{key}: audit_pass differs')
        if ports[1] != modeled.disposition:
            mismatches.append(f'{key}: native disposition {ports[1]!r}, model {modeled.disposition!r}')
    assert not mismatches, mismatches
