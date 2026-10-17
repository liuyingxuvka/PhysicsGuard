"""FlowGuard model for the PhysicsGuard Core bootstrap.

Risk intent brief:
- Prevent solving models before schema, variable bounds, and residual setup are valid.
- Prevent raw or non-finite residuals from reaching the bounded solver.
- Preserve the architecture boundary that setup failures stop before solving,
  while diagnostics are emitted after valid solve attempts.
- Keep optimizer convergence separate from physical audit pass/fail status.
- Keep diagnostic-only residuals out of the solver objective while preserving them
  for JSON diagnostics.
- Add observed-value evaluation without allowing the solver to modify observed
  values, and compare observed values only after a reference solve.
- Add hierarchical audit run/plan/evaluate/compare/inspect modes without automatic
  refinement execution; hierarchy run and plan solve first, hierarchy evaluate
  substitutes observed values without solving, hierarchy compare solves a
  reference and evaluates observed values, and inspect does not solve.
- Add AssumptionGuard Lite without hidden assumptions: parameter assumptions are
  explicit fills or overrides before module construction; variable assumptions
  become fixed residuals, not free solver variables; every assumption is reported.
- Model only the framework lifecycle, not numerical optimizer details or physics.
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
    mode: str = "solve"
    observed_values_complete: bool = True
    has_assumptions: bool = False
    parameter_assumption: bool = False
    variable_assumption: bool = False
    assumption_override: bool = False
    proposed_assumption: bool = False
    rejected_assumption: bool = False
    assumption_as_free_variable: bool = False


@dataclass(frozen=True)
class Validated:
    case_id: str
    has_post_check_residuals: bool = False
    post_check_enters_solver: bool = False
    mode: str = "solve"
    observed_values_complete: bool = True
    has_assumptions: bool = False
    parameter_assumption: bool = False
    variable_assumption: bool = False
    assumption_override: bool = False
    proposed_assumption: bool = False
    rejected_assumption: bool = False
    assumption_as_free_variable: bool = False


@dataclass(frozen=True)
class RegistryReady:
    case_id: str
    has_post_check_residuals: bool = False
    post_check_enters_solver: bool = False
    mode: str = "solve"
    observed_values_complete: bool = True
    has_assumptions: bool = False
    parameter_assumption: bool = False
    variable_assumption: bool = False
    assumption_override: bool = False
    proposed_assumption: bool = False
    rejected_assumption: bool = False


@dataclass(frozen=True)
class ResidualsReady:
    case_id: str
    mode: str = "solve"
    observed_values_complete: bool = True
    has_assumptions: bool = False
    parameter_assumption: bool = False
    variable_assumption: bool = False
    assumption_override: bool = False
    proposed_assumption: bool = False
    rejected_assumption: bool = False


@dataclass(frozen=True)
class SolverFinished:
    case_id: str
    optimization_success: bool
    audit_pass: bool


@dataclass(frozen=True)
class ObservedEvaluated:
    case_id: str
    audit_pass: bool


@dataclass(frozen=True)
class ComparisonFinished:
    case_id: str
    reference_optimization_success: bool
    reference_audit_pass: bool
    observed_audit_pass: bool


@dataclass(frozen=True)
class HierarchyFinished:
    case_id: str
    optimization_success: bool
    audit_pass: bool
    plan_only: bool = False
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
    hierarchy_plans: tuple[str, ...] = ()
    hierarchy_inspections: tuple[str, ...] = ()
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
            ),
            new_state=replace(state, schema_valid=state.schema_valid + (input_obj.case_id,)),
            label="schema_valid",
        )


class BuildRegistry:
    name = "BuildRegistry"
    reads = ("schema_valid",)
    writes = (
        "registry_valid",
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
            ),
            new_state=replace(
                state,
                registry_valid=state.registry_valid + (input_obj.case_id,),
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
    writes = ("residuals_normalized", "variable_assumptions_fixed", "failures")
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
        if input_obj.mode in {
            "evaluate",
            "compare",
            "hierarchy_evaluate",
            "hierarchy_compare",
        } and not input_obj.observed_values_complete:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "missing_observed_values"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="missing_observed_values_failed",
            )
            return
        if input_obj.mode == "hierarchy_inspect":
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


class ExecuteMode:
    name = "ExecuteMode"
    reads = ("registry_valid", "residuals_normalized")
    writes = (
        "solve_attempted",
        "observed_evaluations",
        "observed_without_solver",
        "comparisons",
        "hierarchy_reports",
        "hierarchy_plans",
        "hierarchy_inspections",
    )
    accepted_input_type = ResidualsReady
    input_description = "ResidualsReady"
    output_description = "SolverFinished, ObservedEvaluated, or ComparisonFinished"
    idempotency = "Mode execution is deterministic for this audit case."

    def apply(self, input_obj: ResidualsReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.case_id not in state.registry_valid:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "solver_setup_invalid"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="solver_setup_failed",
            )
            return
        if input_obj.mode == "hierarchy_inspect":
            yield FunctionResult(
                output=HierarchyInspected(input_obj.case_id),
                new_state=replace(
                    state,
                    hierarchy_inspections=state.hierarchy_inspections
                    + (input_obj.case_id,),
                ),
                label="hierarchy_inspected_without_solver",
            )
            return
        if input_obj.case_id not in state.residuals_normalized:
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "solver_setup_invalid"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="solver_setup_failed",
            )
            return
        if input_obj.mode == "evaluate":
            yield FunctionResult(
                output=ObservedEvaluated(
                    input_obj.case_id,
                    audit_pass="bad_audit" not in input_obj.case_id,
                ),
                new_state=replace(
                    state,
                    observed_evaluations=state.observed_evaluations + (input_obj.case_id,),
                    observed_without_solver=state.observed_without_solver + (input_obj.case_id,),
                    audit_passes=(
                        state.audit_passes + (input_obj.case_id,)
                        if "bad_audit" not in input_obj.case_id
                        else state.audit_passes
                    ),
                    audit_failures=(
                        state.audit_failures + (input_obj.case_id,)
                        if "bad_audit" in input_obj.case_id
                        else state.audit_failures
                    ),
                ),
                label="observed_evaluated_without_solver",
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
                    state,
                    observed_evaluations=state.observed_evaluations + (input_obj.case_id,),
                    observed_without_solver=state.observed_without_solver + (input_obj.case_id,),
                    hierarchy_reports=state.hierarchy_reports + (input_obj.case_id,),
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
                label="hierarchy_observed_evaluated_without_solver",
            )
            return
        if input_obj.mode == "compare":
            yield FunctionResult(
                output=ComparisonFinished(
                    input_obj.case_id,
                    reference_optimization_success="no_converge" not in input_obj.case_id,
                    reference_audit_pass="bad_reference_audit" not in input_obj.case_id,
                    observed_audit_pass="bad_audit" not in input_obj.case_id,
                ),
                new_state=replace(
                    state,
                    solve_attempted=state.solve_attempted + (input_obj.case_id,),
                    observed_evaluations=state.observed_evaluations + (input_obj.case_id,),
                    comparisons=state.comparisons + (input_obj.case_id,),
                    optimization_successes=(
                        state.optimization_successes + (input_obj.case_id,)
                        if "no_converge" not in input_obj.case_id
                        else state.optimization_successes
                    ),
                    audit_passes=(
                        state.audit_passes + (input_obj.case_id,)
                        if "bad_audit" not in input_obj.case_id
                        and "bad_reference_audit" not in input_obj.case_id
                        else state.audit_passes
                    ),
                    audit_failures=(
                        state.audit_failures + (input_obj.case_id,)
                        if "bad_audit" in input_obj.case_id
                        or "bad_reference_audit" in input_obj.case_id
                        else state.audit_failures
                    ),
                ),
                label="compare_solved_and_evaluated",
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
                    state,
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
        if input_obj.mode in {"hierarchy_run", "hierarchy_plan"}:
            audit_pass = "bad_audit" not in input_obj.case_id
            yield FunctionResult(
                output=HierarchyFinished(
                    input_obj.case_id,
                    optimization_success="no_converge" not in input_obj.case_id,
                    audit_pass=audit_pass,
                    plan_only=input_obj.mode == "hierarchy_plan",
                ),
                new_state=replace(
                    state,
                    solve_attempted=state.solve_attempted + (input_obj.case_id,),
                    hierarchy_reports=state.hierarchy_reports + (input_obj.case_id,),
                    hierarchy_plans=(
                        state.hierarchy_plans + (input_obj.case_id,)
                        if input_obj.mode == "hierarchy_plan"
                        else state.hierarchy_plans
                    ),
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
                    "hierarchy_plan_solved_and_recommended"
                    if input_obj.mode == "hierarchy_plan"
                    else "hierarchy_run_solved_and_reported"
                ),
            )
            return
        if input_obj.mode != "solve":
            yield FunctionResult(
                output=SetupFailed(input_obj.case_id, "unsupported_mode"),
                new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                label="unsupported_mode_failed",
            )
            return
        yield FunctionResult(
            output=SolverFinished(
                input_obj.case_id,
                optimization_success="no_converge" not in input_obj.case_id,
                audit_pass="bad_audit" not in input_obj.case_id,
            ),
            new_state=replace(
                state,
                solve_attempted=state.solve_attempted + (input_obj.case_id,),
                optimization_successes=(
                    state.optimization_successes + (input_obj.case_id,)
                    if "no_converge" not in input_obj.case_id
                    else state.optimization_successes
                ),
                audit_passes=(
                    state.audit_passes + (input_obj.case_id,)
                    if "bad_audit" not in input_obj.case_id
                    else state.audit_passes
                ),
                audit_failures=(
                    state.audit_failures + (input_obj.case_id,)
                    if "bad_audit" in input_obj.case_id
                    else state.audit_failures
                ),
            ),
            label=(
                "optimizer_converged_audit_failed"
                if "bad_audit" in input_obj.case_id and "no_converge" not in input_obj.case_id
                else "solver_attempted"
            ),
        )


class GenerateDiagnostics:
    name = "GenerateDiagnostics"
    reads = (
        "solve_attempted",
        "observed_evaluations",
        "comparisons",
        "hierarchy_reports",
        "hierarchy_plans",
        "hierarchy_inspections",
        "parameter_assumptions_applied",
        "variable_assumptions_fixed",
        "assumption_overrides_warned",
        "proposed_assumptions_not_applied",
        "rejected_assumptions_not_applied",
        "failures",
    )
    writes = ("diagnostics_emitted", "assumptions_reported")
    accepted_input_type = object
    input_description = "SolverFinished, ObservedEvaluated, ComparisonFinished, HierarchyFinished, or HierarchyInspected"
    output_description = "DiagnosticsReady"
    idempotency = "Diagnostics are pure JSON-ready projections of the current result."

    def apply(self, input_obj, state: State) -> Iterable[FunctionResult]:
        if isinstance(input_obj, SolverFinished):
            if input_obj.case_id not in state.solve_attempted:
                yield FunctionResult(
                    output=SetupFailed(input_obj.case_id, "diagnostics_missing_solver_result"),
                    new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                    label="diagnostics_missing_solver",
                )
                return
            yield FunctionResult(
                output=DiagnosticsReady(input_obj.case_id),
                new_state=_diagnostics_state(state, input_obj.case_id),
                label="diagnostics_after_solver",
            )
            return
        if isinstance(input_obj, ObservedEvaluated):
            if input_obj.case_id not in state.observed_evaluations:
                yield FunctionResult(
                    output=SetupFailed(input_obj.case_id, "diagnostics_missing_observed_result"),
                    new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                    label="diagnostics_missing_observed",
                )
                return
            yield FunctionResult(
                output=DiagnosticsReady(input_obj.case_id),
                new_state=_diagnostics_state(state, input_obj.case_id),
                label="diagnostics_after_observed_evaluation",
            )
            return
        if isinstance(input_obj, ComparisonFinished):
            if input_obj.case_id not in state.comparisons:
                yield FunctionResult(
                    output=SetupFailed(input_obj.case_id, "diagnostics_missing_comparison_result"),
                    new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                    label="diagnostics_missing_comparison",
                )
                return
            yield FunctionResult(
                output=DiagnosticsReady(input_obj.case_id),
                new_state=_diagnostics_state(state, input_obj.case_id),
                label="diagnostics_after_comparison",
            )
            return
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
                    else
                    "diagnostics_after_hierarchy_plan"
                    if input_obj.plan_only
                    else "diagnostics_after_hierarchy_run"
                ),
            )
            return
        if isinstance(input_obj, HierarchyInspected):
            if input_obj.case_id not in state.hierarchy_inspections:
                yield FunctionResult(
                    output=SetupFailed(input_obj.case_id, "diagnostics_missing_hierarchy_inspect"),
                    new_state=replace(state, failures=state.failures + (input_obj.case_id,)),
                    label="diagnostics_missing_hierarchy_inspect",
                )
                return
            yield FunctionResult(
                output=DiagnosticsReady(input_obj.case_id),
                new_state=_diagnostics_state(state, input_obj.case_id),
                label="diagnostics_after_hierarchy_inspect",
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
        | set(state.hierarchy_inspections)
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


def hierarchy_run_and_plan_require_solve(state: State, trace) -> InvariantResult:
    del trace
    hierarchy_reports_that_must_solve = set(state.hierarchy_reports) - set(
        state.observed_without_solver
    )
    bad = tuple(sorted(hierarchy_reports_that_must_solve - set(state.solve_attempted)))
    if bad:
        return InvariantResult.fail(f"hierarchy report missing solve attempt: {bad!r}")
    bad_plans = tuple(sorted(set(state.hierarchy_plans) - set(state.hierarchy_reports)))
    if bad_plans:
        return InvariantResult.fail(f"hierarchy plan missing hierarchy report: {bad_plans!r}")
    return InvariantResult.pass_()


def hierarchy_inspect_does_not_solve(state: State, trace) -> InvariantResult:
    del trace
    bad = tuple(sorted(set(state.hierarchy_inspections) & set(state.solve_attempted)))
    if bad:
        return InvariantResult.fail(f"hierarchy inspect unexpectedly solved: {bad!r}")
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
    return InvariantResult.pass_()


def assumption_overrides_are_warned(state: State, trace) -> InvariantResult:
    del trace
    bad = tuple(sorted(set(state.assumption_overrides_warned) - set(state.assumptions_seen)))
    if bad:
        return InvariantResult.fail(f"assumption overrides not tied to assumption cards: {bad!r}")
    return InvariantResult.pass_()


INVARIANTS = (
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
        name="hierarchy_run_and_plan_require_solve",
        description="Hierarchy run and plan modes solve before reporting block diagnostics.",
        predicate=hierarchy_run_and_plan_require_solve,
    ),
    Invariant(
        name="hierarchy_inspect_does_not_solve",
        description="Hierarchy inspect validates structure without a solve attempt.",
        predicate=hierarchy_inspect_does_not_solve,
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
)


EXTERNAL_INPUTS = (
    AuditInput("clean", True, True, True, True, True, True),
    AuditInput("converged_bad_audit", True, True, True, True, True, False),
    AuditInput("bad_bounds", True, False, True, True, True, True),
    AuditInput("unknown_ref", True, True, False, True, True, True),
    AuditInput("raw_residual", True, True, True, False, True, True),
    AuditInput("post_check_diagnostic_only", True, True, True, True, True, True, True, False),
    AuditInput("post_check_bad_selection", True, True, True, True, True, True, True, True),
    AuditInput("evaluate_clean", True, True, True, True, True, True, False, False, "evaluate", True),
    AuditInput("evaluate_bad_audit", True, True, True, True, True, False, False, False, "evaluate", True),
    AuditInput("evaluate_missing_observed", True, True, True, True, True, True, False, False, "evaluate", False),
    AuditInput("compare_bad_audit", True, True, True, True, True, False, False, False, "compare", True),
    AuditInput("hierarchy_clean", True, True, True, True, True, True, False, False, "hierarchy_run", True),
    AuditInput("hierarchy_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_run", True),
    AuditInput("hierarchy_plan_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_plan", True),
    AuditInput("hierarchy_evaluate_clean", True, True, True, True, True, True, False, False, "hierarchy_evaluate", True),
    AuditInput("hierarchy_evaluate_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_evaluate", True),
    AuditInput("hierarchy_evaluate_missing_observed", True, True, True, True, True, True, False, False, "hierarchy_evaluate", False),
    AuditInput("hierarchy_compare_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_compare", True),
    AuditInput("hierarchy_inspect", True, True, True, True, True, True, False, False, "hierarchy_inspect", True),
    AuditInput("assumption_parameter_fill", True, True, True, True, True, True, has_assumptions=True, parameter_assumption=True),
    AuditInput("assumption_variable_boundary", True, True, True, True, True, True, has_assumptions=True, variable_assumption=True),
    AuditInput("assumption_parameter_override", True, True, True, True, True, True, has_assumptions=True, parameter_assumption=True, assumption_override=True),
    AuditInput("assumption_proposed", True, True, True, True, True, True, has_assumptions=True, proposed_assumption=True),
    AuditInput("assumption_rejected", True, True, True, True, True, True, has_assumptions=True, rejected_assumption=True),
    AuditInput("assumption_context", True, True, True, True, True, True, has_assumptions=True),
    AuditInput("assumption_free_variable", True, True, True, True, True, True, has_assumptions=True, assumption_as_free_variable=True),
    AuditInput("no_converge", True, True, True, True, False, True),
    AuditInput("bad_schema", False, True, True, True, True, True),
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
