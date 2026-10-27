"""The coarse audit pipeline receives stage results without running child models."""
from __future__ import annotations
from dataclasses import dataclass,replace
from flowguard import FunctionResult,Invariant,InvariantResult,Workflow
from flowguard.explorer import Explorer
from _core_fixture import AuditInput,EXTERNAL_INPUTS,ReplayReport,stage_facts,replay_case

MODEL_ID='core'
PARENT='simulation'
COMPONENTS=['simulation','loaders']
IMPLEMENTED_BY={'ValidateSystem': 'src/physicsguard/io/yaml_loader.py:load_system_spec', 'AssembleResiduals': 'src/physicsguard/core/residual.py:ResidualBuilder', 'ExecuteMode.hierarchy': 'src/physicsguard/core/hierarchy.py:HierarchicalAuditRunner', 'ExecuteMode.describe': 'src/physicsguard/core/hierarchy.py:describe_hierarchy', 'GenerateDiagnostics': 'src/physicsguard/core/diagnostics.py:DiagnosticReporter.generate'}
TESTED_BY={'no_solve_without_valid_registry': ['tests/test_residual_builder.py:test_duplicate_fully_qualified_variables_fail', 'tests/test_solver.py:test_bounds_are_respected'], 'no_solve_without_normalized_residuals': ['tests/test_residual_builder.py:test_residual_vector_returns_normalized_values'], 'hierarchy_describe_does_not_solve': ['tests/test_hierarchy_spec.py:test_refines_requires_a_parent_owned_component_and_describe_exposes_it', 'tests/test_hierarchy_cli.py:test_describe_json_keeps_every_inspect_field']}
NOT_MODELED={'src/physicsguard/core/_residual_dependencies.py:_Capture._enter': 'Trace capture used only while collecting partial-snapshot residual dependencies; frame bookkeeping, no audit verdict. Its result is checked by tests/test_hierarchy_runner.py:test_partial_snapshot_does_not_invent_a_zero_product_residual and the hierarchy_evaluate_zero_product replay.', 'src/physicsguard/core/_residual_dependencies.py:_Capture._returned': 'Trace capture used only while collecting partial-snapshot residual dependencies; it records which registered values a returned residual read. Checked by tests/test_hierarchy_runner.py:test_partial_snapshot_skips_a_range_check_with_a_flat_local_region.', 'src/physicsguard/core/_residual_dependencies.py:_Capture._tree': 'Trace capture used only while collecting partial-snapshot residual dependencies; it caches the parsed source of native module files. Checked by tests/test_hierarchy_runner.py:test_partial_sum_tracks_external_reads_when_it_declares_no_variables.', 'src/physicsguard/core/_residual_dependencies.py:_Capture.trace': 'Trace capture used only while collecting partial-snapshot residual dependencies; it chains and restores the thread trace function. Checked by tests/test_hierarchy_runner.py:test_unclassified_custom_residual_is_not_licensed_by_finite_probes.', 'src/physicsguard/core/assumptions.py:AssumptionManager._set_card': "Private record update of one assumption card's disposition inside AssumptionManager; the dispositions are the model's assumption rules (assumptions_are_reported_in_diagnostics, assumption_overrides_are_warned) and are checked by tests/test_assumption_manager.py:test_explicit_parameter_override_requires_allow_override_and_warns.", 'src/physicsguard/modules/registry.py:_DescriptionParameters.__contains__': 'Read recorder used only while describing a module type: it logs which parameters a native constructor tests for; no audit state. Checked by tests/test_cli.py:test_every_registered_module_has_a_native_readable_description.', 'src/physicsguard/modules/registry.py:_DescriptionParameters.__getitem__': 'Read recorder used only while describing a module type: it logs which parameters a native constructor reads; no audit state. Checked by tests/test_cli.py:test_every_registered_module_has_a_native_readable_description.', 'src/physicsguard/cli.py:build_parser': 'Parser declarations are checked against every skill/readme command by test_skill_files_name_only_existing_commands; this contains no audit-state transition.', 'scripts/extract_test_file_manifest.py:main': 'Maintenance wrapper delegates to the native manifest reader covered by contract/CLI tests; no separate physical lifecycle.', 'scripts/portable_model_headers.py:main': 'Portable comment-header generation is checked by native header/parse tests; it changes no physical model data.', 'src/physicsguard/modules/registry.py:_DescriptionParameters.get': 'Read recorder used only while describing a module type: get logs the requested parameter and default through setdefault, like __getitem__ and __contains__; no audit state. Checked by tests/test_cli.py:test_every_registered_module_has_a_native_readable_description.'}
HANDOFF={"observed_derivation": {"observed": "observed_status"}, "assumptions": {"disposition": "assumption_status"},
         "tree_verdicts": {"tree_verdict": "tree_verdict"}, "solver_audit": {"audit": "audit_status"}}
