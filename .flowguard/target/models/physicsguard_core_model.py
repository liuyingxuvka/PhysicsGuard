"""Executable guards for hierarchy run, observed evaluate, reference compare and read-only describe.

Preserve finite registry/normalized residual requirements, explicit assumptions,
immutable observed values, bounded partial derivation and independent checks.
Coarse/detail consistency and planned refinement are reported without executing
templates; numerical convergence alone never licenses an audit pass. The one tree
view shows every block with the verdict the report gives it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class AuditInput:
    case_id: str
    valid_schema: bool
    finite_bounded_variables: bool
    known_references: bool
    normalized_residuals: bool
    solver_converges: bool
    residual_within_threshold: bool
    has_post_check_residuals: bool = False
    post_check_enters_solver: bool = False
    mode: str = "hierarchy_run"
    observed_values_complete: bool = True
    has_assumptions: bool = False
    parameter_assumption: bool = False
    variable_assumption: bool = False
    assumption_override: bool = False
    proposed_assumption: bool = False
    rejected_assumption: bool = False
    assumption_as_free_variable: bool = False
    unobserved_zero_product: bool = False


@dataclass(frozen=True)
class Validated:
    case_id: str
    has_post_check_residuals: bool = False
    post_check_enters_solver: bool = False
    mode: str = "hierarchy_run"
    observed_values_complete: bool = True
    has_assumptions: bool = False
    parameter_assumption: bool = False
    variable_assumption: bool = False
    assumption_override: bool = False
    proposed_assumption: bool = False
    rejected_assumption: bool = False
    assumption_as_free_variable: bool = False
    unobserved_zero_product: bool = False


@dataclass(frozen=True)
class RegistryReady:
    case_id: str
    has_post_check_residuals: bool = False
    post_check_enters_solver: bool = False
    mode: str = "hierarchy_run"
    observed_values_complete: bool = True
    has_assumptions: bool = False
    parameter_assumption: bool = False
    variable_assumption: bool = False
    assumption_override: bool = False
    proposed_assumption: bool = False
    rejected_assumption: bool = False
    unobserved_zero_product: bool = False


@dataclass(frozen=True)
class ResidualsReady:
    case_id: str
    mode: str = "hierarchy_run"
    observed_values_complete: bool = True
    has_assumptions: bool = False
    parameter_assumption: bool = False
    variable_assumption: bool = False
    assumption_override: bool = False
    proposed_assumption: bool = False
    rejected_assumption: bool = False


@dataclass(frozen=True)
class HierarchyFinished:
    case_id: str
    optimization_success: bool
    audit_pass: bool
    observed_only: bool = False
    compare_mode: bool = False


@dataclass(frozen=True)
class HierarchyInspected:
    case_id: str


@dataclass(frozen=True)
class DiagnosticsReady:
    case_id: str


@dataclass(frozen=True)
class SetupFailed:
    case_id: str
    reason: str


@dataclass(frozen=True)
class State:
    schema_valid: tuple[str, ...] = ()
    registry_valid: tuple[str, ...] = ()
    residuals_normalized: tuple[str, ...] = ()
    post_checks_diagnostic_only: tuple[str, ...] = ()
    solve_attempted: tuple[str, ...] = ()
    observed_evaluations: tuple[str, ...] = ()
    observed_without_solver: tuple[str, ...] = ()
    comparisons: tuple[str, ...] = ()
    hierarchy_reports: tuple[str, ...] = ()
    hierarchy_descriptions: tuple[str, ...] = ()
    assumptions_seen: tuple[str, ...] = ()
    assumptions_reported: tuple[str, ...] = ()
    parameter_assumptions_applied: tuple[str, ...] = ()
    variable_assumptions_fixed: tuple[str, ...] = ()
    assumption_overrides_warned: tuple[str, ...] = ()
    proposed_assumptions_not_applied: tuple[str, ...] = ()
    rejected_assumptions_not_applied: tuple[str, ...] = ()
    optimization_successes: tuple[str, ...] = ()
    audit_passes: tuple[str, ...] = ()
    audit_failures: tuple[str, ...] = ()
    diagnostics_emitted: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    unobserved_skipped: tuple[str, ...] = ()
    unobserved_listed: tuple[str, ...] = ()
    residuals_from_guess: tuple[str, ...] = ()
    variable_assumptions_expected: tuple[str, ...] = ()
    assumption_overrides_expected: tuple[str, ...] = ()
    post_checks_in_solver: tuple[str, ...] = ()
    derivation_cases: tuple[str, ...] = ()
    producing_relations: tuple[str, ...] = ()
    checked_relations: tuple[str, ...] = ()
    child_failures: tuple[str, ...] = ()
    parent_failures: tuple[str, ...] = ()
    coarse_refinement_expected: tuple[str, ...] = ()
    coarse_refinement_reported: tuple[str, ...] = ()
    planned_refinements_expected: tuple[str, ...] = ()
    planned_refinements_reported: tuple[str, ...] = ()
    refinement_templates_loaded: tuple[str, ...] = ()
    block_verdicts: tuple[str, ...] = ()
    tree_view_rows: tuple[str, ...] = ()


class ValidateSystem:
    name = "ValidateSystem"
    reads = ()
    writes = ("schema_valid", "failures")
    accepted_input_type = AuditInput
    input_description = "YAML/SystemSpec audit input"
    output_description = "Validated or SetupFailed"
    idempotency = "Validation is deterministic and has no external side effects."

    def apply(self, input_obj: AuditInput, state: State) -> Iterable[FunctionResult]:
        if not input_obj.valid_schema:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "invalid_schema"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="schema_failed",
            )
            return
        yield FunctionResult(
            output=Validated(
                input_obj.case_id,
                input_obj.has_post_check_residuals,
                input_obj.post_check_enters_solver,
                input_obj.mode,
                input_obj.observed_values_complete,
                input_obj.has_assumptions,
                input_obj.parameter_assumption,
                input_obj.variable_assumption,
                input_obj.assumption_override,
                input_obj.proposed_assumption,
                input_obj.rejected_assumption,
                input_obj.assumption_as_free_variable,
                input_obj.unobserved_zero_product,
            ),
            new_state=replace(state, schema_valid=state.schema_valid + (input_obj.case_id,)),
            label="schema_valid",
        )


class BuildRegistry:
    name = "BuildRegistry"
    reads = ("schema_valid",)
    writes = (
        "registry_valid",
        "variable_assumptions_expected",
        "assumption_overrides_expected",
        "assumptions_seen",
        "parameter_assumptions_applied",
        "assumption_overrides_warned",
        "proposed_assumptions_not_applied",
        "rejected_assumptions_not_applied",
        "failures",
    )
    accepted_input_type = Validated
    input_description = "Validated"
    output_description = "RegistryReady or SetupFailed"
    idempotency = "Registry build fails before solving when variable records are invalid."

    def apply(self, input_obj: Validated, state: State) -> Iterable[FunctionResult]:
        if input_obj.case_id not in state.schema_valid:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "schema_not_validated"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="registry_missing_schema",
            )
            return
        if "bad_bounds" in input_obj.case_id:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "invalid_bounds"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="registry_failed",
            )
            return
        if input_obj.assumption_as_free_variable:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "assumption_as_free_variable"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="assumption_free_variable_failed",
            )
            return
        yield FunctionResult(
            output=RegistryReady(
                input_obj.case_id,
                input_obj.has_post_check_residuals,
                input_obj.post_check_enters_solver,
                input_obj.mode,
                input_obj.observed_values_complete,
                input_obj.has_assumptions,
                input_obj.parameter_assumption,
                input_obj.variable_assumption,
                input_obj.assumption_override,
                input_obj.proposed_assumption,
                input_obj.rejected_assumption,
                input_obj.unobserved_zero_product,
            ),
            new_state=replace(
                state,
                registry_valid=state.registry_valid + (input_obj.case_id,),
                variable_assumptions_expected=(
                    state.variable_assumptions_expected + (input_obj.case_id,)
                    if input_obj.variable_assumption else state.variable_assumptions_expected
                ),
                assumption_overrides_expected=(
                    state.assumption_overrides_expected + (input_obj.case_id,)
                    if input_obj.assumption_override else state.assumption_overrides_expected
                ),
                assumptions_seen=(
                    state.assumptions_seen + (input_obj.case_id,)
                    if input_obj.has_assumptions
                    else state.assumptions_seen
                ),
                parameter_assumptions_applied=(
                    state.parameter_assumptions_applied + (input_obj.case_id,)
                    if input_obj.parameter_assumption
                    else state.parameter_assumptions_applied
                ),
                assumption_overrides_warned=(
                    state.assumption_overrides_warned + (input_obj.case_id,)
                    if input_obj.assumption_override
                    else state.assumption_overrides_warned
                ),
                proposed_assumptions_not_applied=(
                    state.proposed_assumptions_not_applied + (input_obj.case_id,)
                    if input_obj.proposed_assumption
                    else state.proposed_assumptions_not_applied
                ),
                rejected_assumptions_not_applied=(
                    state.rejected_assumptions_not_applied + (input_obj.case_id,)
                    if input_obj.rejected_assumption
                    else state.rejected_assumptions_not_applied
                ),
            ),
            label=(
                "assumption_override_warned"
                if input_obj.assumption_override
                else "parameter_assumption_filled"
                if input_obj.parameter_assumption
                else "proposed_assumption_not_applied"
                if input_obj.proposed_assumption
                else "rejected_assumption_not_applied"
                if input_obj.rejected_assumption
                else "registry_ready"
            ),
        )


class AssembleResiduals:
    name = "AssembleResiduals"
    reads = ("registry_valid",)
    writes = ('residuals_normalized', 'variable_assumptions_fixed', 'failures', 'derivation_cases', 'producing_relations', 'coarse_refinement_expected', 'planned_refinements_expected')
    accepted_input_type = RegistryReady
    input_description = "RegistryReady"
    output_description = "ResidualsReady or SetupFailed"
    idempotency = "Residual assembly has no durable side effects."

    def apply(self, input_obj: RegistryReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.case_id not in state.registry_valid:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "registry_not_ready"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="residual_missing_registry",
            )
            return
        if "unknown_ref" in input_obj.case_id:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "unknown_variable_reference"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="residual_reference_failed",
            )
            return
        if "raw_residual" in input_obj.case_id:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "residuals_not_normalized"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="residual_normalization_failed",
            )
            return
        if input_obj.post_check_enters_solver:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "post_check_in_solver"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="post_check_solver_selection_failed",
            )
            return
        if (
            input_obj.mode == "hierarchy_evaluate"
            and not input_obj.observed_values_complete
            and ("partial" in input_obj.case_id or "derived" in input_obj.case_id
                 or input_obj.case_id == "evaluate_missing_observed")
        ):
            derives = "unresolved" not in input_obj.case_id
            yield FunctionResult(
                output=ResidualsReady(input_obj.case_id, input_obj.mode, input_obj.observed_values_complete),
                new_state=replace(
                    state,
                    residuals_normalized=state.residuals_normalized + (input_obj.case_id,),
                    unobserved_skipped=state.unobserved_skipped + (() if derives else (input_obj.case_id,)),
                    unobserved_listed=state.unobserved_listed + (input_obj.case_id,),
                    derivation_cases=state.derivation_cases + ((input_obj.case_id,) if derives else ()),
                    producing_relations=state.producing_relations + ((f"{input_obj.case_id}:producing",) if derives else ()),
                ),
                label="unobserved_values_derived" if derives else "unobserved_residuals_skipped",
            )
            return
        if input_obj.mode == "hierarchy_evaluate" and not input_obj.observed_values_complete:
            # The partial/derived cases above have independent checks. These cases
            # have none after derivation; a missing input alone is not a refusal.
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "no_independent_observed_check"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="no_independent_observed_check_failed",
            )
            return
        if input_obj.mode == "hierarchy_compare" and not input_obj.observed_values_complete:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "missing_observed_values"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="missing_observed_values_failed",
            )
            return
        if input_obj.mode == "hierarchy_describe":
            yield FunctionResult(
                output=ResidualsReady(
                    input_obj.case_id,
                    input_obj.mode,
                    input_obj.observed_values_complete,
                    input_obj.has_assumptions,
                    input_obj.parameter_assumption,
                    input_obj.variable_assumption,
                    input_obj.assumption_override,
                    input_obj.proposed_assumption,
                    input_obj.rejected_assumption,
                ),
                new_state=state,
                label="hierarchy_index_ready",
            )
            return
        yield FunctionResult(
            output=ResidualsReady(
                input_obj.case_id,
                input_obj.mode,
                input_obj.observed_values_complete,
                input_obj.has_assumptions,
                input_obj.parameter_assumption,
                input_obj.variable_assumption,
                input_obj.assumption_override,
                input_obj.proposed_assumption,
                input_obj.rejected_assumption,
            ),
            new_state=replace(
                state,
                residuals_normalized=state.residuals_normalized + (input_obj.case_id,),
                coarse_refinement_expected=state.coarse_refinement_expected + ((input_obj.case_id,) if input_obj.case_id == "growth_coarse_bad_audit" else ()),
                planned_refinements_expected=state.planned_refinements_expected + ((input_obj.case_id,) if input_obj.case_id == "growth_planned_bad_audit" else ()),

                variable_assumptions_fixed=(
                    state.variable_assumptions_fixed + (input_obj.case_id,)
                    if input_obj.variable_assumption
                    else state.variable_assumptions_fixed
                ),
                post_checks_diagnostic_only=(
                    state.post_checks_diagnostic_only + (input_obj.case_id,)
                    if input_obj.has_post_check_residuals
                    else state.post_checks_diagnostic_only
                ),
            ),
            label=(
                "variable_assumption_boundary_ready"
                if input_obj.variable_assumption
                else "residuals_ready"
            ),
        )


def _block_verdicts(input_obj: ResidualsReady) -> tuple[str, ...]:
    """Abstract per-block verdicts of one report: a checked block passes or fails,
    a block with missing inputs is not checked, a block with only producing
    relations has no checks (never PASS)."""
    case = input_obj.case_id
    rows = [f"{case}:root:{'FAIL' if 'bad_audit' in case else 'PASS'}"]
    if "child_bad_audit" in case:
        rows.append(f"{case}:child:FAIL")
    if not input_obj.observed_values_complete:
        rows.append(f"{case}:leaf:not checked")
    rows.append(f"{case}:derived_only:no checks")
    return tuple(rows)


def _with_tree_view(state: State, input_obj: ResidualsReady) -> State:
    rows = _block_verdicts(input_obj)
    return replace(state, block_verdicts=state.block_verdicts + rows, tree_view_rows=state.tree_view_rows + rows)


class ExecuteMode:
    name = "ExecuteMode"
    reads = ('registry_valid', 'residuals_normalized', 'coarse_refinement_expected', 'planned_refinements_expected')
    writes = ('solve_attempted', 'observed_evaluations', 'observed_without_solver', 'comparisons', 'hierarchy_reports', 'hierarchy_descriptions', 'checked_relations', 'child_failures', 'parent_failures', 'coarse_refinement_reported', 'planned_refinements_reported', 'refinement_templates_loaded', 'block_verdicts', 'tree_view_rows')
    accepted_input_type = ResidualsReady
    input_description = "ResidualsReady"
    output_description = "HierarchyFinished, HierarchyInspected, or SetupFailed"
    idempotency = "Mode execution is deterministic for this audit case."

    def apply(self, input_obj: ResidualsReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.case_id not in state.registry_valid:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "solver_setup_invalid"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="solver_setup_failed",
            )
            return
        if input_obj.mode == "hierarchy_describe":
            yield FunctionResult(
                output=HierarchyInspected(input_obj.case_id),
                new_state=replace(
                    state,
                    hierarchy_descriptions=state.hierarchy_descriptions
                    + (input_obj.case_id,),
                ),
                label="hierarchy_described_without_solver",
            )
            return
        if input_obj.case_id not in state.residuals_normalized:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "solver_setup_invalid"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="solver_setup_failed",
            )
            return
        if input_obj.mode == "hierarchy_evaluate":
            audit_pass = "bad_audit" not in input_obj.case_id
            yield FunctionResult(
                output=HierarchyFinished(
                    input_obj.case_id,
                    optimization_success=True,
                    audit_pass=audit_pass,
                    observed_only=True,
                ),
                new_state=replace(
                    _with_tree_view(state, input_obj),
                    observed_evaluations=state.observed_evaluations + (input_obj.case_id,),
                    observed_without_solver=state.observed_without_solver + (input_obj.case_id,),
                    hierarchy_reports=state.hierarchy_reports + (input_obj.case_id,),
                    coarse_refinement_reported=state.coarse_refinement_reported + ((input_obj.case_id,) if input_obj.case_id in state.coarse_refinement_expected else ()),
                    planned_refinements_reported=state.planned_refinements_reported + ((input_obj.case_id,) if input_obj.case_id in state.planned_refinements_expected else ()),

                    checked_relations=state.checked_relations + (f"{input_obj.case_id}:independent",),
                    child_failures=state.child_failures + ((input_obj.case_id,) if "child_bad_audit" in input_obj.case_id else ()),
                    parent_failures=state.parent_failures + ((input_obj.case_id,) if "child_bad_audit" in input_obj.case_id else ()),
                    audit_passes=(
                        state.audit_passes + (input_obj.case_id,)
                        if audit_pass
                        else state.audit_passes
                    ),
                    audit_failures=(
                        state.audit_failures + (input_obj.case_id,)
                        if not audit_pass
                        else state.audit_failures
                    ),
                ),
                label=("tree_view_rendered_with_block_verdicts" if "tree_view" in input_obj.case_id else
                       "coarse_failure_consistency_reported" if input_obj.case_id in state.coarse_refinement_expected else
                       "planned_template_reported_not_executed" if input_obj.case_id in state.planned_refinements_expected else
                       "child_failure_propagated" if "child_bad_audit" in input_obj.case_id else
                       "derived_relations_excluded_from_checks" if input_obj.case_id in state.derivation_cases
                       else "hierarchy_observed_evaluated_without_solver"),
            )
            return
        if input_obj.mode == "hierarchy_compare":
            audit_pass = "bad_audit" not in input_obj.case_id
            yield FunctionResult(
                output=HierarchyFinished(
                    input_obj.case_id,
                    optimization_success="no_converge" not in input_obj.case_id,
                    audit_pass=audit_pass,
                    compare_mode=True,
                ),
                new_state=replace(
                    _with_tree_view(state, input_obj),
                    solve_attempted=state.solve_attempted + (input_obj.case_id,),
                    observed_evaluations=state.observed_evaluations + (input_obj.case_id,),
                    comparisons=state.comparisons + (input_obj.case_id,),
                    hierarchy_reports=state.hierarchy_reports + (input_obj.case_id,),
                    optimization_successes=(
                        state.optimization_successes + (input_obj.case_id,)
                        if "no_converge" not in input_obj.case_id
                        else state.optimization_successes
                    ),
                    audit_passes=(
                        state.audit_passes + (input_obj.case_id,)
                        if audit_pass
                        else state.audit_passes
                    ),
                    audit_failures=(
                        state.audit_failures + (input_obj.case_id,)
                        if not audit_pass
                        else state.audit_failures
                    ),
                ),
                label="hierarchy_compare_solved_and_evaluated",
            )
            return
        if input_obj.mode in {"hierarchy_run"}:
            audit_pass = "bad_audit" not in input_obj.case_id
            yield FunctionResult(
                output=HierarchyFinished(
                    input_obj.case_id,
                    optimization_success="no_converge" not in input_obj.case_id,
                    audit_pass=audit_pass,
                ),
                new_state=replace(
                    _with_tree_view(state, input_obj),
                    solve_attempted=state.solve_attempted + (input_obj.case_id,),
                    hierarchy_reports=state.hierarchy_reports + (input_obj.case_id,),
                    optimization_successes=(
                        state.optimization_successes + (input_obj.case_id,)
                        if "no_converge" not in input_obj.case_id
                        else state.optimization_successes
                    ),
                    audit_passes=(
                        state.audit_passes + (input_obj.case_id,)
                        if audit_pass
                        else state.audit_passes
                    ),
                    audit_failures=(
                        state.audit_failures + (input_obj.case_id,)
                        if not audit_pass
                        else state.audit_failures
                    ),
                ),
                label=(
                    "optimizer_converged_audit_failed"
                    if not audit_pass and "no_converge" not in input_obj.case_id
                    else "hierarchy_run_solved_and_reported"
                ),
            )
            return
        yield FunctionResult(
            output=SetupFailed(input_obj.case_id, "unsupported_mode"),
            new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
            label="unsupported_mode_failed",
        )


class GenerateDiagnostics:
    name = "GenerateDiagnostics"
    reads = (
        "solve_attempted",
        "observed_evaluations",
        "comparisons",
        "hierarchy_reports",
        "hierarchy_descriptions",
        "parameter_assumptions_applied",
        "variable_assumptions_fixed",
        "assumption_overrides_warned",
        "proposed_assumptions_not_applied",
        "rejected_assumptions_not_applied",
        "failures",
    )
    writes = ("diagnostics_emitted", "assumptions_reported")
    accepted_input_type = object
    input_description = "HierarchyFinished, HierarchyInspected, or SetupFailed"
    output_description = "DiagnosticsReady"
    idempotency = "Diagnostics are pure JSON-ready projections of the current result."

    def apply(self, input_obj, state: State) -> Iterable[FunctionResult]:
        if isinstance(input_obj, HierarchyFinished):
            if (
                input_obj.case_id not in state.hierarchy_reports
                or (
                    not input_obj.observed_only
                    and input_obj.case_id not in state.solve_attempted
                )
            ):
                yield FunctionResult(
                    output=SetupFailed(input_obj.case_id, "diagnostics_missing_hierarchy_result"),
                    new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                    label="diagnostics_missing_hierarchy",
                )
                return
            yield FunctionResult(
                output=DiagnosticsReady(input_obj.case_id),
                new_state=_diagnostics_state(state, input_obj.case_id),
                label=(
                    "diagnostics_after_hierarchy_evaluate"
                    if input_obj.observed_only
                    else "diagnostics_after_hierarchy_compare"
                    if input_obj.compare_mode
                    else "diagnostics_after_hierarchy_run"
                ),
            )
            return
        if isinstance(input_obj, HierarchyInspected):
            if input_obj.case_id not in state.hierarchy_descriptions:
                yield FunctionResult(
                    output=SetupFailed(input_obj.case_id, "diagnostics_missing_hierarchy_describe"),
                    new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                    label="diagnostics_missing_hierarchy_describe",
                )
                return
            yield FunctionResult(
                output=DiagnosticsReady(input_obj.case_id),
                new_state=_diagnostics_state(state, input_obj.case_id),
                label="diagnostics_after_hierarchy_describe",
            )
            return
        case_id = getattr(input_obj, "case_id", "<unknown>")
        if case_id not in state.failures:
            yield FunctionResult(
                output=SetupFailed(case_id, "diagnostics_input_unsupported"),
                new_state=replace(state, failures=state.failures + (case_id,)),
                label="diagnostics_input_unsupported",
            )


def _diagnostics_state(state: State, case_id: str) -> State:
    assumption_cases = (
        set(state.assumptions_seen)
        | set(state.parameter_assumptions_applied)
        | set(state.variable_assumptions_fixed)
        | set(state.assumption_overrides_warned)
        | set(state.proposed_assumptions_not_applied)
        | set(state.rejected_assumptions_not_applied)
    )
    return replace(
        state,
        diagnostics_emitted=state.diagnostics_emitted + (case_id,),
        assumptions_reported=(
            state.assumptions_reported + (case_id,)
            if case_id in assumption_cases
            else state.assumptions_reported
        ),
    )


def terminal_predicate(current_output, state: State, trace) -> bool:
    del trace
    return isinstance(current_output, (DiagnosticsReady, SetupFailed))


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


def audit_pass_and_failure_are_disjoint(state: State, trace) -> InvariantResult:
    del trace
    bad = tuple(sorted(set(state.audit_passes) & set(state.audit_failures)))
    if bad:
        return InvariantResult.fail(f"audit pass and failure both recorded: {bad!r}")
    return InvariantResult.pass_()


def post_checks_never_block_valid_solver_selection(state: State, trace) -> InvariantResult:
    del trace
    bad = tuple(
        sorted(set(state.post_checks_diagnostic_only) - set(state.residuals_normalized))
    )
    if bad:
        return InvariantResult.fail(
            f"post_check residuals recorded without normalized diagnostics: {bad!r}"
        )
    if state.post_checks_in_solver:
        return InvariantResult.fail(f"post_check residuals selected for the solver: {state.post_checks_in_solver!r}")
    return InvariantResult.pass_()


def observed_evaluation_does_not_solve(state: State, trace) -> InvariantResult:
    del trace
    bad = tuple(sorted(set(state.observed_without_solver) & set(state.solve_attempted)))
    if bad:
        return InvariantResult.fail(f"observed evaluation modified by solver: {bad!r}")
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


def hierarchy_run_requires_solve(state: State, trace) -> InvariantResult:
    del trace
    hierarchy_reports_that_must_solve = set(state.hierarchy_reports) - set(
        state.observed_without_solver
    )
    bad = tuple(sorted(hierarchy_reports_that_must_solve - set(state.solve_attempted)))
    if bad:
        return InvariantResult.fail(f"hierarchy report missing solve attempt: {bad!r}")
    return InvariantResult.pass_()


def hierarchy_describe_does_not_solve(state: State, trace) -> InvariantResult:
    del trace
    bad = tuple(sorted(set(state.hierarchy_descriptions) & set(state.solve_attempted)))
    if bad:
        return InvariantResult.fail(f"hierarchy describe unexpectedly solved: {bad!r}")
    return InvariantResult.pass_()


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


INVARIANTS = (
    Invariant("parent_fails_with_child", "A failed child makes every containing parent fail.", parent_fails_with_child),
    Invariant("derived_relations_are_not_checks", "A producing relation is never an independent check.", derived_relations_are_not_checks),
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
        name="diagnostics_after_solver_or_failure",
        description="Diagnostics are emitted only after solve attempt or setup failure.",
        predicate=diagnostics_after_solver_or_failure,
    ),
    Invariant(
        name="audit_pass_and_failure_are_disjoint",
        description="Audit pass/fail status is computed separately and never overlaps.",
        predicate=audit_pass_and_failure_are_disjoint,
    ),
    Invariant(
        name="post_checks_never_block_valid_solver_selection",
        description="Diagnostic-only residuals remain normalized diagnostics, not solver terms.",
        predicate=post_checks_never_block_valid_solver_selection,
    ),
    Invariant(
        name="observed_evaluation_does_not_solve",
        description="Evaluate mode substitutes observed values without running the solver.",
        predicate=observed_evaluation_does_not_solve,
    ),
    Invariant(
        name="comparison_requires_reference_and_observed",
        description="Compare mode includes both a reference solve and observed evaluation.",
        predicate=comparison_requires_reference_and_observed,
    ),
    Invariant(
        name="hierarchy_run_requires_solve",
        description="Hierarchy run solves before reporting block diagnostics.",
        predicate=hierarchy_run_requires_solve,
    ),
    Invariant(
        name="hierarchy_describe_does_not_solve",
        description="Hierarchy describe validates structure without a solve attempt.",
        predicate=hierarchy_describe_does_not_solve,
    ),
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
    Invariant(
        name="no_residual_from_unobserved_guess",
        description="No residual is evaluated from an unobserved variable's initial guess.",
        predicate=no_residual_from_unobserved_guess,
    ),
    Invariant(
        name="unobserved_variables_stay_listed",
        description="A partial snapshot lists missing or explicitly derived variables without silent fills.",
        predicate=unobserved_variables_stay_listed,
    ),
    Invariant("coarse_failure_with_passing_children_is_inconsistent", "Checked coarse failure with passing children is explicitly inconsistent.", coarse_failure_with_passing_children_is_inconsistent),
    Invariant("planned_template_is_reported_not_executed", "An unbuilt refinement is reported as planned and never loaded or executed.", planned_template_is_reported_not_executed),
    Invariant("tree_view_shows_every_block_verdict", "The tree view prints every block with the verdict of the report; a block without checked residuals is never PASS.", tree_view_shows_every_block_verdict),
)


EXTERNAL_INPUTS = (
    AuditInput("clean", True, True, True, True, True, True),
    AuditInput("converged_bad_audit", True, True, True, True, True, False),
    AuditInput("bad_bounds", True, False, True, True, True, True),
    AuditInput("unknown_ref", True, True, False, True, True, True),
    AuditInput("raw_residual", True, True, True, False, True, True),
    AuditInput("post_check_diagnostic_only", True, True, True, True, True, True, True, False),
    AuditInput("post_check_bad_selection", True, True, True, True, True, True, True, True),
    AuditInput("evaluate_clean", True, True, True, True, True, True, False, False, "hierarchy_evaluate", True),
    AuditInput("evaluate_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_evaluate", True),
    AuditInput("evaluate_missing_observed", True, True, True, True, True, True, False, False, "hierarchy_evaluate", False),
    AuditInput("compare_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_compare", True),
    AuditInput("hierarchy_clean", True, True, True, True, True, True, False, False, "hierarchy_run", True),
    AuditInput("hierarchy_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_run", True),
    AuditInput("hierarchy_evaluate_clean", True, True, True, True, True, True, False, False, "hierarchy_evaluate", True),
    AuditInput("hierarchy_evaluate_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_evaluate", True),
    AuditInput("hierarchy_evaluate_missing_observed", True, True, True, True, True, True, False, False, "hierarchy_evaluate", False),
    AuditInput("hierarchy_evaluate_derived_bad_audit", True, True, True, True, True, False, mode="hierarchy_evaluate", observed_values_complete=False),
    AuditInput("hierarchy_evaluate_derived_child_bad_audit", True, True, True, True, True, False, mode="hierarchy_evaluate", observed_values_complete=False),
    AuditInput("hierarchy_evaluate_partial_unresolved", True, True, True, True, True, True, mode="hierarchy_evaluate", observed_values_complete=False),
    AuditInput("hierarchy_evaluate_partial_snapshot", True, True, True, True, True, True, False, False, "hierarchy_evaluate", False),
    AuditInput("hierarchy_evaluate_zero_product", True, True, True, True, True, True, mode="hierarchy_evaluate", observed_values_complete=False, unobserved_zero_product=True),
    AuditInput("hierarchy_compare_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_compare", True),
    AuditInput("hierarchy_describe", True, True, True, True, True, True, False, False, "hierarchy_describe", True),
    AuditInput("assumption_parameter_fill", True, True, True, True, True, True, has_assumptions=True, parameter_assumption=True),
    AuditInput("assumption_variable_boundary", True, True, True, True, True, True, has_assumptions=True, variable_assumption=True),
    AuditInput("assumption_parameter_override", True, True, True, True, True, True, has_assumptions=True, parameter_assumption=True, assumption_override=True),
    AuditInput("assumption_proposed", True, True, True, True, True, True, has_assumptions=True, proposed_assumption=True),
    AuditInput("assumption_rejected", True, True, True, True, True, True, has_assumptions=True, rejected_assumption=True),
    AuditInput("assumption_context", True, True, True, True, True, True, has_assumptions=True),
    AuditInput("assumption_free_variable", True, True, True, True, True, True, has_assumptions=True, assumption_as_free_variable=True),
    AuditInput("no_converge", True, True, True, True, False, True),
    AuditInput("bad_schema", False, True, True, True, True, True),
    AuditInput("growth_coarse_bad_audit", True, True, True, True, True, False, mode="hierarchy_evaluate"),
    AuditInput("growth_planned_bad_audit", True, True, True, True, True, False, mode="hierarchy_evaluate"),
    AuditInput("hierarchy_evaluate_partial_tree_view_bad_audit", True, True, True, True, True, False, mode="hierarchy_evaluate", observed_values_complete=False),
)

MAX_SEQUENCE_LENGTH = 1


def initial_state() -> State:
    return State()


def build_workflow() -> Workflow:
    return Workflow(
        (
            ValidateSystem(),
            BuildRegistry(),
            AssembleResiduals(),
            ExecuteMode(),
            GenerateDiagnostics(),
        ),
        name="physicsguard_core_lifecycle",
    )


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "AuditInput",
    "State",
    "build_workflow",
    "initial_state",
    "terminal_predicate",
]


# Contract: what this model is about in the real code, its known-bad variants, and the replay on that code.

from contextlib import contextmanager  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402

from flowguard.explorer import Explorer  # noqa: E402

MODEL_ID = "core"
PARENT = "system"
ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTED_BY = {
    "ValidateSystem": "src/physicsguard/io/yaml_loader.py:load_system_spec",
    "AssembleResiduals": "src/physicsguard/core/residual.py:ResidualBuilder",
    "ExecuteMode.solve": "src/physicsguard/core/solver.py:BoundedSolver.solve",
    "ExecuteMode.evaluate": "src/physicsguard/core/hierarchy.py:HierarchicalAuditRunner.evaluate_observed",
    "ExecuteMode.hierarchy": "src/physicsguard/core/hierarchy.py:HierarchicalAuditRunner",
    "ExecuteMode.describe": "src/physicsguard/core/hierarchy.py:describe_hierarchy",
    "ExecuteMode.growth": "src/physicsguard/core/hierarchy.py:RefinementPlanner.recommended_refinements",
    "ExecuteMode.tree_view": "src/physicsguard/core/tree_view.py:render_tree_view",
    "GenerateDiagnostics": "src/physicsguard/core/diagnostics.py:DiagnosticReporter.generate",
}
TESTED_BY = {
    "tree_view_shows_every_block_verdict": [
        "tests/test_hierarchy_cli.py:test_evaluate_prints_the_tree_with_verdicts",
    ],
    "coarse_failure_with_passing_children_is_inconsistent": [
        "tests/test_hierarchy_scoring.py:test_refinement_consistency_uses_own_checked_coarse_relations",
    ],
    "planned_template_is_reported_not_executed": [
        "tests/test_hierarchy_refinement.py:test_unbuilt_template_is_planned",
    ],
    "no_solve_without_valid_registry": [
        "tests/test_residual_builder.py:test_duplicate_fully_qualified_variables_fail",
        "tests/test_solver.py:test_bounds_are_respected",
    ],
    "no_solve_without_normalized_residuals": [
        "tests/test_residual_builder.py:test_residual_vector_returns_normalized_values",
    ],
    "diagnostics_after_solver_or_failure": [
        "tests/test_diagnostics.py:test_warnings_generated_for_solver_failure",
        "tests/test_solver.py:test_solver_result_includes_diagnostics_ready_fields",
    ],
    "post_checks_never_block_valid_solver_selection": [
        "tests/test_solver.py:test_range_check_post_check_does_not_pull_solution",
        "tests/test_residual_builder.py:test_post_check_residuals_are_not_in_solver_vector",
    ],
    "comparison_requires_reference_and_observed": [
        "tests/test_hierarchy_runner.py:test_compare_to_reference_returns_reference_and_observed_variables",
    ],
    "hierarchy_run_requires_solve": [
        "tests/test_hierarchy_runner.py:test_clean_hierarchical_example_audit_pass_true",
        "tests/test_hierarchy_runner.py:test_conflict_hierarchical_example_identifies_top_block_and_refinement",
    ],
    "hierarchy_describe_does_not_solve": [
        "tests/test_hierarchy_spec.py:test_refines_requires_a_parent_owned_component_and_describe_exposes_it",
        "tests/test_hierarchy_cli.py:test_describe_json_keeps_every_inspect_field",
    ],
    "assumptions_are_reported_in_diagnostics": [
        "tests/test_assumption_diagnostics.py:test_normal_diagnostic_json_includes_assumptions_section",
        "tests/test_assumption_diagnostics.py:test_proposed_assumption_warning_appears_and_not_applied",
    ],
    "parent_fails_with_child": [
        "tests/test_hierarchy_scoring.py:test_real_heater_failure_propagates_through_two_ancestors_without_changing_own_scores",
        "tests/test_hierarchy_runner.py:test_hierarchy_evaluate_observed_fault_identifies_block_and_recommends_refinement",
    ],
    "derived_relations_are_not_checks": [
        "tests/test_heated_tank_example.py:test_measured_tank_derivations_are_reported_without_solving",
        "tests/test_hierarchy_runner.py:test_repeated_connection_names_keep_distinct_producing_and_checked_occurrences",
    ],
    "no_residual_from_unobserved_guess": [
        "tests/test_hierarchy_runner.py:test_partial_snapshot_does_not_invent_a_zero_product_residual",
        "tests/test_hierarchy_runner.py:test_partial_snapshot_skips_a_range_check_with_a_flat_local_region",
        "tests/test_hierarchy_runner.py:test_unclassified_custom_residual_is_not_licensed_by_finite_probes",
        "tests/test_hierarchy_runner.py:test_partial_sum_tracks_external_reads_when_it_declares_no_variables",
    ],
    "audit_pass_and_failure_are_disjoint": [
        "tests/test_diagnostics.py:test_report_distinguishes_optimization_success_from_audit_pass",
    ],
    "observed_evaluation_does_not_solve": [
        "tests/test_hierarchy_runner.py:test_evaluate_observed_does_not_call_solver",
        "tests/test_hierarchy_runner.py:test_hierarchy_evaluate_observed_clean_does_not_solve_and_passes",
    ],
    "variable_assumptions_are_fixed_residuals": [
        "tests/test_assumption_residuals.py:test_variable_assumption_creates_active_assumption_residual",
    ],
    "assumption_overrides_are_warned": [
        "tests/test_assumption_manager.py:test_explicit_parameter_override_requires_allow_override_and_warns",
    ],
    "unobserved_variables_stay_listed": [
        "tests/test_hierarchy_runner.py:test_hierarchy_evaluate_skips_residuals_that_need_unobserved_variables",
        "tests/test_hierarchy_cli.py:test_hierarchy_evaluate_reports_a_partial_snapshot",
    ],
}
REQUIRED_LABELS = (
    "schema_valid",
    "registry_ready",
    "residuals_ready",
    "optimizer_converged_audit_failed",
    "hierarchy_index_ready",
    "hierarchy_run_solved_and_reported",
    "hierarchy_observed_evaluated_without_solver",
    "hierarchy_compare_solved_and_evaluated",
    "hierarchy_described_without_solver",
    "diagnostics_after_hierarchy_run",
    "diagnostics_after_hierarchy_evaluate",
    "diagnostics_after_hierarchy_compare",
    "diagnostics_after_hierarchy_describe",
    "parameter_assumption_filled",
    "variable_assumption_boundary_ready",
    "assumption_override_warned",
    "proposed_assumption_not_applied",
    "rejected_assumption_not_applied",
    "assumption_free_variable_failed",
    "schema_failed",
    "registry_failed",
    "residual_reference_failed",
    "residual_normalization_failed",
    "post_check_solver_selection_failed",
    "no_independent_observed_check_failed",
    "unobserved_residuals_skipped",
    "unobserved_values_derived",
    "derived_relations_excluded_from_checks",
    "child_failure_propagated",
    "coarse_failure_consistency_reported",
    "planned_template_reported_not_executed",
    "tree_view_rendered_with_block_verdicts",
)
ASSUMPTION_LABELS = {
    "parameter_fill": "parameter_assumption_filled",
    "parameter_override": "assumption_override_warned",
    "not_applied_proposed": "proposed_assumption_not_applied",
    "not_applied_rejected": "rejected_assumption_not_applied",
    "boundary_residual": "variable_assumption_boundary_ready",
}


def _explorer(workflow: Workflow) -> Explorer:
    return Explorer(
        workflow=workflow,
        initial_states=(initial_state(),),
        external_inputs=EXTERNAL_INPUTS,
        invariants=INVARIANTS,
        max_sequence_length=MAX_SEQUENCE_LENGTH,
        terminal_predicate=terminal_predicate,
        required_labels=REQUIRED_LABELS,
    )


def build_explorer() -> Explorer:
    return _explorer(build_workflow())


class _EvaluateCallsSolver(ExecuteMode):
    """Known bad: observed evaluation also runs the solver."""

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            new = result.new_state
            added = tuple(case for case in new.observed_without_solver if case not in state.observed_without_solver)
            yield replace(result, new_state=replace(new, solve_attempted=new.solve_attempted + added))


class _FailedAuditAlsoPasses(ExecuteMode):
    """Known bad: a failed audit is also recorded as a pass."""

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            new = result.new_state
            added = tuple(case for case in new.audit_failures if case not in state.audit_failures)
            yield replace(result, new_state=replace(new, audit_passes=new.audit_passes + added))


class _SkipsUnobservedSilently(AssembleResiduals):
    """Known bad: a partial snapshot skips residuals without listing the unobserved variables."""

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            if result.label in {"unobserved_residuals_skipped", "unobserved_values_derived"}:
                result = replace(result, new_state=replace(result.new_state, unobserved_listed=state.unobserved_listed))
            yield result


class _EvaluatesFromInitialGuess(AssembleResiduals):
    """Known bad: a zero product hides missing inputs and is evaluated from guesses."""

    writes = AssembleResiduals.writes + ("residuals_from_guess",)

    def apply(self, input_obj, state):
        if input_obj.unobserved_zero_product:
            yield FunctionResult(
                output=ResidualsReady(input_obj.case_id, input_obj.mode, input_obj.observed_values_complete),
                new_state=replace(
                    state,
                    residuals_normalized=state.residuals_normalized + (input_obj.case_id,),
                    residuals_from_guess=state.residuals_from_guess + (input_obj.case_id,),
                ),
                label="unobserved_guesses_evaluated",
            )
            return
        yield from super().apply(input_obj, state)


class _InvalidRegistryReachesSolver(BuildRegistry):
    """Known bad: registry setup failure still attempts the bounded solver."""

    writes = BuildRegistry.writes + ("solve_attempted",)

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            if result.label == "registry_failed":
                result = replace(result, new_state=replace(result.new_state, solve_attempted=state.solve_attempted + (input_obj.case_id,)))
            yield result


class _RawResidualReachesSolver(AssembleResiduals):
    """Known bad: residual normalization failure still attempts the solver."""

    writes = AssembleResiduals.writes + ("solve_attempted",)

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            if result.label == "residual_normalization_failed":
                result = replace(result, new_state=replace(result.new_state, solve_attempted=state.solve_attempted + (input_obj.case_id,)))
            yield result


class _DiagnosticsWithoutResult(GenerateDiagnostics):
    """Known bad: emit diagnostics for a case with no solve, evaluation, or failure."""

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            if input_obj.case_id == "clean":
                result = replace(result, output=DiagnosticsReady("premature_diagnostics"),
                                 new_state=replace(result.new_state, diagnostics_emitted=result.new_state.diagnostics_emitted + ("premature_diagnostics",)))
            yield result


class _PostChecksEnterSolver(AssembleResiduals):
    """Known bad: the invalid post-check selection reaches the solver objective."""

    writes = AssembleResiduals.writes + ("post_checks_in_solver",)

    def apply(self, input_obj, state):
        if input_obj.post_check_enters_solver:
            for result in super().apply(replace(input_obj, post_check_enters_solver=False), state):
                yield replace(result, new_state=replace(result.new_state, post_checks_in_solver=state.post_checks_in_solver + (input_obj.case_id,)))
            return
        yield from super().apply(input_obj, state)


class _ComparisonSkipsReference(ExecuteMode):
    """Known bad: hierarchy comparison omits the reference solve."""

    def apply(self, input_obj, state):
        if input_obj.mode == "hierarchy_compare":
            for result in super().apply(replace(input_obj, mode="hierarchy_evaluate"), state):
                yield replace(
                    result,
                    output=HierarchyFinished(
                        input_obj.case_id,
                        optimization_success=False,
                        audit_pass=result.output.audit_pass,
                        compare_mode=True,
                    ),
                    new_state=replace(
                        result.new_state,
                        comparisons=state.comparisons + (input_obj.case_id,),
                    ),
                )
            return
        yield from super().apply(input_obj, state)


class _HierarchySkipsSolve(ExecuteMode):
    """Known bad: hierarchy run emits its report without solving."""

    def apply(self, input_obj, state):
        if input_obj.mode in {"hierarchy_run"}:
            yield FunctionResult(output=HierarchyFinished(input_obj.case_id, False, True),
                                 new_state=replace(state, hierarchy_reports=state.hierarchy_reports + (input_obj.case_id,)),
                                 label="hierarchy_report_without_solve")
            return
        yield from super().apply(input_obj, state)


class _DescribeSolves(ExecuteMode):
    """Known bad: structural describe assembles residuals and solves a reference."""

    writes = ExecuteMode.writes + ("residuals_normalized",)

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            if input_obj.mode == "hierarchy_describe":
                result = replace(result, new_state=replace(result.new_state,
                                 residuals_normalized=state.residuals_normalized + (input_obj.case_id,),
                                 solve_attempted=state.solve_attempted + (input_obj.case_id,)))
            yield result


class _DiagnosticsDropAssumptions(GenerateDiagnostics):
    """Known bad: diagnostics omit the current case's explicit assumption cards."""

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            yield replace(result, new_state=replace(result.new_state,
                          assumptions_reported=tuple(case for case in result.new_state.assumptions_reported if case != input_obj.case_id)))


