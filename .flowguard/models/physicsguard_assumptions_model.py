"""assumptions: one audit stage with fresh native replay of its own cases."""
from __future__ import annotations
from dataclasses import dataclass,replace
from flowguard import FunctionResult,Invariant,InvariantResult,Workflow
from flowguard.explorer import Explorer
from _core_fixture import AuditInput,EXTERNAL_INPUTS,ReplayReport,stage_facts,replay_case

MODEL_ID='assumptions'
PARENT="core"
READS_PARENT=('registry_valid', 'failures', 'residuals_normalized')
OUTPUTS={'disposition': ('applied', 'override_warned', 'not_applied', 'none')}
IMPLEMENTED_BY={'Cards': 'src/physicsguard/core/residual.py:ResidualBuilder.assumption_cards', 'Summary': 'src/physicsguard/core/residual.py:ResidualBuilder.assumption_summary', 'FixedVariableResiduals': 'src/physicsguard/core/assumptions.py:AssumptionManager.assumption_residual_records'}
USES={'Diagnostics': 'src/physicsguard/core/diagnostics.py:DiagnosticReporter.generate'}
TESTED_BY={'assumptions_are_reported_in_diagnostics': ['tests/test_assumption_diagnostics.py:test_normal_diagnostic_json_includes_assumptions_section', 'tests/test_assumption_diagnostics.py:test_proposed_assumption_warning_appears_and_not_applied'], 'variable_assumptions_are_fixed_residuals': ['tests/test_assumption_residuals.py:test_variable_assumption_creates_active_assumption_residual'], 'assumption_overrides_are_warned': ['tests/test_assumption_manager.py:test_explicit_parameter_override_requires_allow_override_and_warns']}
MUTATIONS={'diagnostics_drop_assumptions': 'assumptions_are_reported_in_diagnostics', 'variable_assumption_not_fixed': 'variable_assumptions_are_fixed_residuals', 'override_not_warned': 'assumption_overrides_are_warned'}
REAL_CASE_IDS=('assumption_parameter_fill', 'assumption_parameter_override', 'assumption_proposed', 'assumption_rejected', 'assumption_variable_boundary')
LABELS={'growth_coarse_bad_audit': 'coarse_failure_consistency_reported', 'growth_planned_bad_audit': 'planned_template_reported_not_executed', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'tree_view_rendered_with_block_verdicts', 'hierarchy_evaluate_derived_child_bad_audit': 'child_failure_propagated', 'hierarchy_evaluate_derived_bad_audit': 'derived_relations_excluded_from_checks', 'hierarchy_evaluate_partial_unresolved': 'unobserved_residuals_skipped', 'clean': 'hierarchy_run_solved_and_reported', 'converged_bad_audit': 'optimizer_converged_audit_failed', 'bad_schema': 'schema_failed', 'evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'evaluate_missing_observed': 'derived_relations_excluded_from_checks', 'compare_bad_audit': 'hierarchy_compare_solved_and_evaluated', 'hierarchy_clean': 'hierarchy_run_solved_and_reported', 'hierarchy_bad_audit': 'optimizer_converged_audit_failed', 'hierarchy_evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_missing_observed': 'no_independent_observed_check_failed', 'hierarchy_evaluate_zero_product': 'no_independent_observed_check_failed', 'hierarchy_evaluate_partial_snapshot': 'unobserved_values_derived', 'hierarchy_describe': 'hierarchy_described_without_solver', 'assumption_parameter_fill': 'parameter_assumption_filled', 'assumption_parameter_override': 'assumption_override_warned', 'assumption_proposed': 'proposed_assumption_not_applied', 'assumption_rejected': 'rejected_assumption_not_applied', 'assumption_variable_boundary': 'variable_assumption_boundary_ready', 'hierarchy_evaluate_partial_tree_view_not_checked': 'tree_view_rendered_with_block_verdicts'}
# Expected finite fixture outcomes; conformance always runs native code afresh.
PORT_VALUES={'growth_coarse_bad_audit': 'none', 'growth_planned_bad_audit': 'none', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'applied', 'hierarchy_evaluate_derived_child_bad_audit': 'applied', 'hierarchy_evaluate_derived_bad_audit': 'applied', 'hierarchy_evaluate_partial_unresolved': 'none', 'clean': 'none', 'converged_bad_audit': 'none', 'bad_schema': 'none', 'evaluate_clean': 'none', 'evaluate_bad_audit': 'none', 'evaluate_missing_observed': 'none', 'compare_bad_audit': 'none', 'hierarchy_clean': 'applied', 'hierarchy_bad_audit': 'applied', 'hierarchy_evaluate_clean': 'none', 'hierarchy_evaluate_bad_audit': 'none', 'hierarchy_evaluate_missing_observed': 'none', 'hierarchy_evaluate_zero_product': 'none', 'hierarchy_evaluate_partial_snapshot': 'applied', 'hierarchy_describe': 'none', 'assumption_parameter_fill': 'applied', 'assumption_parameter_override': 'override_warned', 'assumption_proposed': 'not_applied', 'assumption_rejected': 'not_applied', 'assumption_variable_boundary': 'applied', 'hierarchy_evaluate_partial_tree_view_not_checked': 'none'}

@dataclass(frozen=True)
class State:
    assumptions_seen: tuple[str,...] = ()
    assumptions_reported: tuple[str,...] = ()
    parameter_assumptions_applied: tuple[str,...] = ()
    variable_assumptions_fixed: tuple[str,...] = ()
    assumption_overrides_warned: tuple[str,...] = ()
    proposed_assumptions_not_applied: tuple[str,...] = ()
    rejected_assumptions_not_applied: tuple[str,...] = ()
    variable_assumptions_expected: tuple[str,...] = ()
    assumption_overrides_expected: tuple[str,...] = ()
    registry_valid: tuple[str,...] = ()
    failures: tuple[str,...] = ()
    residuals_normalized: tuple[str,...] = ()
    disposition: str = ""

class Evaluate:
    name="Evaluate"
    reads=('registry_valid', 'failures', 'residuals_normalized', 'assumptions_seen', 'assumptions_reported', 'parameter_assumptions_applied', 'variable_assumptions_fixed', 'assumption_overrides_warned', 'proposed_assumptions_not_applied', 'rejected_assumptions_not_applied', 'variable_assumptions_expected', 'assumption_overrides_expected')
    writes=('registry_valid', 'failures', 'residuals_normalized', 'assumptions_seen', 'assumptions_reported', 'parameter_assumptions_applied', 'variable_assumptions_fixed', 'assumption_overrides_warned', 'proposed_assumptions_not_applied', 'rejected_assumptions_not_applied', 'variable_assumptions_expected', 'assumption_overrides_expected', 'disposition')
    def __init__(self,defect=''):self.defect=defect
    def apply(self,q,state):
        key=q.case_id
        facts=stage_facts(q)
        incoming={name:facts[name] for name in READS_PARENT}
        state=replace(state,**incoming)
        values={}
        def put(name,condition):
            if condition:values[name]=(key,)
        ready=key in state.registry_valid
        normalized=key in state.residuals_normalized
        put('assumptions_seen',ready and q.has_assumptions)
        put('assumptions_reported',ready and q.has_assumptions and key not in state.failures)
        put('parameter_assumptions_applied',ready and q.parameter_assumption)
        put('variable_assumptions_fixed',normalized and q.variable_assumption)
        put('assumption_overrides_warned',ready and q.assumption_override)
        put('proposed_assumptions_not_applied',ready and q.proposed_assumption)
        put('rejected_assumptions_not_applied',ready and q.rejected_assumption)
        put('variable_assumptions_expected',ready and q.variable_assumption)
        put('assumption_overrides_expected',ready and q.assumption_override)
        if self.defect=='diagnostics_drop_assumptions':values['assumptions_reported']=()
        if self.defect=='variable_assumption_not_fixed':values['variable_assumptions_fixed']=()
        if self.defect=='override_not_warned':values['assumption_overrides_warned']=()
        values['disposition']=PORT_VALUES.get(key,'none')
        result=replace(state,**incoming,**values)
        yield FunctionResult(result.disposition,result,label=LABELS.get(key,'stage_checked'))


def assumptions_are_reported_in_diagnostics(state: State, trace) -> InvariantResult:
    del trace
    valid_assumption_cases = set(state.assumptions_seen) - set(state.failures)
    missing = tuple(sorted(valid_assumption_cases - set(state.assumptions_reported)))
    if missing:
        return InvariantResult.fail(f"assumptions not reported in diagnostics: {missing!r}")
    return InvariantResult.pass_()


def variable_assumptions_are_fixed_residuals(state: State, trace) -> InvariantResult:
    del trace
    bad = tuple(sorted(set(state.variable_assumptions_fixed) - set(state.residuals_normalized)))
    if bad:
        return InvariantResult.fail(f"variable assumptions not represented as residuals: {bad!r}")
    assembled = set(state.residuals_normalized) - set(state.failures)
    missing = (set(state.variable_assumptions_expected) & assembled) - set(state.variable_assumptions_fixed)
    if missing:
        return InvariantResult.fail(f"variable assumptions missing fixed residuals: {sorted(missing)!r}")
    return InvariantResult.pass_()


def assumption_overrides_are_warned(state: State, trace) -> InvariantResult:
    del trace
    bad = tuple(sorted(set(state.assumption_overrides_warned) - set(state.assumptions_seen)))
    if bad:
        return InvariantResult.fail(f"assumption overrides not tied to assumption cards: {bad!r}")
    ready = set(state.registry_valid) - set(state.failures)
    missing = (set(state.assumption_overrides_expected) & ready) - set(state.assumption_overrides_warned)
    if missing:
        return InvariantResult.fail(f"assumption overrides missing warnings: {sorted(missing)!r}")
    return InvariantResult.pass_()

INVARIANTS=(
    Invariant(
        name="assumptions_are_reported_in_diagnostics",
        description="Every valid assumption card is included in diagnostics.",
        predicate=assumptions_are_reported_in_diagnostics,
    ),
    Invariant(
        name="variable_assumptions_are_fixed_residuals",
        description="Variable assumptions become fixed residuals, not free variables.",
        predicate=variable_assumptions_are_fixed_residuals,
    ),
    Invariant(
        name="assumption_overrides_are_warned",
        description="Assumption overrides remain explicit and warning-bearing.",
        predicate=assumption_overrides_are_warned,
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
            from _core_fixture import replay_assumption_report
            replay_assumption_report(key)
            if label!=modeled.label:mismatches.append(f'{key}: native label {label!r}, model {modeled.label!r}')
            if audit is not None and audit!=q.residual_within_threshold:mismatches.append(f'{key}: audit_pass differs')
            if ports[1]!=modeled.new_state.disposition:mismatches.append(f'{key}: native disposition {ports[1]!r}, model {modeled.new_state.disposition!r}')
        except Exception as exc:mismatches.append(f'{key}: real replay raised {type(exc).__name__}: {exc}')
    return ReplayReport(len(REAL_CASE_IDS),mismatches)
