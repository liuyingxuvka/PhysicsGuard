"""Finite original contract inputs and deliberately bad ABSTRACT facts.

These independent expectations are not a driver, production validator or a claim
that a source mutation was executed. Real code is checked separately.
"""
from dataclasses import replace
from importlib import import_module
from itertools import product

TOPICS = ('assumptions','cli_exit','core','fault_variants','heated_tank_generator',
          'model_dataset_validation','module_descriptions','observed_derivation',
          'skill_install','solver_audit','test_file_contract','tree_verdicts')


def module(topic):
    return import_module(__package__ + '.' + topic)


def cases(topic):
    m = module(topic)
    if topic == 'model_dataset_validation':
        return (*m.EXTERNAL_INPUTS, *m.DEPTH_EXTERNAL_INPUTS)
    if topic in ('core','assumptions','observed_derivation','solver_audit','tree_verdicts'):
        return (*m.EXTERNAL_INPUTS, *getattr(m,'HINT_INPUTS',()), *getattr(m,'RESOLUTION_INPUTS',()))
    return m.CASES


def expected(topic, case, mutation='', previous=None):
    m = module(topic)
    if topic == 'core':
        from ._audit_cases import stage_facts
        facts = stage_facts(case)
        before = previous if previous is not None else m.State()
        state = replace(before, **{name:getattr(before,name)+values for name,values in facts.items()})
        if mutation == 'invalid_registry_reaches_solver' and not facts['registry_valid']:
            state = replace(state, solve_attempted=state.solve_attempted+(case.case_id,))
        elif mutation == 'raw_residual_reaches_solver' and case.case_id == 'raw_residual':
            state = replace(state, solve_attempted=state.solve_attempted+(case.case_id,))
        elif mutation == 'describe_solves' and case.mode == 'hierarchy_describe':
            state = replace(state, solve_attempted=state.solve_attempted+(case.case_id,))
        return state
    if topic == 'model_dataset_validation':
        return validation_facts(case, mutation, previous)
    if topic == 'test_file_contract':
        claim = case.data is False or (case.fresh and case.roles and case.mappings and case.passed)
        ignored = {'claim_without_fresh_manifest':'fresh','claim_with_unclassified_fields':'roles',
                   'claim_without_mapping_evidence_or_known_targets':'mappings','claim_without_contract_pass':'passed'}.get(mutation)
        if ignored:
            claim = not case.data or all(getattr(case,k) for k in ('fresh','roles','mappings') if k != ignored)
        return m.State(case.name,True,case.data,case.fresh,case.roles,case.mappings,case.passed,claim)
    initial = m.VariantState() if topic == 'fault_variants' else m.State()
    if topic == 'cli_exit' and mutation == 'failed_audit_exits_zero':
        mutation = True
    state = m.expected(case, initial, mutation=mutation) if topic != 'fault_variants' else m.expected(case, initial)
    if topic == 'fault_variants':
        c = case
        if mutation == 'ignores_heater_half' and c.selected == ('heater_half',):
            state = replace(state,audit_pass=True,failed_blocks=())
        elif mutation == 'reports_first_defect_only' and c.name == 'unmasked_two_owners':
            state = replace(state,failed_blocks=state.failed_blocks[:1])
        elif mutation == 'rejects_outflow_rounding' and c.selected == ('outflow_rounding',):
            state = replace(state,audit_pass=False,failed_blocks=('hydraulics',),row_ok=False)
        elif mutation == 'rejects_masked_pairs' and state.pair_status == 'masked':
            state = replace(state,row_ok=False)
        elif mutation == 'accepts_undetected_pairs' and state.pair_status == 'undetected':
            state = replace(state,row_ok=True)
        elif mutation == 'accepts_outside_pairs' and state.pair_status == 'outside':
            state = replace(state,row_ok=True)
        elif mutation == 'drops_pairwise_evidence' and c.name == 'all_fault_pairs':
            state = replace(state,pairwise_pairs=state.pairwise_pairs[:-1])
        elif mutation == 'hides_observed_model_miss' and c.name == 'observed_unexplained':
            state = replace(state,model_miss=False)
        elif mutation == 'fabricates_unavailable_evidence' and c.name == 'unavailable_pair':
            state = replace(state,audit_pass=True,failed_blocks=(),pair_status='undetected',row_ok=True)
    return state