class _VariableAssumptionNotFixed(AssembleResiduals):
    """Known bad: variable assumptions become free inputs rather than fixed residuals."""

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            if input_obj.variable_assumption:
                result = replace(result, new_state=replace(result.new_state, variable_assumptions_fixed=state.variable_assumptions_fixed))
            yield result


class _OverrideNotWarned(BuildRegistry):
    """Known bad: an explicit parameter override is applied without its warning."""

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            if input_obj.assumption_override:
                result = replace(result, new_state=replace(result.new_state, assumption_overrides_warned=state.assumption_overrides_warned))
            yield result


class _ParentIgnoresChildren(ExecuteMode):
    """Known bad: retain child failure while reporting only the parent's own check."""

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            if input_obj.case_id in result.new_state.child_failures:
                result = replace(result, new_state=replace(result.new_state,
                                 parent_failures=tuple(case for case in result.new_state.parent_failures if case != input_obj.case_id)))
            yield result


class _CountsDerivationsAsChecks(ExecuteMode):
    """Known bad: include the actual producing relation among checked evidence."""

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            if input_obj.case_id in state.derivation_cases:
                producing = tuple(item for item in state.producing_relations if item.startswith(input_obj.case_id + ":"))
                result = replace(result, new_state=replace(result.new_state,
                                 checked_relations=result.new_state.checked_relations + producing))
            yield result


