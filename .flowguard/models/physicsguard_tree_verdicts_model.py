"""tree_verdicts: one audit stage with fresh native replay of its own cases."""
from __future__ import annotations
from dataclasses import dataclass,replace
from flowguard import FunctionResult,Invariant,InvariantResult,Workflow
from flowguard.explorer import Explorer
from _core_fixture import AuditInput,EXTERNAL_INPUTS,ReplayReport,stage_facts,replay_case

MODEL_ID='tree_verdicts'
PARENT="core"
READS_PARENT=('solve_attempted',)
OUTPUTS={'tree_verdict': ('PASS', 'FAIL', 'not checked', 'no checks')}
IMPLEMENTED_BY={'ExecuteMode.growth': 'src/physicsguard/core/hierarchy.py:RefinementPlanner.recommended_refinements', 'ExecuteMode.tree_view': 'src/physicsguard/core/tree_view.py:render_tree_view'}
USES = {
    'HierarchicalAuditRunner': 'src/physicsguard/core/hierarchy.py:HierarchicalAuditRunner',
    'ResidualBuilder': 'src/physicsguard/core/residual.py:ResidualBuilder',
}
TESTED_BY={'parent_fails_with_child': ['tests/test_hierarchy_scoring.py:test_real_heater_failure_propagates_through_two_ancestors_without_changing_own_scores', 'tests/test_hierarchy_runner.py:test_hierarchy_evaluate_observed_fault_identifies_block_and_recommends_refinement'], 'coarse_failure_with_passing_children_is_inconsistent': ['tests/test_hierarchy_scoring.py:test_refinement_consistency_uses_own_checked_coarse_relations'], 'planned_template_is_reported_not_executed': ['tests/test_hierarchy_refinement.py:test_unbuilt_template_is_planned'], 'tree_view_shows_every_block_verdict': ['tests/test_core.py:test_evaluate_prints_the_tree_with_verdicts'], 'verdict_lines_omit_structure': ['tests/test_core.py:test_evaluate_prints_the_tree_with_verdicts']}
MUTATIONS={'parent_ignores_children': 'parent_fails_with_child', 'coarse_failure_reported_consistent': 'coarse_failure_with_passing_children_is_inconsistent', 'planned_target_loaded': 'planned_template_is_reported_not_executed', 'tree_view_hides_a_failing_block': 'tree_view_shows_every_block_verdict', 'verdict_lines_repeat_structure': 'verdict_lines_omit_structure'}
REAL_CASE_IDS=('growth_coarse_bad_audit', 'growth_planned_bad_audit', 'hierarchy_evaluate_partial_tree_view_bad_audit', 'hierarchy_evaluate_derived_child_bad_audit', 'hierarchy_evaluate_partial_tree_view_not_checked')
LABELS={'growth_coarse_bad_audit': 'coarse_failure_consistency_reported', 'growth_planned_bad_audit': 'planned_template_reported_not_executed', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'tree_view_rendered_with_block_verdicts', 'hierarchy_evaluate_derived_child_bad_audit': 'child_failure_propagated', 'hierarchy_evaluate_derived_bad_audit': 'derived_relations_excluded_from_checks', 'hierarchy_evaluate_partial_unresolved': 'unobserved_residuals_skipped', 'clean': 'hierarchy_run_solved_and_reported', 'converged_bad_audit': 'optimizer_converged_audit_failed', 'bad_schema': 'schema_failed', 'evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'evaluate_missing_observed': 'derived_relations_excluded_from_checks', 'compare_bad_audit': 'hierarchy_compare_solved_and_evaluated', 'hierarchy_clean': 'hierarchy_run_solved_and_reported', 'hierarchy_bad_audit': 'optimizer_converged_audit_failed', 'hierarchy_evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_missing_observed': 'no_independent_observed_check_failed', 'hierarchy_evaluate_zero_product': 'no_independent_observed_check_failed', 'hierarchy_evaluate_partial_snapshot': 'unobserved_values_derived', 'hierarchy_describe': 'hierarchy_described_without_solver', 'assumption_parameter_fill': 'parameter_assumption_filled', 'assumption_parameter_override': 'assumption_override_warned', 'assumption_proposed': 'proposed_assumption_not_applied', 'assumption_rejected': 'rejected_assumption_not_applied', 'assumption_variable_boundary': 'variable_assumption_boundary_ready', 'hierarchy_evaluate_partial_tree_view_not_checked': 'tree_view_rendered_with_block_verdicts'}
# Expected finite fixture outcomes; conformance always runs native code afresh.
PORT_VALUES={'growth_coarse_bad_audit': 'FAIL', 'growth_planned_bad_audit': 'FAIL', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'FAIL', 'hierarchy_evaluate_derived_child_bad_audit': 'PASS', 'hierarchy_evaluate_derived_bad_audit': 'FAIL', 'hierarchy_evaluate_partial_unresolved': 'PASS', 'clean': 'PASS', 'converged_bad_audit': 'FAIL', 'bad_schema': 'no checks', 'evaluate_clean': 'PASS', 'evaluate_bad_audit': 'FAIL', 'evaluate_missing_observed': 'PASS', 'compare_bad_audit': 'no checks', 'hierarchy_clean': 'PASS', 'hierarchy_bad_audit': 'FAIL', 'hierarchy_evaluate_clean': 'no checks', 'hierarchy_evaluate_bad_audit': 'no checks', 'hierarchy_evaluate_missing_observed': 'no checks', 'hierarchy_evaluate_zero_product': 'no checks', 'hierarchy_evaluate_partial_snapshot': 'PASS', 'hierarchy_describe': 'no checks', 'assumption_parameter_fill': 'no checks', 'assumption_parameter_override': 'no checks', 'assumption_proposed': 'no checks', 'assumption_rejected': 'no checks', 'assumption_variable_boundary': 'no checks', 'hierarchy_evaluate_partial_tree_view_not_checked': 'not checked'}

@dataclass(frozen=True)
class State:
    child_failures: tuple[str,...] = ()
    parent_failures: tuple[str,...] = ()
    coarse_refinement_expected: tuple[str,...] = ()
    coarse_refinement_reported: tuple[str,...] = ()
    planned_refinements_expected: tuple[str,...] = ()
    planned_refinements_reported: tuple[str,...] = ()
    refinement_templates_loaded: tuple[str,...] = ()
    block_verdicts: tuple[str,...] = ()
    tree_view_rows: tuple[str,...] = ()
    solve_attempted: tuple[str,...] = ()
    tree_verdict: str = ""
    structure_rows: tuple[str,...] = ()

class Evaluate:
    name="Evaluate"
    reads=('solve_attempted', 'child_failures', 'parent_failures', 'coarse_refinement_expected', 'coarse_refinement_reported', 'planned_refinements_expected', 'planned_refinements_reported', 'refinement_templates_loaded', 'block_verdicts', 'tree_view_rows')
    writes=('solve_attempted', 'child_failures', 'parent_failures', 'coarse_refinement_expected', 'coarse_refinement_reported', 'planned_refinements_expected', 'planned_refinements_reported', 'refinement_templates_loaded', 'block_verdicts', 'tree_view_rows', 'tree_verdict', 'structure_rows')
    def __init__(self,defect=''):self.defect=defect
    def apply(self,q,state):
        key=q.case_id
        facts=stage_facts(q)
        incoming={name:facts[name] for name in READS_PARENT}
        state=replace(state,**incoming)
        values={}
        def put(name,condition):
            if condition:values[name]=(key,)
        active=key not in stage_facts(q)['failures'] and q.mode!='hierarchy_describe' and (q.mode not in ('hierarchy_run','hierarchy_compare') or key in state.solve_attempted)
        put('child_failures',active and 'child_bad_audit' in key)
        put('parent_failures',active and 'child_bad_audit' in key)
        put('coarse_refinement_expected',active and key=='growth_coarse_bad_audit')
        put('coarse_refinement_reported',active and key=='growth_coarse_bad_audit')
        put('planned_refinements_expected',active and key=='growth_planned_bad_audit')
        put('planned_refinements_reported',active and key=='growth_planned_bad_audit')
        if active:
            rows=[f"{key}:root:{PORT_VALUES.get(key, 'FAIL' if 'bad_audit' in key else 'PASS')}"]
            if 'child_bad_audit' in key:rows.append(f'{key}:child:FAIL')
            if not q.observed_values_complete:rows.append(f'{key}:leaf:not checked')
            rows.append(f'{key}:derived_only:no checks')
            values['block_verdicts']=tuple(rows);values['tree_view_rows']=tuple(rows)
        if self.defect=='parent_ignores_children':values['parent_failures']=()
        if self.defect=='coarse_failure_reported_consistent':values['coarse_refinement_reported']=()
        if self.defect=='planned_target_loaded' and key=='growth_planned_bad_audit':values['refinement_templates_loaded']=(key,)
        if self.defect=='tree_view_hides_a_failing_block' and values.get('tree_view_rows'):values['tree_view_rows']=values['tree_view_rows'][1:]
        if self.defect=='verdict_lines_repeat_structure' and active:values['structure_rows']=('components:',)
        values['tree_verdict']=PORT_VALUES.get(key,'no checks')
        result=replace(state,**incoming,**values)
        yield FunctionResult(result.tree_verdict,result,label=LABELS.get(key,'stage_checked'))


def parent_fails_with_child(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.child_failures) - set(state.parent_failures)
    return InvariantResult.fail(f"failed child omitted from parent verdict: {sorted(missing)}") if missing else InvariantResult.pass_()


def coarse_failure_with_passing_children_is_inconsistent(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.coarse_refinement_expected) - set(state.coarse_refinement_reported)
    return InvariantResult.fail(f"coarse failure with passing children lost its inconsistency: {sorted(missing)}") if missing else InvariantResult.pass_()


def planned_template_is_reported_not_executed(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.planned_refinements_expected) - set(state.planned_refinements_reported)
    loaded = set(state.planned_refinements_expected) & set(state.refinement_templates_loaded)
    return InvariantResult.fail(f"planned targets missing={sorted(missing)}, loaded={sorted(loaded)}") if missing or loaded else InvariantResult.pass_()


def tree_view_shows_every_block_verdict(state: State, trace) -> InvariantResult:
    del trace
    hidden = sorted(set(state.block_verdicts) - set(state.tree_view_rows))
    invented = sorted(set(state.tree_view_rows) - set(state.block_verdicts))
    unchecked_pass = sorted(row for row in state.tree_view_rows if row.split(":")[1] in {"leaf", "derived_only"} and row.endswith(":PASS"))
    if hidden or invented or unchecked_pass:
        return InvariantResult.fail(f"tree view disagrees with block verdicts: hidden={hidden}, invented={invented}, unchecked_pass={unchecked_pass}")
    return InvariantResult.pass_()

def verdict_lines_omit_structure(state,trace):
    return InvariantResult.fail('Verdict rows repeat components or links') if state.structure_rows else InvariantResult.pass_()

INVARIANTS=(Invariant('verdict_lines_omit_structure','Verdict lines contain results without repeating declared components or links.',verdict_lines_omit_structure),
    Invariant("parent_fails_with_child", "A failed child makes every containing parent fail.", parent_fails_with_child),
    Invariant("coarse_failure_with_passing_children_is_inconsistent", "Checked coarse failure with passing children is explicitly inconsistent.", coarse_failure_with_passing_children_is_inconsistent),
    Invariant("planned_template_is_reported_not_executed", "An unbuilt refinement is reported as planned and never loaded or executed.", planned_template_is_reported_not_executed),
    Invariant("tree_view_shows_every_block_verdict", "The tree view prints every block with the verdict of the report; a block without checked residuals is never PASS.", tree_view_shows_every_block_verdict),
)

def make(defect='',names=None):
    return Explorer(Workflow((Evaluate(defect),)),(State(),),EXTERNAL_INPUTS,
                    tuple(rule for rule in INVARIANTS if names is None or rule.name in names),
                    max_sequence_length=1,progress_steps=0)
def build_explorer():return make()
def broken_variants():return {name:make(name,{rule}) for name,rule in MUTATIONS.items()}

from contextlib import contextmanager

@contextmanager
def _rendered_lines():
    from physicsguard.core import tree_view
    original=tree_view.render_tree_view
    captured=[]
    def render(*args,**kwargs):
        text=original(*args,**kwargs);captured.extend(text.splitlines());return text
    tree_view.render_tree_view=render
    try:yield captured
    finally:tree_view.render_tree_view=original

def conformance():
    mismatches=[]
    cases={case.case_id:case for case in EXTERNAL_INPUTS}
    for key in REAL_CASE_IDS:
        q=cases[key]
        modeled=next(iter(Evaluate().apply(q,State())))
        try:
            with _rendered_lines() as lines:label,audit,ports,report,assumptions=replay_case(key)
            if key=='hierarchy_evaluate_partial_tree_view_bad_audit' and (not lines or any('components:' in line or line.startswith('links:') for line in lines)):
                mismatches.append('verdict_lines_omit_structure: verdict rows repeat declared structure')
            if label!=modeled.label:mismatches.append(f'{key}: native label {label!r}, model {modeled.label!r}')
            if audit is not None and audit!=q.residual_within_threshold:mismatches.append(f'{key}: audit_pass differs')
            if ports[2]!=modeled.new_state.tree_verdict:mismatches.append(f'{key}: native tree_verdict {ports[2]!r}, model {modeled.new_state.tree_verdict!r}')
        except Exception as exc:mismatches.append(f'{key}: real replay raised {type(exc).__name__}: {exc}')
    return ReplayReport(len(REAL_CASE_IDS),mismatches)