KEEPS=('schema_valid',)
CHILD_RESULTS={'bad_schema': ('not_observed', 'none', 'no checks', 'not_run'), 'assumption_variable_boundary': ('not_observed', 'applied', 'no checks', 'not_run'), 'assumption_proposed': ('not_observed', 'not_applied', 'no checks', 'not_run'), 'assumption_parameter_override': ('not_observed', 'override_warned', 'no checks', 'not_run'), 'evaluate_clean': ('evaluated', 'none', 'PASS', 'not_run'), 'converged_bad_audit': ('not_observed', 'none', 'FAIL', 'failed'), 'clean': ('not_observed', 'none', 'PASS', 'passed'), 'hierarchy_evaluate_partial_unresolved': ('unobserved_listed', 'none', 'PASS', 'not_run'), 'hierarchy_evaluate_partial_tree_view_not_checked': ('unobserved_listed', 'none', 'not checked', 'not_run')}
REAL_CASE_IDS=('clean', 'bad_schema', 'hierarchy_describe')
MUTATIONS={'invalid_registry_reaches_solver': 'no_solve_without_valid_registry', 'raw_residual_reaches_solver': 'no_solve_without_normalized_residuals', 'describe_solves': 'hierarchy_describe_does_not_solve'}
LABELS={'growth_coarse_bad_audit': 'coarse_failure_consistency_reported', 'growth_planned_bad_audit': 'planned_template_reported_not_executed', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'tree_view_rendered_with_block_verdicts', 'hierarchy_evaluate_derived_child_bad_audit': 'child_failure_propagated', 'hierarchy_evaluate_derived_bad_audit': 'derived_relations_excluded_from_checks', 'hierarchy_evaluate_partial_unresolved': 'unobserved_residuals_skipped', 'clean': 'hierarchy_run_solved_and_reported', 'converged_bad_audit': 'optimizer_converged_audit_failed', 'bad_schema': 'schema_failed', 'evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'evaluate_missing_observed': 'derived_relations_excluded_from_checks', 'compare_bad_audit': 'hierarchy_compare_solved_and_evaluated', 'hierarchy_clean': 'hierarchy_run_solved_and_reported', 'hierarchy_bad_audit': 'optimizer_converged_audit_failed', 'hierarchy_evaluate_clean': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_bad_audit': 'hierarchy_observed_evaluated_without_solver', 'hierarchy_evaluate_missing_observed': 'no_independent_observed_check_failed', 'hierarchy_evaluate_zero_product': 'no_independent_observed_check_failed', 'hierarchy_evaluate_partial_snapshot': 'unobserved_values_derived', 'hierarchy_describe': 'hierarchy_described_without_solver', 'assumption_parameter_fill': 'parameter_assumption_filled', 'assumption_parameter_override': 'assumption_override_warned', 'assumption_proposed': 'proposed_assumption_not_applied', 'assumption_rejected': 'rejected_assumption_not_applied', 'assumption_variable_boundary': 'variable_assumption_boundary_ready', 'hierarchy_evaluate_partial_tree_view_not_checked': 'tree_view_rendered_with_block_verdicts'}