class _CoarseFailureReportedConsistent(ExecuteMode):
    def apply(self, input_obj: ResidualsReady, state: State) -> Iterable[FunctionResult]:
        for result in super().apply(input_obj, state):
            if input_obj.case_id == "growth_coarse_bad_audit":
                yield replace(result, new_state=replace(result.new_state, coarse_refinement_reported=state.coarse_refinement_reported))
            else:
                yield result


class _PlannedTargetLoaded(ExecuteMode):
    def apply(self, input_obj: ResidualsReady, state: State) -> Iterable[FunctionResult]:
        for result in super().apply(input_obj, state):
            if input_obj.case_id == "growth_planned_bad_audit":
                yield replace(result, new_state=replace(result.new_state, refinement_templates_loaded=state.refinement_templates_loaded + (input_obj.case_id,)))
            else:
                yield result


class _TreeViewHidesAFailingBlock(ExecuteMode):
    """Known bad: the tree view prints a failing block as PASS."""

    def apply(self, input_obj: ResidualsReady, state: State) -> Iterable[FunctionResult]:
        for result in super().apply(input_obj, state):
            rows = tuple(row.replace(":FAIL", ":PASS") for row in result.new_state.tree_view_rows)
            yield replace(result, new_state=replace(result.new_state, tree_view_rows=rows))


