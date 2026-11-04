"""Independent observed derivation domain facts and production contracts."""
from __future__ import annotations
from dataclasses import dataclass, replace
from ._audit_cases import AuditInput, EXTERNAL_INPUTS, stage_facts, replay_case
READS_PARENT = ('registry_valid', 'solve_attempted', 'hierarchy_reports', 'hierarchy_descriptions', 'comparisons', 'diagnostics_emitted', 'failures')
OUTPUTS = {'observed': ('evaluated', 'unobserved_listed', 'not_observed')}
MUTATIONS = {'counts_derivations_as_checks': 'derived_relations_are_not_checks', 'evaluate_calls_solver': 'observed_evaluation_does_not_solve', 'partial_snapshot_hides_unobserved': 'unobserved_variables_stay_listed', 'evaluates_from_initial_guess': 'no_residual_from_unobserved_guess', 'diagnostics_without_result': 'diagnostics_after_solver_or_failure', 'comparison_skips_reference': 'comparison_requires_reference_and_observed', 'hierarchy_skips_solve': 'hierarchy_run_requires_solve', 'probe_edits_an_observation': 'unit_factor_probe_is_read_only_and_bounded'}
REAL_CASE_IDS = ('evaluate_clean', 'evaluate_bad_audit', 'evaluate_missing_observed', 'compare_bad_audit', 'hierarchy_clean', 'hierarchy_bad_audit', 'hierarchy_evaluate_clean', 'hierarchy_evaluate_bad_audit', 'hierarchy_evaluate_missing_observed', 'hierarchy_evaluate_derived_bad_audit', 'hierarchy_evaluate_partial_unresolved', 'hierarchy_evaluate_zero_product', 'hierarchy_evaluate_partial_snapshot')
LABELS = {'growth_coarse_bad_audit': 'coarse_failure_consistency_reported', 'growth_planned_bad_audit': 'planned_template_reported_not_executed', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'tree_view_rendered_with_block_verdicts', 'hierarchy_evaluate_derived_child_bad_audit': 'child_failure_propagated', 'hierarchy_evaluate_derived_bad_audit': 'derived_relations_excluded_from_checks', 'hierarchy_evaluate_partial_unresolved': 'unobserved_residuals_skipped', 'clean': 'hierarchy_run_solved_and_reported', 'converged_bad_audit': 'optimizer_converged_audit_failed', 'bad_schema': 'schema_failed', 'evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'evaluate_missing_observed': 'derived_relations_excluded_from_checks', 'compare_bad_audit': 'hierarchy_compare_solved_and_evaluated', 'hierarchy_clean': 'hierarchy_run_solved_and_reported', 'hierarchy_bad_audit': 'optimizer_converged_audit_failed', 'hierarchy_evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_missing_observed': 'no_independent_observed_check_failed', 'hierarchy_evaluate_zero_product': 'no_independent_observed_check_failed', 'hierarchy_evaluate_partial_snapshot': 'unobserved_values_derived', 'hierarchy_describe': 'hierarchy_described_without_solver', 'assumption_parameter_fill': 'parameter_assumption_filled', 'assumption_parameter_override': 'assumption_override_warned', 'assumption_proposed': 'proposed_assumption_not_applied', 'assumption_rejected': 'rejected_assumption_not_applied', 'assumption_variable_boundary': 'variable_assumption_boundary_ready', 'hierarchy_evaluate_partial_tree_view_not_checked': 'tree_view_rendered_with_block_verdicts'}
PORT_VALUES = {'growth_coarse_bad_audit': 'evaluated', 'growth_planned_bad_audit': 'evaluated', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'unobserved_listed', 'hierarchy_evaluate_derived_child_bad_audit': 'evaluated', 'hierarchy_evaluate_derived_bad_audit': 'unobserved_listed', 'hierarchy_evaluate_partial_unresolved': 'unobserved_listed', 'clean': 'not_observed', 'converged_bad_audit': 'not_observed', 'bad_schema': 'not_observed', 'evaluate_clean': 'evaluated', 'evaluate_bad_audit': 'evaluated', 'evaluate_missing_observed': 'evaluated', 'compare_bad_audit': 'evaluated', 'hierarchy_clean': 'not_observed', 'hierarchy_bad_audit': 'not_observed', 'hierarchy_evaluate_clean': 'evaluated', 'hierarchy_evaluate_bad_audit': 'evaluated', 'hierarchy_evaluate_missing_observed': 'not_observed', 'hierarchy_evaluate_zero_product': 'not_observed', 'hierarchy_evaluate_partial_snapshot': 'evaluated', 'hierarchy_describe': 'not_observed', 'assumption_parameter_fill': 'not_observed', 'assumption_parameter_override': 'not_observed', 'assumption_proposed': 'not_observed', 'assumption_rejected': 'not_observed', 'assumption_variable_boundary': 'not_observed', 'hierarchy_evaluate_partial_tree_view_not_checked': 'unobserved_listed'}

@dataclass(frozen=True)
class State:
    observed_evaluations: tuple[str, ...] = ()
    observed_without_solver: tuple[str, ...] = ()
    unobserved_skipped: tuple[str, ...] = ()
    unobserved_listed: tuple[str, ...] = ()
    residuals_from_guess: tuple[str, ...] = ()
    derivation_cases: tuple[str, ...] = ()
    producing_relations: tuple[str, ...] = ()
    checked_relations: tuple[str, ...] = ()
    registry_valid: tuple[str, ...] = ()
    solve_attempted: tuple[str, ...] = ()
    hierarchy_reports: tuple[str, ...] = ()
    hierarchy_descriptions: tuple[str, ...] = ()
    comparisons: tuple[str, ...] = ()
    diagnostics_emitted: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    unit_hint_cases: tuple[str, ...] = ()
    observation_edits: tuple[str, ...] = ()
    observed: str = ''

def expected(q, state, mutation=''):
    key = q.case_id
    facts = stage_facts(q)
    incoming = {name: facts[name] for name in READS_PARENT}
    state = replace(state, **incoming)
    values = {}

    def put(name, condition):
        if condition:
            values[name] = (key,)
    evaluated = key in state.hierarchy_reports and q.mode in ('hierarchy_evaluate', 'hierarchy_compare')
    partial = q.mode == 'hierarchy_evaluate' and (not q.observed_values_complete) and ('partial' in key or 'derived' in key or key == 'evaluate_missing_observed')
    derives = partial and 'unresolved' not in key
    put('observed_evaluations', evaluated)
    put('observed_without_solver', evaluated and q.mode == 'hierarchy_evaluate')
    put('unobserved_listed', partial and key in state.registry_valid)
    put('unobserved_skipped', partial and (not derives))
    put('derivation_cases', derives)
    if derives:
        values['producing_relations'] = (key + ':producing',)
    if evaluated and q.mode == 'hierarchy_evaluate':
        values['checked_relations'] = (key + ':independent',)
    if mutation == 'counts_derivations_as_checks' and derives:
        values['checked_relations'] = values.get('producing_relations', ())
    if mutation == 'evaluate_calls_solver' and evaluated and (q.mode == 'hierarchy_evaluate'):
        incoming['solve_attempted'] = (key,)
    if mutation == 'partial_snapshot_hides_unobserved' and partial:
        values['unobserved_listed'] = ()
    if mutation == 'evaluates_from_initial_guess' and q.unobserved_zero_product:
        values['residuals_from_guess'] = (key,)
    if mutation == 'diagnostics_without_result':
        for name in READS_PARENT:
            incoming[name] = ()
        incoming['diagnostics_emitted'] = (key,)
    if mutation == 'comparison_skips_reference' and q.mode == 'hierarchy_compare':
        incoming['solve_attempted'] = ()
    if mutation == 'hierarchy_skips_solve' and q.mode == 'hierarchy_run':
        incoming['solve_attempted'] = ()
    if q.mode == 'hierarchy_evaluate' and (not q.residual_within_threshold):
        values['unit_hint_cases'] = (key,)
        if mutation == 'probe_edits_an_observation':
            values['observation_edits'] = (key,)
    values['observed'] = PORT_VALUES.get(key, 'not_observed')
    result = replace(state, **incoming, **values)
    return result

def unobserved_variables_stay_listed(state: State, trace) -> bool:
    del trace
    hidden = tuple(sorted((set(state.unobserved_skipped) | set(state.derivation_cases)) - set(state.unobserved_listed)))
    if hidden:
        return False
    return True

def no_residual_from_unobserved_guess(state: State, trace) -> bool:
    del trace
    if state.residuals_from_guess:
        return False
    return True

def derived_relations_are_not_checks(state: State, trace) -> bool:
    del trace
    overlap = set(state.producing_relations) & set(state.checked_relations)
    if overlap:
        return False
    for case in set(state.derivation_cases) & set(state.hierarchy_reports):
        if f'{case}:producing' not in state.producing_relations or f'{case}:independent' not in state.checked_relations:
            return False
    return True

def observed_evaluation_does_not_solve(state: State, trace) -> bool:
    del trace
    bad = tuple(sorted(set(state.observed_without_solver) & set(state.solve_attempted)))
    if bad:
        return False
    return True

def hierarchy_run_requires_solve(state: State, trace) -> bool:
    del trace
    hierarchy_reports_that_must_solve = set(state.hierarchy_reports) - set(state.observed_without_solver)
    bad = tuple(sorted(hierarchy_reports_that_must_solve - set(state.solve_attempted)))
    if bad:
        return False
    return True

def comparison_requires_reference_and_observed(state: State, trace) -> bool:
    del trace
    bad = tuple(sorted(set(state.comparisons) - (set(state.solve_attempted) & set(state.observed_evaluations))))
    if bad:
        return False
    return True

def diagnostics_after_solver_or_failure(state: State, trace) -> bool:
    solved_or_failed = set(state.solve_attempted) | set(state.observed_evaluations) | set(state.comparisons) | set(state.hierarchy_reports) | set(state.hierarchy_descriptions) | set(state.failures)
    extra = tuple(sorted(set(state.diagnostics_emitted) - solved_or_failed))
    if extra:
        return False
    return True

def unit_factor_probe_is_read_only_and_bounded(state: State, trace) -> bool:
    del trace
    if state.observation_edits:
        return False
    return True

def _unit_hint_slip():
    from pathlib import Path
    import yaml
    from physicsguard.core import hierarchy
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.schema.observation_spec import ObservedValuesSpec
    tank = Path(__file__).resolve().parents[2] / 'examples/hierarchical/heated_tank'
    data = yaml.safe_load((tank / 'measured_k30.yaml').read_text())
    for row in data['variables'].values():
        row.pop('raw_value')
        row.pop('raw_unit')
    variable = 'inflow_mass.V_dot_m3_s'
    data['variables'][variable]['value'] *= 1000
    observed = ObservedValuesSpec.model_validate(data)
    before = observed.model_dump()
    measured = {name: row.value for name, row in observed.variables.items()}
    attempted = set()
    original = hierarchy._derive_unobserved

    def counted(builder, registry, known):
        attempted.update((name for name, value in measured.items() if name in known and known[name] != value))
        return original(builder, registry, known)
    hierarchy._derive_unobserved = counted
    try:
        spec = load_hierarchical_audit_spec(tank / 'heated_tank.yaml')
        report = hierarchy.HierarchicalAuditRunner(spec).evaluate_observed(observed, _resolution=False)
    finally:
        hierarchy._derive_unobserved = original
    problems = []
    if observed.model_dump() != before:
        problems.append('unit_hint_slip: observations changed')
    names = tuple((name for followup in report.bug_family_followups if followup.followup_id == 'unit_conversion_family' for name in followup.affected_variables))
    if names != (variable,):
        problems.append(f'unit_hint_slip: hint names {names!r}')
    if len(attempted) > 20:
        problems.append(f'unit_hint_slip: probed {len(attempted)} variables')
    return problems
RULE_NAMES = ('unit_factor_probe_is_read_only_and_bounded', 'unobserved_variables_stay_listed', 'no_residual_from_unobserved_guess', 'derived_relations_are_not_checks', 'observed_evaluation_does_not_solve', 'hierarchy_run_requires_solve', 'comparison_requires_reference_and_observed', 'diagnostics_after_solver_or_failure')
RULES = (unit_factor_probe_is_read_only_and_bounded, unobserved_variables_stay_listed, no_residual_from_unobserved_guess, derived_relations_are_not_checks, observed_evaluation_does_not_solve, hierarchy_run_requires_solve, comparison_requires_reference_and_observed, diagnostics_after_solver_or_failure)

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
        if ports[0] != modeled.observed:
            mismatches.append(f'{key}: native observed {ports[0]!r}, model {modeled.observed!r}')
    mismatches.extend(_unit_hint_slip())
    assert not mismatches, mismatches