@dataclass(frozen=True)
class State:
    schema_valid: tuple[str,...] = ()
    registry_valid: tuple[str,...] = ()
    residuals_normalized: tuple[str,...] = ()
    solve_attempted: tuple[str,...] = ()
    comparisons: tuple[str,...] = ()
    hierarchy_reports: tuple[str,...] = ()
    hierarchy_descriptions: tuple[str,...] = ()
    diagnostics_emitted: tuple[str,...] = ()
    failures: tuple[str,...] = ()
    observed_status: tuple[str,...] = ()
    assumption_status: tuple[str,...] = ()
    tree_verdict: tuple[str,...] = ()
    audit_status: tuple[str,...] = ()

@dataclass(frozen=True)
class Results:
    case_id:str
    observed:str
    disposition:str
    tree_verdict:str
    audit:str

@dataclass(frozen=True)
class Failed:
    case_id:str

class ValidateSystem:
    name='ValidateSystem'
    reads=()
    writes=('schema_valid','failures')
    accepted_input_type=AuditInput
    def apply(self,q,state):
        valid=stage_facts(q)['schema_valid']
        new=replace(state,schema_valid=state.schema_valid+valid,failures=state.failures+(() if valid else (q.case_id,)))
        yield FunctionResult(q if valid else Failed(q.case_id),new,label='schema_valid' if valid else 'schema_failed')

class BuildRegistry:
    name='BuildRegistry'
    reads=('schema_valid',)
    writes=('registry_valid','failures')
    accepted_input_type=AuditInput
    def __init__(self,defect=''):self.defect=defect
    def apply(self,q,state):
        valid=stage_facts(q)['registry_valid']
        allow=bool(valid) or self.defect=='invalid_registry_reaches_solver'
        new=replace(state,registry_valid=state.registry_valid+valid,failures=state.failures+(() if allow else (q.case_id,)))
        yield FunctionResult(q if allow else Failed(q.case_id),new,label='registry_ready' if allow else 'registry_failed')

class AssembleResiduals:
    name='AssembleResiduals'
    reads=('registry_valid',)
    writes=('residuals_normalized','failures')
    accepted_input_type=AuditInput
    def __init__(self,defect=''):self.defect=defect
    def apply(self,q,state):
        facts=stage_facts(q)
        allow=not facts['failures'] or self.defect in ('invalid_registry_reaches_solver','raw_residual_reaches_solver')
        new=replace(state,residuals_normalized=state.residuals_normalized+facts['residuals_normalized'],failures=state.failures+(() if allow else (q.case_id,)))
        yield FunctionResult(q if allow else Failed(q.case_id),new,label='residuals_ready' if allow else 'residual_setup_failed')

class ExecuteMode:
    name='ExecuteMode'
    reads=('registry_valid','residuals_normalized')
    writes=('solve_attempted','comparisons','hierarchy_reports','hierarchy_descriptions')
    accepted_input_type=AuditInput
    def __init__(self,defect=''):self.defect=defect
    def apply(self,q,state):
        facts=stage_facts(q)
        solved=facts['solve_attempted']
        if self.defect=='invalid_registry_reaches_solver' and not facts['registry_valid']:solved=(q.case_id,)
        if self.defect=='raw_residual_reaches_solver' and 'raw_residual' in q.case_id:solved=(q.case_id,)
        if self.defect=='describe_solves' and q.mode=='hierarchy_describe':solved=(q.case_id,)
        new=replace(state,solve_attempted=state.solve_attempted+solved,
                    comparisons=state.comparisons+facts['comparisons'],hierarchy_reports=state.hierarchy_reports+facts['hierarchy_reports'],
                    hierarchy_descriptions=state.hierarchy_descriptions+facts['hierarchy_descriptions'])
        yield FunctionResult(q,new,label=LABELS.get(q.case_id,'mode_completed'))

class GenerateDiagnostics:
    name='GenerateDiagnostics'
    reads=('solve_attempted','comparisons','hierarchy_reports','hierarchy_descriptions','failures')
    writes=('diagnostics_emitted',)
    accepted_input_type=AuditInput
    def apply(self,q,state):
        new=replace(state,diagnostics_emitted=state.diagnostics_emitted+stage_facts(q)['diagnostics_emitted'])
        yield FunctionResult(Results(q.case_id,*CHILD_RESULTS.get(q.case_id,('not_observed','none','no checks','not_run'))),new,label='diagnostics_emitted')