def broken_variants() -> dict[str, Explorer]:
    """Known-bad variants; each must violate an invariant of the design."""

    variants = {
        "parent_ignores_children": _ParentIgnoresChildren(),
        "counts_derivations_as_checks": _CountsDerivationsAsChecks(),
        "evaluate_calls_solver": _EvaluateCallsSolver(),
        "failed_audit_also_passes": _FailedAuditAlsoPasses(),
        "partial_snapshot_hides_unobserved": _SkipsUnobservedSilently(),
        "evaluates_from_initial_guess": _EvaluatesFromInitialGuess(),
        "invalid_registry_reaches_solver": _InvalidRegistryReachesSolver(),
        "raw_residual_reaches_solver": _RawResidualReachesSolver(),
        "diagnostics_without_result": _DiagnosticsWithoutResult(),
        "post_checks_enter_solver": _PostChecksEnterSolver(),
        "comparison_skips_reference": _ComparisonSkipsReference(),
        "hierarchy_skips_solve": _HierarchySkipsSolve(),
        "describe_solves": _DescribeSolves(),
        "diagnostics_drop_assumptions": _DiagnosticsDropAssumptions(),
        "variable_assumption_not_fixed": _VariableAssumptionNotFixed(),
        "override_not_warned": _OverrideNotWarned(),
        "coarse_failure_reported_consistent": _CoarseFailureReportedConsistent(),
        "planned_target_loaded": _PlannedTargetLoaded(),
        "tree_view_hides_a_failing_block": _TreeViewHidesAFailingBlock(),
    }
    return {
        name: _explorer(Workflow(
            tuple(broken if isinstance(broken, type(block)) else block for block in build_workflow().blocks),
            name=name,
        ))
        for name, broken in variants.items()
    }


