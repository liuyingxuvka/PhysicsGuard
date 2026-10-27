"""observed_derivation: one audit stage with fresh native replay of its own cases."""
from __future__ import annotations
from dataclasses import dataclass,replace
from flowguard import FunctionResult,Invariant,InvariantResult,Workflow
from flowguard.explorer import Explorer
from _core_fixture import AuditInput,EXTERNAL_INPUTS,ReplayReport,stage_facts,replay_case

MODEL_ID='observed_derivation'
PARENT="core"
READS_PARENT=('registry_valid', 'solve_attempted', 'hierarchy_reports', 'hierarchy_descriptions', 'comparisons', 'diagnostics_emitted', 'failures')
OUTPUTS={'observed': ('evaluated', 'unobserved_listed', 'not_observed')}
IMPLEMENTED_BY={'ExecuteMode.evaluate': 'src/physicsguard/core/hierarchy.py:HierarchicalAuditRunner.evaluate_observed', 'BuildObservedRegistry': 'src/physicsguard/core/residual.py:ResidualBuilder.build_registry'}
USES={'ResidualBuilder': 'src/physicsguard/core/residual.py:ResidualBuilder', 'Diagnostics': 'src/physicsguard/core/diagnostics.py:DiagnosticReporter.generate'}
TESTED_BY={'unobserved_variables_stay_listed': ['tests/test_hierarchy_runner.py:test_hierarchy_evaluate_skips_residuals_that_need_unobserved_variables', 'tests/test_core.py:test_hierarchy_evaluate_reports_a_partial_snapshot'], 'no_residual_from_unobserved_guess': ['tests/test_hierarchy_runner.py:test_partial_snapshot_does_not_invent_a_zero_product_residual', 'tests/test_hierarchy_runner.py:test_partial_snapshot_skips_a_range_check_with_a_flat_local_region', 'tests/test_hierarchy_runner.py:test_unclassified_custom_residual_is_not_licensed_by_finite_probes', 'tests/test_hierarchy_runner.py:test_partial_sum_tracks_external_reads_when_it_declares_no_variables'], 'derived_relations_are_not_checks': ['tests/test_heated_tank_example.py:test_measured_tank_derivations_are_reported_without_solving', 'tests/test_hierarchy_runner.py:test_repeated_connection_names_keep_distinct_producing_and_checked_occurrences'], 'observed_evaluation_does_not_solve': ['tests/test_hierarchy_runner.py:test_evaluate_observed_does_not_call_solver', 'tests/test_hierarchy_runner.py:test_hierarchy_evaluate_observed_clean_does_not_solve_and_passes'], 'hierarchy_run_requires_solve': ['tests/test_hierarchy_runner.py:test_clean_hierarchical_example_audit_pass_true', 'tests/test_hierarchy_runner.py:test_conflict_hierarchical_example_identifies_top_block_and_refinement'], 'comparison_requires_reference_and_observed': ['tests/test_hierarchy_runner.py:test_compare_to_reference_returns_reference_and_observed_variables'], 'diagnostics_after_solver_or_failure': ['tests/test_diagnostics.py:test_warnings_generated_for_solver_failure', 'tests/test_solver.py:test_solver_result_includes_diagnostics_ready_fields']}
MUTATIONS={'counts_derivations_as_checks': 'derived_relations_are_not_checks', 'evaluate_calls_solver': 'observed_evaluation_does_not_solve', 'partial_snapshot_hides_unobserved': 'unobserved_variables_stay_listed', 'evaluates_from_initial_guess': 'no_residual_from_unobserved_guess', 'diagnostics_without_result': 'diagnostics_after_solver_or_failure', 'comparison_skips_reference': 'comparison_requires_reference_and_observed', 'hierarchy_skips_solve': 'hierarchy_run_requires_solve'}
REAL_CASE_IDS=('evaluate_clean', 'evaluate_bad_audit', 'evaluate_missing_observed', 'compare_bad_audit', 'hierarchy_clean', 'hierarchy_bad_audit', 'hierarchy_evaluate_clean', 'hierarchy_evaluate_bad_audit', 'hierarchy_evaluate_missing_observed', 'hierarchy_evaluate_derived_bad_audit', 'hierarchy_evaluate_partial_unresolved', 'hierarchy_evaluate_zero_product', 'hierarchy_evaluate_partial_snapshot')
LABELS={'growth_coarse_bad_audit': 'coarse_failure_consistency_reported', 'growth_planned_bad_audit': 'planned_template_reported_not_executed', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'tree_view_rendered_with_block_verdicts', 'hierarchy_evaluate_derived_child_bad_audit': 'child_failure_propagated', 'hierarchy_evaluate_derived_bad_audit': 'derived_relations_excluded_from_checks', 'hierarchy_evaluate_partial_unresolved': 'unobserved_residuals_skipped', 'clean': 'hierarchy_run_solved_and_reported', 'converged_bad_audit': 'optimizer_converged_audit_failed', 'bad_schema': 'schema_failed', 'evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'evaluate_missing_observed': 'derived_relations_excluded_from_checks', 'compare_bad_audit': 'hierarchy_compare_solved_and_evaluated', 'hierarchy_clean': 'hierarchy_run_solved_and_reported', 'hierarchy_bad_audit': 'optimizer_converged_audit_failed', 'hierarchy_evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_missing_observed': 'no_independent_observed_check_failed', 'hierarchy_evaluate_zero_product': 'no_independent_observed_check_failed', 'hierarchy_evaluate_partial_snapshot': 'unobserved_values_derived', 'hierarchy_describe': 'hierarchy_described_without_solver', 'assumption_parameter_fill': 'parameter_assumption_filled', 'assumption_parameter_override': 'assumption_override_warned', 'assumption_proposed': 'proposed_assumption_not_applied', 'assumption_rejected': 'rejected_assumption_not_applied', 'assumption_variable_boundary': 'variable_assumption_boundary_ready', 'hierarchy_evaluate_partial_tree_view_not_checked': 'tree_view_rendered_with_block_verdicts'}
# Expected finite fixture outcomes; conformance always runs native code afresh.
PORT_VALUES={'growth_coarse_bad_audit': 'evaluated', 'growth_planned_bad_audit': 'evaluated', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'unobserved_listed', 'hierarchy_evaluate_derived_child_bad_audit': 'evaluated', 'hierarchy_evaluate_derived_bad_audit': 'unobserved_listed', 'hierarchy_evaluate_partial_unresolved': 'unobserved_listed', 'clean': 'not_observed', 'converged_bad_audit': 'not_observed', 'bad_schema': 'not_observed', 'evaluate_clean': 'evaluated', 'evaluate_bad_audit': 'evaluated', 'evaluate_missing_observed': 'evaluated', 'compare_bad_audit': 'evaluated', 'hierarchy_clean': 'not_observed', 'hierarchy_bad_audit': 'not_observed', 'hierarchy_evaluate_clean': 'evaluated', 'hierarchy_evaluate_bad_audit': 'evaluated', 'hierarchy_evaluate_missing_observed': 'not_observed', 'hierarchy_evaluate_zero_product': 'not_observed', 'hierarchy_evaluate_partial_snapshot': 'evaluated', 'hierarchy_describe': 'not_observed', 'assumption_parameter_fill': 'not_observed', 'assumption_parameter_override': 'not_observed', 'assumption_proposed': 'not_observed', 'assumption_rejected': 'not_observed', 'assumption_variable_boundary': 'not_observed', 'hierarchy_evaluate_partial_tree_view_not_checked': 'unobserved_listed'}

@dataclass(frozen=True)
class State:
    observed_evaluations: tuple[str,...] = ()
    observed_without_solver: tuple[str,...] = ()
    unobserved_skipped: tuple[str,...] = ()
    unobserved_listed: tuple[str,...] = ()
    residuals_from_guess: tuple[str,...] = ()
    derivation_cases: tuple[str,...] = ()
    producing_relations: tuple[str,...] = ()
    checked_relations: tuple[str,...] = ()
    registry_valid: tuple[str,...] = ()
    solve_attempted: tuple[str,...] = ()
    hierarchy_reports: tuple[str,...] = ()
    hierarchy_descriptions: tuple[str,...] = ()
    comparisons: tuple[str,...] = ()
    diagnostics_emitted: tuple[str,...] = ()
    failures: tuple[str,...] = ()
    observed: str = ""

class Evaluate:
    name="Evaluate"
    reads=('registry_valid', 'solve_attempted', 'hierarchy_reports', 'hierarchy_descriptions', 'comparisons', 'diagnostics_emitted', 'failures', 'observed_evaluations', 'observed_without_solver', 'unobserved_skipped', 'unobserved_listed', 'residuals_from_guess', 'derivation_cases', 'producing_relations', 'checked_relations')
    writes=('registry_valid', 'solve_attempted', 'hierarchy_reports', 'hierarchy_descriptions', 'comparisons', 'diagnostics_emitted', 'failures', 'observed_evaluations', 'observed_without_solver', 'unobserved_skipped', 'unobserved_listed', 'residuals_from_guess', 'derivation_cases', 'producing_relations', 'checked_relations', 'observed')
    def __init__(self,defect=''):self.defect=defect
    def apply(self,q,state):
        key=q.case_id
        facts=stage_facts(q)
        incoming={name:facts[name] for name in READS_PARENT}
        state=replace(state,**incoming)
        values={}
        def put(name,condition):
            if condition:values[name]=(key,)
        evaluated=key in state.hierarchy_reports and q.mode in ('hierarchy_evaluate','hierarchy_compare')
        partial=q.mode=='hierarchy_evaluate' and not q.observed_values_complete and ('partial' in key or 'derived' in key or key=='evaluate_missing_observed')
        derives=partial and 'unresolved' not in key
        put('observed_evaluations',evaluated)
        put('observed_without_solver',evaluated and q.mode=='hierarchy_evaluate')
        put('unobserved_listed',partial and key in state.registry_valid)
        put('unobserved_skipped',partial and not derives)
        put('derivation_cases',derives)
        if derives:values['producing_relations']=(key+':producing',)
        if evaluated and q.mode=='hierarchy_evaluate':values['checked_relations']=(key+':independent',)
        if self.defect=='counts_derivations_as_checks' and derives:values['checked_relations']=values.get('producing_relations',())
        if self.defect=='evaluate_calls_solver' and evaluated and q.mode=='hierarchy_evaluate':incoming['solve_attempted']=(key,)
        if self.defect=='partial_snapshot_hides_unobserved' and partial:values['unobserved_listed']=()
        if self.defect=='evaluates_from_initial_guess' and q.unobserved_zero_product:values['residuals_from_guess']=(key,)
        if self.defect=='diagnostics_without_result':
            for name in READS_PARENT:incoming[name]=()
            incoming['diagnostics_emitted']=(key,)
        if self.defect=='comparison_skips_reference' and q.mode=='hierarchy_compare':incoming['solve_attempted']=()
        if self.defect=='hierarchy_skips_solve' and q.mode=='hierarchy_run':incoming['solve_attempted']=()
        values['observed']=PORT_VALUES.get(key,'not_observed')
        result=replace(state,**incoming,**values)
        yield FunctionResult(result.observed,result,label=LABELS.get(key,'stage_checked'))


def unobserved_variables_stay_listed(state: State, trace) -> InvariantResult:
    del trace
    hidden = tuple(sorted((set(state.unobserved_skipped) | set(state.derivation_cases)) - set(state.unobserved_listed)))
    if hidden:
        return InvariantResult.fail(f"residuals skipped without listing the unobserved variables: {hidden!r}")
    return InvariantResult.pass_()


def no_residual_from_unobserved_guess(state: State, trace) -> InvariantResult:
    del trace
    if state.residuals_from_guess:
        return InvariantResult.fail(f"residuals evaluated from unobserved initial guesses: {state.residuals_from_guess!r}")
    return InvariantResult.pass_()


def derived_relations_are_not_checks(state: State, trace) -> InvariantResult:
    del trace
    overlap = set(state.producing_relations) & set(state.checked_relations)
    if overlap:
        return InvariantResult.fail(f"producing relations counted as checks: {sorted(overlap)!r}")
    for case in set(state.derivation_cases) & set(state.hierarchy_reports):
        if f"{case}:producing" not in state.producing_relations or f"{case}:independent" not in state.checked_relations:
            return InvariantResult.fail(f"derived report omitted its producing or independent relation: {case}")
    return InvariantResult.pass_()


def observed_evaluation_does_not_solve(state: State, trace) -> InvariantResult:
    del trace
    bad = tuple(sorted(set(state.observed_without_solver) & set(state.solve_attempted)))
    if bad:
        return InvariantResult.fail(f"observed evaluation modified by solver: {bad!r}")
    return InvariantResult.pass_()


def hierarchy_run_requires_solve(state: State, trace) -> InvariantResult:
    del trace
    hierarchy_reports_that_must_solve = set(state.hierarchy_reports) - set(
        state.observed_without_solver
    )
    bad = tuple(sorted(hierarchy_reports_that_must_solve - set(state.solve_attempted)))
    if bad:
        return InvariantResult.fail(f"hierarchy report missing solve attempt: {bad!r}")
    return InvariantResult.pass_()


def comparison_requires_reference_and_observed(state: State, trace) -> InvariantResult:
    del trace
    bad = tuple(
        sorted(
            set(state.comparisons)
            - (set(state.solve_attempted) & set(state.observed_evaluations))
        )
    )
    if bad:
        return InvariantResult.fail(
            f"comparison missing reference solve or observed evaluation: {bad!r}"
        )
    return InvariantResult.pass_()


def diagnostics_after_solver_or_failure(state: State, trace) -> InvariantResult:
    solved_or_failed = (
        set(state.solve_attempted)
        | set(state.observed_evaluations)
        | set(state.comparisons)
        | set(state.hierarchy_reports)
        | set(state.hierarchy_descriptions)
        | set(state.failures)
    )
    extra = tuple(sorted(set(state.diagnostics_emitted) - solved_or_failed))
    if extra:
        return InvariantResult.fail(f"diagnostics emitted without result source: {extra!r}")
    return InvariantResult.pass_()

INVARIANTS=(
    Invariant(
        name="unobserved_variables_stay_listed",
        description="A partial snapshot lists missing or explicitly derived variables without silent fills.",
        predicate=unobserved_variables_stay_listed,
    ),
    Invariant(
        name="no_residual_from_unobserved_guess",
        description="No residual is evaluated from an unobserved variable's initial guess.",
        predicate=no_residual_from_unobserved_guess,
    ),
    Invariant("derived_relations_are_not_checks", "A producing relation is never an independent check.", derived_relations_are_not_checks),
    Invariant(
        name="observed_evaluation_does_not_solve",
        description="Evaluate mode substitutes observed values without running the solver.",
        predicate=observed_evaluation_does_not_solve,
    ),
    Invariant(
        name="hierarchy_run_requires_solve",
        description="Hierarchy run solves before reporting block diagnostics.",
        predicate=hierarchy_run_requires_solve,
    ),
    Invariant(
        name="comparison_requires_reference_and_observed",
        description="Compare mode includes both a reference solve and observed evaluation.",
        predicate=comparison_requires_reference_and_observed,
    ),
    Invariant(
        name="diagnostics_after_solver_or_failure",
        description="Diagnostics are emitted only after solve attempt or setup failure.",
        predicate=diagnostics_after_solver_or_failure,
    ),
)

def make(defect='',names=None):
    return Explorer(Workflow((Evaluate(defect),)),(State(),),EXTERNAL_INPUTS,
                    tuple(rule for rule in INVARIANTS if names is None or rule.name in names),
                    max_sequence_length=1,progress_steps=0)
def build_explorer():return make()
def broken_variants():return {name:make(name,{rule}) for name,rule in MUTATIONS.items()}

def conformance():
    mismatches=[]
    cases={case.case_id:case for case in EXTERNAL_INPUTS}
    for key in REAL_CASE_IDS:
        q=cases[key]
        modeled=next(iter(Evaluate().apply(q,State())))
        try:
            label,audit,ports,report,assumptions=replay_case(key)
            if label!=modeled.label:mismatches.append(f'{key}: native label {label!r}, model {modeled.label!r}')
            if audit is not None and audit!=q.residual_within_threshold:mismatches.append(f'{key}: audit_pass differs')
            if ports[0]!=modeled.new_state.observed:mismatches.append(f'{key}: native observed {ports[0]!r}, model {modeled.new_state.observed!r}')
        except Exception as exc:mismatches.append(f'{key}: real replay raised {type(exc).__name__}: {exc}')
    return ReplayReport(len(REAL_CASE_IDS),mismatches)