class CollectResults:
    name='CollectResults'
    reads=()
    writes=('observed_status','assumption_status','tree_verdict','audit_status')
    accepted_input_type=Results
    def apply(self,event,state):
        new=replace(state,observed_status=state.observed_status+(event.observed,),assumption_status=state.assumption_status+(event.disposition,),
                    tree_verdict=state.tree_verdict+(event.tree_verdict,),audit_status=state.audit_status+(event.audit,))
        yield FunctionResult(event,new,label='stage_results_received')


def no_solve_without_valid_registry(state: State, trace) -> InvariantResult:
    del trace
    missing = tuple(sorted(set(state.solve_attempted) - set(state.registry_valid)))
    if missing:
        return InvariantResult.fail(f"solve attempted without valid registry: {missing!r}")
    return InvariantResult.pass_()


def no_solve_without_normalized_residuals(state: State, trace) -> InvariantResult:
    del trace
    missing = tuple(sorted(set(state.solve_attempted) - set(state.residuals_normalized)))
    if missing:
        return InvariantResult.fail(f"solve attempted without normalized residuals: {missing!r}")
    return InvariantResult.pass_()


def hierarchy_describe_does_not_solve(state: State, trace) -> InvariantResult:
    del trace
    bad = tuple(sorted(set(state.hierarchy_descriptions) & set(state.solve_attempted)))
    if bad:
        return InvariantResult.fail(f"hierarchy describe unexpectedly solved: {bad!r}")
    return InvariantResult.pass_()

INVARIANTS=(
    Invariant(
        name="no_solve_without_valid_registry",
        description="The solver is reached only after variable registry validation.",
        predicate=no_solve_without_valid_registry,
    ),
    Invariant(
        name="no_solve_without_normalized_residuals",
        description="The solver is reached only with normalized residuals.",
        predicate=no_solve_without_normalized_residuals,
    ),
    Invariant(
        name="hierarchy_describe_does_not_solve",
        description="Hierarchy describe validates structure without a solve attempt.",
        predicate=hierarchy_describe_does_not_solve,
    ),
)

def terminal_predicate(output,state,trace):return isinstance(output,Failed)
def build_workflow(defect=''):
    return Workflow((ValidateSystem(),BuildRegistry(defect),AssembleResiduals(defect),ExecuteMode(defect),GenerateDiagnostics(),CollectResults()))
def make(defect='',names=None):
    cases=tuple(q for q in EXTERNAL_INPUTS if q.case_id in CHILD_RESULTS or q.case_id in REAL_CASE_IDS or q.case_id in ('bad_bounds','raw_residual'))
    return Explorer(build_workflow(defect),(State(),),cases,
                    tuple(rule for rule in INVARIANTS if names is None or rule.name in names),
                    max_sequence_length=2,terminal_predicate=terminal_predicate,progress_steps=0)
def build_explorer():return make()
def broken_variants():return {name:make(name,{rule}) for name,rule in MUTATIONS.items()}

def conformance():
    mismatches=[]
    cases={q.case_id:q for q in EXTERNAL_INPUTS}
    keys=tuple(dict.fromkeys((*REAL_CASE_IDS,*CHILD_RESULTS)))
    for key in keys:
        q=cases[key]
        run=build_workflow().execute(State(),q,terminal_predicate=terminal_predicate)
        model_labels=[step.label for step in run.completed_paths[0].trace.steps]
        try:
            label,audit,ports,report,assumptions=replay_case(key)
            if key in REAL_CASE_IDS:
                if label not in model_labels:mismatches.append(f'{key}: native label {label!r}, model {model_labels!r}')
                if audit is not None and audit!=q.residual_within_threshold:mismatches.append(f'{key}: audit_pass differs')
            if key in CHILD_RESULTS and tuple(ports)!=CHILD_RESULTS[key]:mismatches.append(f'{key}: native stage values {ports!r}, expected {CHILD_RESULTS[key]!r}')
        except Exception as exc:mismatches.append(f'{key}: real replay raised {type(exc).__name__}: {exc}')
    return ReplayReport(len(keys),mismatches)