@contextmanager
def _solver_counted():
    from physicsguard.core.solver import BoundedSolver

    calls = []
    original = BoundedSolver.solve

    def counting(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)

    BoundedSolver.solve = counting
    try:
        yield calls
    finally:
        BoundedSolver.solve = original


def _hierarchy(mode: str, audit_file: str, observed_file: str | None = None, keep: int | None = None):
    from physicsguard.core.hierarchy import HierarchicalAuditRunner, describe_hierarchy
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    spec = load_hierarchical_audit_spec(ROOT / audit_file)
    with _solver_counted() as calls:
        if mode == "describe":
            describe_hierarchy(spec)
            return ("hierarchy_described_without_solver" if not calls else "solver_attempted"), None
        if mode == "run":
            report = HierarchicalAuditRunner(spec).run()
            if not calls:
                return "no_solver_call", report.audit_pass
            label = (
                "optimizer_converged_audit_failed"
                if report.optimization_success and not report.audit_pass
                else "hierarchy_run_solved_and_reported"
            )
            return label, report.audit_pass
        if mode not in {"evaluate", "compare"}:
            raise ValueError(f"unsupported replay mode: {mode}")
        observed = load_observed_values(ROOT / observed_file)
        if keep is not None:
            observed = observed.model_copy(update={"variables": dict(list(observed.variables.items())[:keep])})
        before = observed.model_dump(mode="json")
        try:
            if mode == "compare":
                report = HierarchicalAuditRunner(spec).compare_observed(observed)
                assert observed.model_dump(mode="json") == before
                assert calls, "comparison requires a reference solve"
                assert report.reference_optimization_success
                assert report.reference_audit_pass
                assert report.reference_variables and report.observed_variables
                return "hierarchy_compare_solved_and_evaluated", report.observed_audit_pass
            report = HierarchicalAuditRunner(spec).evaluate_observed(observed, skip_unobserved=True)
        except ValueError as exc:
            assert observed.model_dump(mode="json") == before
            if mode == "evaluate":
                assert not calls, "observed evaluation must not solve"
                if "no residual can be evaluated without them" in str(exc):
                    return "no_independent_observed_check_failed", None
            raise
        assert observed.model_dump(mode="json") == before
    if keep is not None and report.derived_variables:
        assert report.checked_residuals, "derived values alone are not independent checks"
        assert not set(report.metadata["derivation_residual_occurrences"]) & set(report.metadata["checked_residual_occurrences"])
        return ("derived_relations_excluded_from_checks" if not calls else "solver_attempted"), report.audit_pass
    return ("hierarchy_observed_evaluated_without_solver" if not calls else "solver_attempted"), report.audit_pass


