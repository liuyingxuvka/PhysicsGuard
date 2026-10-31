"""tree_verdicts: one audit stage with fresh native replay of its own cases."""
from __future__ import annotations
from dataclasses import dataclass,replace
from flowguard import FunctionResult,Invariant,InvariantResult,Workflow
from flowguard.explorer import Explorer
from _core_fixture import AuditInput,EXTERNAL_INPUTS,ReplayReport,stage_facts,replay_case,ROOT

MODEL_ID='tree_verdicts'
PARENT="core"
READS_PARENT=('solve_attempted',)
OUTPUTS={'tree_verdict': ('PASS', 'FAIL', 'not checked', 'no checks')}
IMPLEMENTED_BY={'ExecuteMode.growth': 'src/physicsguard/core/hierarchy.py:RefinementPlanner.recommended_refinements', 'ExecuteMode.tree_view': 'src/physicsguard/core/tree_view.py:render_tree_view', 'RenderHints': 'src/physicsguard/core/tree_view.py:_report_tail'}
USES = {
    'HierarchicalAuditRunner': 'src/physicsguard/core/hierarchy.py:HierarchicalAuditRunner',
    'DescribeHierarchy': 'src/physicsguard/core/hierarchy.py:describe_hierarchy',
    'EvaluateObserved': 'src/physicsguard/core/hierarchy.py:HierarchicalAuditRunner.evaluate_observed',
    'ResidualBuilder': 'src/physicsguard/core/residual.py:ResidualBuilder',
    'LoadAudit': 'src/physicsguard/io/hierarchy_loader.py:load_hierarchical_audit_spec',
    'LoadObserved': 'src/physicsguard/io/observation_loader.py:load_observed_values',
}
TESTED_BY={'parent_fails_with_child': ['tests/test_hierarchy_scoring.py:test_real_heater_failure_propagates_through_two_ancestors_without_changing_own_scores', 'tests/test_hierarchy_runner.py:test_hierarchy_evaluate_observed_fault_identifies_block_and_recommends_refinement'], 'coarse_failure_with_passing_children_is_inconsistent': ['tests/test_hierarchy_scoring.py:test_refinement_consistency_uses_own_checked_coarse_relations'], 'planned_template_is_reported_not_executed': ['tests/test_hierarchy_refinement.py:test_unbuilt_template_is_planned'], 'tree_view_shows_every_block_verdict': ['tests/test_core.py:test_evaluate_prints_the_tree_with_verdicts'], 'verdict_lines_omit_structure': ['tests/test_core.py:test_evaluate_prints_the_tree_with_verdicts'], 'hint_shown_in_tree': ['tests/test_tree_view.py:test_unit_hint_line', 'tests/test_tree_view.py:test_conservation_hint_without_unit_hint'], 'resolution_shown': ['tests/test_tree_view.py:test_resolution_line_names_default_scale', 'tests/test_tree_view.py:test_resolution_rederives_values_and_keeps_checked_occurrence_scales', 'tests/test_tree_view.py:test_resolution_scale_origin_belongs_to_the_winning_residual', 'tests/test_tree_view.py:test_native_lookup_numeric_tables_keep_a_real_resolution', 'tests/test_tree_view.py:test_resolution_tree_order_empty_block_and_unknown_scale_source', 'tests/test_tree_view.py:test_resolution_is_optional_for_projectors_and_zero_sensitivity_is_unchecked']}
MUTATIONS={'parent_ignores_children': 'parent_fails_with_child', 'coarse_failure_reported_consistent': 'coarse_failure_with_passing_children_is_inconsistent', 'planned_target_loaded': 'planned_template_is_reported_not_executed', 'tree_view_hides_a_failing_block': 'tree_view_shows_every_block_verdict', 'verdict_lines_repeat_structure': 'verdict_lines_omit_structure', 'tree_view_hides_hint': 'hint_shown_in_tree', 'tree_view_hides_resolution': 'resolution_shown'}
REAL_CASE_IDS=('growth_coarse_bad_audit', 'growth_planned_bad_audit', 'hierarchy_evaluate_partial_tree_view_bad_audit', 'hierarchy_evaluate_derived_child_bad_audit', 'hierarchy_evaluate_partial_tree_view_not_checked')
LABELS={'growth_coarse_bad_audit': 'coarse_failure_consistency_reported', 'growth_planned_bad_audit': 'planned_template_reported_not_executed', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'tree_view_rendered_with_block_verdicts', 'hierarchy_evaluate_derived_child_bad_audit': 'child_failure_propagated', 'hierarchy_evaluate_derived_bad_audit': 'derived_relations_excluded_from_checks', 'hierarchy_evaluate_partial_unresolved': 'unobserved_residuals_skipped', 'clean': 'hierarchy_run_solved_and_reported', 'converged_bad_audit': 'optimizer_converged_audit_failed', 'bad_schema': 'schema_failed', 'evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'evaluate_missing_observed': 'derived_relations_excluded_from_checks', 'compare_bad_audit': 'hierarchy_compare_solved_and_evaluated', 'hierarchy_clean': 'hierarchy_run_solved_and_reported', 'hierarchy_bad_audit': 'optimizer_converged_audit_failed', 'hierarchy_evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_missing_observed': 'no_independent_observed_check_failed', 'hierarchy_evaluate_zero_product': 'no_independent_observed_check_failed', 'hierarchy_evaluate_partial_snapshot': 'unobserved_values_derived', 'hierarchy_describe': 'hierarchy_described_without_solver', 'assumption_parameter_fill': 'parameter_assumption_filled', 'assumption_parameter_override': 'assumption_override_warned', 'assumption_proposed': 'proposed_assumption_not_applied', 'assumption_rejected': 'rejected_assumption_not_applied', 'assumption_variable_boundary': 'variable_assumption_boundary_ready', 'hierarchy_evaluate_partial_tree_view_not_checked': 'tree_view_rendered_with_block_verdicts'}
# Expected finite fixture outcomes; conformance always runs native code afresh.
PORT_VALUES={'growth_coarse_bad_audit': 'FAIL', 'growth_planned_bad_audit': 'FAIL', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'FAIL', 'hierarchy_evaluate_derived_child_bad_audit': 'PASS', 'hierarchy_evaluate_derived_bad_audit': 'FAIL', 'hierarchy_evaluate_partial_unresolved': 'PASS', 'clean': 'PASS', 'converged_bad_audit': 'FAIL', 'bad_schema': 'no checks', 'evaluate_clean': 'PASS', 'evaluate_bad_audit': 'FAIL', 'evaluate_missing_observed': 'PASS', 'compare_bad_audit': 'no checks', 'hierarchy_clean': 'PASS', 'hierarchy_bad_audit': 'FAIL', 'hierarchy_evaluate_clean': 'no checks', 'hierarchy_evaluate_bad_audit': 'no checks', 'hierarchy_evaluate_missing_observed': 'no checks', 'hierarchy_evaluate_zero_product': 'no checks', 'hierarchy_evaluate_partial_snapshot': 'PASS', 'hierarchy_describe': 'no checks', 'assumption_parameter_fill': 'no checks', 'assumption_parameter_override': 'no checks', 'assumption_proposed': 'no checks', 'assumption_rejected': 'no checks', 'assumption_variable_boundary': 'no checks', 'hierarchy_evaluate_partial_tree_view_not_checked': 'not checked'}


# Both fixed observations carry conservation advice; only the unit slip carries a unit hint.
_CONSERVATION = "Inspect sibling inflow/outflow, loss, storage, and boundary-condition variables before adding deeper component physics."
HINT_ROWS = {
    'observed_q_kw': (
        "hint: conservation_balance heater.coolant_heat_balance, mix.flow_merge_temperature_balance: " + _CONSERVATION,
        "hint: unit_conversion heater.Q_dot_W multiply by 1000",
    ),
    'observed_ai': ("hint: conservation_balance mix.flow_merge_temperature_balance: " + _CONSERVATION,),
}
HINT_INPUTS = tuple(AuditInput(key, True, True, True, True, True, False, mode='hierarchy_evaluate') for key in HINT_ROWS)
PORT_VALUES.update({key: 'PASS' for key in HINT_ROWS})
PORT_VALUES['observed_ai_half'] = 'no checks'
RESOLUTION_ROWS = {
    'observed_ai': ('mix.T_out_K +-0.2 K',),
    'observed_ai_half': ('mix.T_out_K +-8 K (default scale)',),
}
RESOLUTION_INPUTS = (AuditInput('observed_ai_half', True, True, True, True, True, True, mode='hierarchy_evaluate'),)

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
    expected_hint_rows: tuple[str,...] = ()
    shown_hint_rows: tuple[str,...] = ()
    expected_resolution_rows: tuple[str,...] = ()
    shown_resolution_rows: tuple[str,...] = ()

class Evaluate:
    name="Evaluate"
    reads=('solve_attempted', 'child_failures', 'parent_failures', 'coarse_refinement_expected', 'coarse_refinement_reported', 'planned_refinements_expected', 'planned_refinements_reported', 'refinement_templates_loaded', 'block_verdicts', 'tree_view_rows')
    writes=('solve_attempted', 'child_failures', 'parent_failures', 'coarse_refinement_expected', 'coarse_refinement_reported', 'planned_refinements_expected', 'planned_refinements_reported', 'refinement_templates_loaded', 'block_verdicts', 'tree_view_rows', 'tree_verdict', 'structure_rows', 'expected_hint_rows', 'shown_hint_rows', 'expected_resolution_rows', 'shown_resolution_rows')
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
        hints = HINT_ROWS.get(key, ())
        values['expected_hint_rows'] = hints
        values['shown_hint_rows'] = hints[:-1] if self.defect == 'tree_view_hides_hint' else hints
        resolutions = RESOLUTION_ROWS.get(key, ())
        values['expected_resolution_rows'] = resolutions
        values['shown_resolution_rows'] = () if self.defect == 'tree_view_hides_resolution' else resolutions
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

def hint_shown_in_tree(state, trace):
    del trace
    return InvariantResult.fail('The tree dropped, reordered or invented a follow-up hint') if state.shown_hint_rows != state.expected_hint_rows else InvariantResult.pass_()


def resolution_shown(state, trace):
    del trace
    return InvariantResult.fail('A resolution, unit or default-scale mark is hidden') if state.shown_resolution_rows != state.expected_resolution_rows else InvariantResult.pass_()


INVARIANTS=(Invariant(name='resolution_shown', description='Every observed variable of a checked block is printed on a resolution line with its unit, and a module-default residual scale is marked.', predicate=resolution_shown),
    Invariant('hint_shown_in_tree', 'Every bug-family follow-up of the report is printed as one hint line on the compact tree.', hint_shown_in_tree),
    Invariant('verdict_lines_omit_structure','Verdict lines contain results without repeating declared components or links.',verdict_lines_omit_structure),
    Invariant("parent_fails_with_child", "A failed child makes every containing parent fail.", parent_fails_with_child),
    Invariant("coarse_failure_with_passing_children_is_inconsistent", "Checked coarse failure with passing children is explicitly inconsistent.", coarse_failure_with_passing_children_is_inconsistent),
    Invariant("planned_template_is_reported_not_executed", "An unbuilt refinement is reported as planned and never loaded or executed.", planned_template_is_reported_not_executed),
    Invariant("tree_view_shows_every_block_verdict", "The tree view prints every block with the verdict of the report; a block without checked residuals is never PASS.", tree_view_shows_every_block_verdict),
)

def make(defect='',names=None):
    return Explorer(Workflow((Evaluate(defect),)),(State(),),EXTERNAL_INPUTS + HINT_INPUTS + RESOLUTION_INPUTS,
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
    from physicsguard.core.hierarchy import HierarchicalAuditRunner, describe_hierarchy
    from physicsguard.core.tree_view import render_tree_view
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values
    shower = ROOT / 'examples/hierarchical/shower_mix'
    for case in HINT_INPUTS + RESOLUTION_INPUTS:
        case_mismatches = []
        try:
            audit_file = 'audit_default_scales.yaml' if case.case_id == 'observed_ai_half' else 'audit.yaml'
            spec = load_hierarchical_audit_spec(shower / audit_file)
            observed = load_observed_values(shower / (case.case_id + '.yaml'))
            runner = HierarchicalAuditRunner(spec, base_dir=shower)
            report = runner.to_dict(runner.evaluate_observed(observed))
            description = describe_hierarchy(spec, base_dir=shower)
            text = render_tree_view(description, report=report)
            rows = tuple(line for line in text.splitlines() if line.startswith('hint:'))
            modeled = next(iter(Evaluate().apply(case, State()))).new_state
            root = next(row for row in report['block_verdicts'] if row['level'] == 0)
            native_port = ('PASS' if root['own_audit_pass'] else 'FAIL') if root['checked_residual_count'] else 'not checked' if root['missing_required_variables'] else 'no checks'
            if native_port != modeled.tree_verdict:
                case_mismatches.append(f'native root port {native_port!r}, model {modeled.tree_verdict!r}')
            if case.case_id in HINT_ROWS and (rows != modeled.expected_hint_rows or len(rows) != len(report['bug_family_followups'])):
                case_mismatches.append(f'hint_shown_in_tree: expected {modeled.expected_hint_rows!r}, got {rows!r}')
            if case.case_id in RESOLUTION_ROWS:
                expected_value = 8.0 if case.case_id == 'observed_ai_half' else 0.2
                expected_default = case.case_id == 'observed_ai_half'
                resolution_lines = [line for line in text.splitlines() if line.startswith('resolution:')]
                fragment = RESOLUTION_ROWS[case.case_id][0]
                entry = report.get('resolution', {}).get('mix.T_out_K')
                if not any(fragment in line for line in resolution_lines) or entry is None:
                    case_mismatches.append(f'resolution_shown: missing native resolution {fragment!r}')
                elif abs(entry['value'] - expected_value) > expected_value * 1e-4 or entry['default_scale'] is not expected_default:
                    case_mismatches.append(f'resolution_shown: wrong native sensitivity or scale origin: {entry!r}')
                owned = {component: block['id'] for block in description['blocks'] for component in block['component_ids']}
                checked = {row['block_id'] for row in report['block_verdicts'] if row['checked_residual_count']}
                expected_variables = {name for name in observed.variables if owned.get(name.split('.', 1)[0]) in checked}
                resolution = report.get('resolution', {})
                if set(resolution) != expected_variables:
                    case_mismatches.append('resolution_shown: observed variables omitted or invented')
                visible = {part for line in resolution_lines for part in line.removeprefix('resolution: ').split(', ')}
                for name in expected_variables & resolution.keys():
                    entry = resolution[name]
                    if entry is None:
                        token = f'{name} unchecked'
                    else:
                        token = f"{name} +-{entry['value']:.2g} {entry['unit']}".rstrip() + (' (scale source unavailable)' if entry['default_scale'] is None else ' (default scale)' if entry['default_scale'] else '')
                        if entry['unit'] != observed.variables[name].unit or entry['residual'] not in report['checked_residuals']:
                            case_mismatches.append(f'resolution_shown: wrong unit or unchecked residual for {name}')
                    if token not in visible:
                        case_mismatches.append(f'resolution_shown: native line omits {token!r}')
        except Exception as exc:
            rule = 'resolution_shown' if case.case_id in RESOLUTION_ROWS else 'hint_shown_in_tree'
            case_mismatches.append(f'{rule}: real replay raised {type(exc).__name__}: {exc}')
        if case_mismatches:
            mismatches.append(f'{case.case_id}: ' + '; '.join(case_mismatches))
    return ReplayReport(len(REAL_CASE_IDS) + len(HINT_INPUTS) + len(RESOLUTION_INPUTS),mismatches)