def validation_facts(case, mutation='', previous=None):
    """The former independent gate obligations, expressed directly as facts."""
    m = module('model_dataset_validation')
    state = previous if previous is not None else m.State()
    key = case.case_id
    def add(name):
        nonlocal state
        state = replace(state,**{name:getattr(state,name)+(key,)})
    if case.missing_input_count:
        count = case.missing_input_finding_count + (mutation == 'duplicate_missing_input_finding')
        return replace(state,blocked=state.blocked+(key,), input_failure_reports=state.input_failure_reports+
                       ((key,case.missing_input_count,count,case.dependent_checks_not_run),))
    if not case.contracts_passed and mutation != 'failed_contracts_continue':
        add('blocked'); return state
    if case.contracts_passed:
        add('contracts_ready')
    hard = all(getattr(case,k) for k in ('dataset_identity_current','mapping_review_current','claim_scope_honest',
               'split_disjoint','residual_series_evaluated','envelope_intervals_preserved'))
    hard = hard and case.parameter_contribution_mode in ('sensitive','verified_non_sensitive')
    hard = hard and (case.parameter_contribution_mode != 'verified_non_sensitive' or case.non_sensitive_disposition_bounded)
    hard = hard and (not case.prediction_requested or (case.stateful_dynamic and case.predictive_rollout_passed))
    if not hard and mutation != 'hard_depth_gate_ignored':
        add('blocked'); return state
    adequate = all(getattr(case,k) for k in ('coverage_universe_complete','temporal_adequacy_passed',
        'critical_family_coverage_passed','parameter_temporal_adequacy_passed','parameter_universe_complete',
        'per_parameter_denominator_current','manifest_point_denominator_reconciled','parameter_strata_adequate',
        'dynamic_coverage_floor_passed','representative_parameter_evidence_passed','parameter_model_contribution_passed',
        'static_parameter_binding_passed'))
    if not adequate:
        add('partial'); return state
    if hard:
        add('depth_inputs_ready')
    if not case.direct_validation_ran:
        add('blocked'); return state
    if mutation != 'direct_validation_skipped':
        add('direct_validation_ran')
    if case.observed_values_mutated or (case.calibration_enabled and not case.calibration_parameters_bounded):
        add('blocked'); return state
    if case.calibration_enabled:
        add('calibration_ran')
    if case.calibration_enabled and not case.holdout_passed:
        add('validation_passed' if mutation == 'failed_holdout_passes' else 'partial'); return state
    add('holdout_passed')
    if not case.confidence_feedback_recorded:
        add('partial'); return state
    add('confidence_feedback_recorded');add('validation_passed')
    return state


def mutations(topic):
    m = module(topic)
    if hasattr(m,'MUTATIONS'):
        return dict(m.MUTATIONS)
    if topic == 'cli_exit':
        return {'failed_audit_exits_zero':'exit_code_follows_audit_pass','validation_prints_json_by_default':'default_view_is_the_tree'}
    if topic == 'model_dataset_validation':
        return {'duplicate_missing_input_finding':'one_finding_per_missing_input','hard_depth_gate_ignored':'no_pass_without_depth_inputs',
                'failed_holdout_passes':'no_pass_without_holdout_and_feedback','failed_contracts_continue':'no_pass_without_contracts',
                'direct_validation_skipped':'no_pass_without_direct_validation'}
    if topic == 'test_file_contract':
        return dict(zip(('claim_without_fresh_manifest','claim_with_unclassified_fields',
                        'claim_without_mapping_evidence_or_known_targets','claim_without_contract_pass'),m.RULE_NAMES))
    if topic == 'fault_variants':
        return dict(zip(('ignores_heater_half','reports_first_defect_only','rejects_outflow_rounding','rejects_masked_pairs',
                         'accepts_undetected_pairs','accepts_outside_pairs','drops_pairwise_evidence',
                         'hides_observed_model_miss','fabricates_unavailable_evidence'),m.RULE_NAMES[1:]))
    raise AssertionError(topic)


def states(topic):
    values = tuple(cases(topic))
    if topic in ('core','model_dataset_validation'):
        # Both original contracts explored ordered pairs with accumulated case facts.
        return tuple(expected(topic,b,previous=expected(topic,a)) for a,b in product(values,repeat=2))
    return tuple(expected(topic,case) for case in values)