def _coolant_declared_fault_run() -> tuple[str, bool]:
    """Replay the existing underread on the same connected tree, without a copy."""
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec

    directory = ROOT / "examples/hierarchical/coolant_loop"
    spec = load_hierarchical_audit_spec(directory / "tree.yaml")
    nominal = load_observed_values(directory / "nominal_observed.yaml")
    before = spec.model_dump(mode="json"), nominal.model_dump(mode="json")
    variant = next(v for v in spec.fault_variants if v.id == "heat_rejection")
    change, = variant.changes
    assert change.scale is not None and not variant.parameters and not variant.rederive
    data = spec.model_dump(mode="json")
    boundary = next(row for row in data["system"]["boundaries"] if row["variable"] == change.variable)
    boundary["value"] = nominal.variables[change.variable].value * change.scale
    with _solver_counted() as calls:
        report = HierarchicalAuditRunner(HierarchicalAuditSpec.model_validate(data), directory).run()
    assert (spec.model_dump(mode="json"), nominal.model_dump(mode="json")) == before
    if not calls:
        return "no_solver_call", report.audit_pass
    return ("optimizer_converged_audit_failed" if report.optimization_success and not report.audit_pass
            else "hierarchy_run_solved_and_reported"), report.audit_pass


def _partial_snapshot(audit_file: str, unobserved: str) -> tuple[str, bool]:
    """The CLI path: a solved snapshot without one variable, evaluated with skip_unobserved."""
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.core.solver import BoundedSolver
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.schema.observation_spec import ObservedValuesSpec

    spec = load_hierarchical_audit_spec(ROOT / audit_file)
    solved = BoundedSolver(ResidualBuilder(spec.system), spec.system.solver).solve().variables
    observed = ObservedValuesSpec(variables={name: {"value": value} for name, value in solved.items() if name != unobserved})
    with _solver_counted() as calls:
        report = HierarchicalAuditRunner(spec).evaluate_observed(observed, skip_unobserved=True)
    listed = unobserved in report.missing_required_variables and bool(report.unchecked_residuals)
    derived = report.derived_variables.get(unobserved)
    if derived and derived["residual_occurrence"] not in report.metadata["checked_residual_occurrences"] and not calls:
        return "unobserved_values_derived", report.audit_pass
    label = "unobserved_residuals_skipped" if listed and not calls else "unobserved_residuals_hidden"
    return label, report.audit_pass


def _derived_tank_snapshot() -> tuple[str, bool]:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    example = ROOT / "examples/hierarchical/heated_tank"
    sparse = example / "sparse_measured_k70.yaml"
    assert sparse.is_file(), f"new sparse snapshot is not implemented: {sparse}"
    spec = load_hierarchical_audit_spec(example / "heated_tank.yaml")
    observed = load_observed_values(sparse)
    before = observed.model_dump(mode="json")
    with _solver_counted() as calls:
        report = HierarchicalAuditRunner(spec).evaluate_observed(observed, skip_unobserved=True)
    used = set(report.metadata["derivation_residual_occurrences"])
    checked = set(report.metadata["checked_residual_occurrences"])
    thermal = any(block.block_id in {"tank", "thermal"} and not block.own_audit_pass for block in report.top_blocks) and not report.audit_pass
    heater = any("heater" in rec.next_template_ids and rec.template_status.get("heater") == "block" for rec in report.recommended_refinements)
    valid = used and checked and not used & checked and report.derived_variables and thermal and heater
    valid = valid and not calls and observed.model_dump(mode="json") == before
    return ("derived_relations_excluded_from_checks" if valid else "derived_relations_misreported"), report.audit_pass


def _unresolved_partial_snapshot() -> tuple[str, bool]:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
    from physicsguard.schema.observation_spec import ObservedValuesSpec

    parameters = {"a": 1., "b": 0., **{f"{axis}_{key}": value for axis in ("x", "y")
                  for key, value in (("lower_bound", -100.), ("upper_bound", 100.), ("initial_guess", 0.), ("scale", 1.))}}
    spec = HierarchicalAuditSpec.model_validate({
        "audit_name": "partial", "system": {"system_name": "partial", "components": [
            {"id": "unseen", "type": "LinearRelationModule", "parameters": parameters},
            {"id": "known", "type": "DummyResidualModule", "parameters": {"target": 0.}},
        ]}, "hierarchy": {"blocks": [{"id": "plant", "level": 0, "components": ["unseen", "known"]}]},
    })
    observed = ObservedValuesSpec(variables={"known.x": {"value": 0.}})
    with _solver_counted() as calls:
        report = HierarchicalAuditRunner(spec).evaluate_observed(observed, skip_unobserved=True)
    listed = report.missing_required_variables == ["unseen.x", "unseen.y"] and bool(report.unchecked_residuals)
    return ("unobserved_residuals_skipped" if listed and not calls else "unobserved_residuals_hidden"), report.audit_pass


def _child_failure_snapshot() -> tuple[str, bool]:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    example = ROOT / "examples/hierarchical/heated_tank"
    observed = load_observed_values(example / "measured_k70.yaml")
    with _solver_counted() as calls:
        report = HierarchicalAuditRunner(load_hierarchical_audit_spec(example / "heated_tank.yaml")).evaluate_observed(observed)
    blocks = {block.block_id: block for block in report.top_blocks}
    own_failures = [block for block in report.top_blocks if not block.own_audit_pass]
    valid = not calls and not report.audit_pass and max(own_failures, key=lambda block: block.level).block_id == "heater"
    valid = valid and all(not blocks[name].audit_pass for name in ("heater", "thermal", "tank"))
    valid = valid and blocks["hydraulics"].audit_pass
    return "child_failure_propagated" if valid else "child_failure_hidden", report.audit_pass


def _zero_product_snapshot() -> tuple[str, bool | None]:
    """An electrical zero product supplies no independently evaluable residual."""
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
    from physicsguard.schema.observation_spec import ObservedValuesSpec

    spec = HierarchicalAuditSpec.model_validate({
        "audit_name": "zero_product",
        "system": {"system_name": "power", "components": [{
            "id": "power", "type": "ElectricalPowerModule",
            "parameters": {"V_initial_guess": 0.0, "current_initial_guess": 0.0, "P_initial_guess": 0.0},
        }]},
        "hierarchy": {"blocks": [{"id": "power_block", "name": "power", "level": 0,
            "components": ["power"], "required_variables": ["power.V_V", "power.current_A", "power.P_W"]}]},
    })
    observed = ObservedValuesSpec(variables={"power.P_W": {"value": 0.0, "unit": "W"}})
    before = observed.model_dump(mode="json")
    with _solver_counted() as calls:
        try:
            report = HierarchicalAuditRunner(spec).evaluate_observed(observed, skip_unobserved=True)
        except ValueError as exc:
            if "no residual can be evaluated without them" not in str(exc):
                raise
            assert not calls, "partial observations must not solve"
            assert observed.model_dump(mode="json") == before
            return "no_independent_observed_check_failed", None
    assert observed.model_dump(mode="json") == before
    return ("solver_attempted" if calls else "residual_evaluated_from_unobserved_guess"), report.audit_pass


def _bad_schema() -> tuple[str, None]:
    from pydantic import ValidationError

    from physicsguard.schema.system_spec import SystemSpec

    try:
        SystemSpec.model_validate({"system_name": "missing_components"})
    except ValidationError:
        return "schema_failed", None
    return "schema_valid", None


def _assumption(relative: str) -> tuple[str, None]:
    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.io.yaml_loader import load_system_spec

    summary = ResidualBuilder(load_system_spec(ROOT / relative)).assumption_summary()
    return ASSUMPTION_LABELS.get(summary.cards[0].application, summary.cards[0].application), None


def _growth_coarse_report() -> tuple[str, bool]:
    """Framework-only two-relation witness; no claim of a physical module."""
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
    from physicsguard.schema.observation_spec import ObservedValuesSpec

    spec = HierarchicalAuditSpec.model_validate({"audit_name": "growth", "system": {"system_name": "growth", "components": [
        {"id": name, "type": "DummyResidualModule", "parameters": {"target": 0.}} for name in ("coarse", "fine")
    ]}, "hierarchy": {"blocks": [
        {"id": "parent", "components": ["coarse"]},
        {"id": "child", "parent_id": "parent", "level": 1, "components": ["fine"], "refines": ["coarse"]},
    ]}})
    observed = ObservedValuesSpec(variables={"coarse.x": {"value": 2.}, "fine.x": {"value": 0.}})
    before = observed.model_dump(mode="json")
    with _solver_counted() as calls:
        report = HierarchicalAuditRunner(spec).evaluate_observed(observed)
    row, = report.refinement_checks
    assert row["coarse_pass"] is False and row["children_pass"] is True and row["consistent"] is False
    assert "refinement_inconsistent: parent" in report.warnings
    assert not calls and observed.model_dump(mode="json") == before
    return "coarse_failure_consistency_reported", report.audit_pass


def _growth_planned_report() -> tuple[str, bool]:
    import builtins
    import io
    import os
    from tempfile import TemporaryDirectory
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
    from physicsguard.schema.observation_spec import ObservedValuesSpec
    from physicsguard.io import hierarchy_loader, yaml_loader, test_file_contract_loader

    target = "future_subsystem"
    spec = HierarchicalAuditSpec.model_validate({"audit_name": "planned", "system": {"system_name": "planned", "components": [
        {"id": "coarse", "type": "DummyResidualModule", "parameters": {"target": 0.}},
    ]}, "hierarchy": {"blocks": [{"id": "root", "components": ["coarse"]}], "refinement_rules": [
        {"id": "grow", "block_id": "root", "score_threshold": 1., "next_template_ids": [target]},
    ]}})
    observed = ObservedValuesSpec(variables={"coarse.x": {"value": 2.}})
    before = observed.model_dump(mode="json")
    attempts = []
    restores = []
    with TemporaryDirectory() as directory:
        base = Path(directory) / "audit"
        base.mkdir()
        candidates = {candidate.resolve() for parent in (base, base.parent) for candidate in (parent / target, parent / (target + ".yaml"))}
        assert len(candidates) == 4 and all(not candidate.exists() for candidate in candidates)
        def is_candidate(value):
            return isinstance(value, (str, bytes, os.PathLike)) and Path(os.fsdecode(value)).resolve() in candidates
        def forbidden_loader(*args, **kwargs):
            attempts.append(("loader", str(args[0]) if args else str(kwargs)))
            raise AssertionError("refinement suggestions must not load a model")
        def guard_method(original):
            def checked(self, *args, **kwargs):
                if is_candidate(self):
                    attempts.append(("path", str(self)))
                    raise AssertionError("planned candidate must not be read or executed")
                return original(self, *args, **kwargs)
            return checked
        def guard_raw_open(original):
            def checked(file, *args, **kwargs):
                if is_candidate(file):
                    attempts.append(("open", str(file)))
                    raise AssertionError("planned candidate must not be opened")
                return original(file, *args, **kwargs)
            return checked
        for owner, name in [(hierarchy_loader, "load_hierarchical_audit_spec"), (yaml_loader, "load_system_spec"), (test_file_contract_loader, "load_yaml_mapping")]:
            restores.append((owner, name, getattr(owner, name)))
            setattr(owner, name, forbidden_loader)
        for name in ("read_text", "read_bytes", "open"):
            restores.append((Path, name, getattr(Path, name)))
            setattr(Path, name, guard_method(getattr(Path, name)))
        for owner in (builtins, io):
            restores.append((owner, "open", owner.open))
            owner.open = guard_raw_open(owner.open)
        try:
            with _solver_counted() as solver_calls:
                report = HierarchicalAuditRunner(spec, base_dir=base).evaluate_observed(observed)
        finally:
            for owner, name, original in reversed(restores):
                setattr(owner, name, original)
    assert not attempts and not solver_calls and observed.model_dump(mode="json") == before
    rec, = report.recommended_refinements
    assert rec.next_template_ids == [target] and rec.template_status == {target: "planned"}
    return "planned_template_reported_not_executed", report.audit_pass


PITCH = "examples/hierarchical/observed_debugging"
REAL_CASES = {
    "growth_coarse_bad_audit": _growth_coarse_report,
    "growth_planned_bad_audit": _growth_planned_report,
    "hierarchy_evaluate_derived_child_bad_audit": _child_failure_snapshot,
    "hierarchy_evaluate_derived_bad_audit": _derived_tank_snapshot,
    "hierarchy_evaluate_partial_unresolved": _unresolved_partial_snapshot,
    "clean": lambda: _hierarchy("run", "examples/dummy_system.yaml"),
    "converged_bad_audit": lambda: _hierarchy("run", "examples/dummy_conflict_system.yaml"),
    "bad_schema": _bad_schema,
    "evaluate_clean": lambda: _hierarchy("evaluate", "examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_clean.yaml"),
    "evaluate_bad_audit": lambda: _hierarchy("evaluate", "examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_conflict.yaml"),
    "evaluate_missing_observed": lambda: _hierarchy("evaluate", "examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_clean.yaml", keep=1),
    "compare_bad_audit": lambda: _hierarchy("compare", "examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_conflict.yaml"),
    "hierarchy_clean": lambda: _hierarchy("run", "examples/hierarchical/coolant_loop/tree.yaml"),
    "hierarchy_bad_audit": lambda: _coolant_declared_fault_run(),
    "hierarchy_evaluate_clean": lambda: _hierarchy("evaluate", f"{PITCH}/pitch_feedback_level_0.yaml", f"{PITCH}/pitch_feedback_observed_clean.yaml"),
    "hierarchy_evaluate_bad_audit": lambda: _hierarchy("evaluate", f"{PITCH}/pitch_feedback_level_0.yaml", f"{PITCH}/pitch_feedback_observed_fault.yaml"),
    "hierarchy_evaluate_missing_observed": lambda: _hierarchy("evaluate", f"{PITCH}/pitch_feedback_level_0.yaml", f"{PITCH}/pitch_feedback_observed_clean.yaml", keep=1),
    "hierarchy_evaluate_zero_product": _zero_product_snapshot,
    "hierarchy_evaluate_partial_snapshot": lambda: _partial_snapshot("examples/hierarchical/coolant_loop/tree.yaml", "cool.Q_stack_heat_W"),
    "hierarchy_describe": lambda: _hierarchy("describe", f"{PITCH}/pitch_feedback_level_0.yaml"),
    "assumption_parameter_fill": lambda: _assumption("examples/assumptions/parameter_assumption.yaml"),
    "assumption_parameter_override": lambda: _assumption("examples/assumptions/parameter_override_warning.yaml"),
    "assumption_proposed": lambda: _assumption("examples/assumptions/proposed_assumption.yaml"),
    "assumption_rejected": lambda: _assumption("examples/assumptions/rejected_assumption.yaml"),
    "assumption_variable_boundary": lambda: _assumption("examples/assumptions/variable_assumption.yaml"),
}


class ReplayReport:
    """Conformance result: how many model cases were replayed on the real code, and the mismatches."""

    def __init__(self, checked: int, mismatches: list[str]) -> None:
        self.checked = checked
        self.mismatches = tuple(mismatches)
        self.ok = not self.mismatches

    def format_text(self, max_examples: int | None = None) -> str:
        lines = [f"conformance: {self.checked - len(self.mismatches)}/{self.checked} model cases match the real code"]
        examples = list(self.mismatches[:max_examples])
        for mismatch in self.mismatches:
            if "real replay raised " in mismatch and mismatch not in examples:
                examples.append(mismatch)
        return "\n".join(lines + [f"  mismatch: {line}" for line in examples])


def conformance() -> ReplayReport:
    """Run each mapped model case through the real code and compare labels and audit_pass."""

    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    workflow = build_workflow()
    inputs = {item.case_id: item for item in EXTERNAL_INPUTS}
    mismatches = []
    for case_id, real in REAL_CASES.items():
        run = workflow.execute(initial_state(), inputs[case_id], terminal_predicate=terminal_predicate)
        model_labels = [step.label for step in run.completed_paths[0].trace.steps]
        try:
            real_label, real_audit_pass = real()
        except (ValueError, AssertionError) as exc:
            mismatches.append(f"{case_id}: real replay raised {type(exc).__name__}: {exc}")
            continue
        if real_label not in model_labels:
            mismatches.append(f"{case_id}: real code gave {real_label!r}, model labels {model_labels}")
        expected_pass = inputs[case_id].residual_within_threshold
        if real_audit_pass is not None and real_audit_pass != expected_pass:
            mismatches.append(f"{case_id}: real audit_pass={real_audit_pass}, model expects {expected_pass}")
    return ReplayReport(len(REAL_CASES), mismatches)


if __name__ == "__main__":
    print(build_explorer().explore().format_text())
    for name, variant in broken_variants().items():
        print(f"known-bad {name}: {'caught' if not variant.explore().ok else 'MISSED'}")
    print(conformance().format_text())


NOT_MODELED = {
    "src/physicsguard/cli.py:build_parser": "Parser declarations are checked against every skill/readme command by test_skill_files_name_only_existing_commands; this contains no audit-state transition.",
    "scripts/extract_test_file_manifest.py:main": "Maintenance wrapper delegates to the native manifest reader covered by contract/CLI tests; no separate physical lifecycle.",
    "scripts/install_physicsguard_skills.py:main": "Skill installation is governed by native transactional installer tests, not the residual-audit workflow.",
    "scripts/portable_model_headers.py:main": "Portable comment-header generation is checked by native header/parse tests; it changes no physical model data.",
    "src/physicsguard/cli.py:main": "Argument parsing, formatting and exit dispatch are covered by native CLI tests; the five flows model their actual behavior owners.",
    "examples/hierarchical/heated_tank/sim_tank.py:main": "External synthetic CSV generator, not a device-audit lifecycle; its imported entrypoint and generated CSV bytes are covered by test_generator_reproduces_committed_csv.",
}
