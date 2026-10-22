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
- A partial snapshot in hierarchy evaluate skips only the residuals that need
  unobserved variables and lists those variables; it never passes silently.
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
    unobserved_zero_product: bool = False


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
    unobserved_zero_product: bool = False


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
    unobserved_zero_product: bool = False


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
    unobserved_skipped: tuple[str, ...] = ()
    unobserved_listed: tuple[str, ...] = ()
    residuals_from_guess: tuple[str, ...] = ()
    variable_assumptions_expected: tuple[str, ...] = ()
    assumption_overrides_expected: tuple[str, ...] = ()
    post_checks_in_solver: tuple[str, ...] = ()


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
        if (
            input_obj.mode == "hierarchy_evaluate"
            and not input_obj.observed_values_complete
            and "partial" in input_obj.case_id
        ):
            yield FunctionResult(
                output=ResidualsReady(input_obj.case_id, input_obj.mode, input_obj.observed_values_complete),
                new_state=replace(
                    state,
                    residuals_normalized=state.residuals_normalized + (input_obj.case_id,),
                    unobserved_skipped=state.unobserved_skipped + (input_obj.case_id,),
                    unobserved_listed=state.unobserved_listed + (input_obj.case_id,),
                ),
                label="unobserved_residuals_skipped",
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
    hidden = tuple(sorted(set(state.unobserved_skipped) - set(state.unobserved_listed)))
    if hidden:
        return InvariantResult.fail(f"residuals skipped without listing the unobserved variables: {hidden!r}")
    return InvariantResult.pass_()


def no_residual_from_unobserved_guess(state: State, trace) -> InvariantResult:
    del trace
    if state.residuals_from_guess:
        return InvariantResult.fail(f"residuals evaluated from unobserved initial guesses: {state.residuals_from_guess!r}")
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
    Invariant(
        name="no_residual_from_unobserved_guess",
        description="No residual is evaluated from an unobserved variable's initial guess.",
        predicate=no_residual_from_unobserved_guess,
    ),
    Invariant(
        name="unobserved_variables_stay_listed",
        description="A partial snapshot skips residuals only while listing the unobserved variables.",
        predicate=unobserved_variables_stay_listed,
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
    AuditInput("hierarchy_evaluate_partial_snapshot", True, True, True, True, True, True, False, False, "hierarchy_evaluate", False),
    AuditInput("hierarchy_evaluate_zero_product", True, True, True, True, True, True, mode="hierarchy_evaluate", observed_values_complete=False, unobserved_zero_product=True),
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


# Contract: what this model is about in the real code, its known-bad variants, and the replay on that code.

from contextlib import contextmanager  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402

from flowguard.explorer import Explorer  # noqa: E402

MODEL_ID = "core"
ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTED_BY = {
    "ValidateSystem": "src/physicsguard/io/yaml_loader.py:load_system_spec",
    "AssembleResiduals": "src/physicsguard/core/residual.py:ResidualBuilder",
    "ExecuteMode.solve": "src/physicsguard/core/solver.py:BoundedSolver.solve",
    "ExecuteMode.evaluate": "src/physicsguard/core/evaluator.py:AuditEvaluator.evaluate_observed",
    "ExecuteMode.hierarchy": "src/physicsguard/core/hierarchy.py:HierarchicalAuditRunner",
    "ExecuteMode.inspect": "src/physicsguard/core/hierarchy.py:inspect_hierarchy",
    "GenerateDiagnostics": "src/physicsguard/core/diagnostics.py:DiagnosticReporter.generate",
}
TESTED_BY = {
    "no_residual_from_unobserved_guess": [
        "tests/test_hierarchy_runner.py:test_partial_snapshot_does_not_invent_a_zero_product_residual",
        "tests/test_hierarchy_runner.py:test_partial_snapshot_skips_a_range_check_with_a_flat_local_region",
        "tests/test_hierarchy_runner.py:test_unclassified_custom_residual_is_not_licensed_by_finite_probes",
    ],
    "audit_pass_and_failure_are_disjoint": [
        "tests/test_diagnostics.py:test_report_distinguishes_optimization_success_from_audit_pass",
    ],
    "observed_evaluation_does_not_solve": [
        "tests/test_evaluator.py:test_evaluate_observed_does_not_call_solver",
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
    "solver_attempted",
    "optimizer_converged_audit_failed",
    "diagnostics_after_solver",
    "observed_evaluated_without_solver",
    "diagnostics_after_observed_evaluation",
    "compare_solved_and_evaluated",
    "diagnostics_after_comparison",
    "hierarchy_index_ready",
    "hierarchy_run_solved_and_reported",
    "hierarchy_plan_solved_and_recommended",
    "hierarchy_observed_evaluated_without_solver",
    "hierarchy_compare_solved_and_evaluated",
    "hierarchy_inspected_without_solver",
    "diagnostics_after_hierarchy_run",
    "diagnostics_after_hierarchy_plan",
    "diagnostics_after_hierarchy_evaluate",
    "diagnostics_after_hierarchy_compare",
    "diagnostics_after_hierarchy_inspect",
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
    "missing_observed_values_failed",
    "unobserved_residuals_skipped",
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
            if result.label == "unobserved_residuals_skipped":
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
    """Known bad: compare reports an observation without a reference solve."""

    def apply(self, input_obj, state):
        if input_obj.mode == "compare":
            for result in super().apply(replace(input_obj, mode="evaluate"), state):
                yield replace(result, output=ComparisonFinished(input_obj.case_id, False, False, result.output.audit_pass),
                              new_state=replace(result.new_state, comparisons=state.comparisons + (input_obj.case_id,)))
            return
        yield from super().apply(input_obj, state)


class _HierarchySkipsSolve(ExecuteMode):
    """Known bad: hierarchy run or plan emits its report without solving."""

    def apply(self, input_obj, state):
        if input_obj.mode in {"hierarchy_run", "hierarchy_plan"}:
            yield FunctionResult(output=HierarchyFinished(input_obj.case_id, False, True),
                                 new_state=replace(state, hierarchy_reports=state.hierarchy_reports + (input_obj.case_id,)),
                                 label="hierarchy_report_without_solve")
            return
        yield from super().apply(input_obj, state)


class _InspectSolves(ExecuteMode):
    """Known bad: structural inspect assembles residuals and solves a reference."""

    writes = ExecuteMode.writes + ("residuals_normalized",)

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            if input_obj.mode == "hierarchy_inspect":
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


def broken_variants() -> dict[str, Explorer]:
    """Known-bad variants; each must violate an invariant of the design."""

    variants = {
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
        "inspect_solves": _InspectSolves(),
        "diagnostics_drop_assumptions": _DiagnosticsDropAssumptions(),
        "variable_assumption_not_fixed": _VariableAssumptionNotFixed(),
        "override_not_warned": _OverrideNotWarned(),
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


def _solve(relative: str) -> tuple[str, bool]:
    from physicsguard.core.diagnostics import DiagnosticReporter
    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.core.solver import BoundedSolver
    from physicsguard.io.yaml_loader import load_system_spec

    system = load_system_spec(ROOT / relative)
    builder = ResidualBuilder(system)
    result = BoundedSolver(builder, system.solver).solve()
    report = DiagnosticReporter().generate(system, builder, result)
    if report.optimization_success and not report.audit_pass:
        return "optimizer_converged_audit_failed", report.audit_pass
    return "solver_attempted", report.audit_pass


def _evaluate(system_file: str, observed_file: str, keep: int | None = None) -> tuple[str, bool | None]:
    from physicsguard.core.evaluator import AuditEvaluator
    from physicsguard.io.observation_loader import load_observed_values
    from physicsguard.io.yaml_loader import load_system_spec

    observed = load_observed_values(ROOT / observed_file)
    if keep is not None:
        observed = observed.model_copy(update={"variables": dict(list(observed.variables.items())[:keep])})
    with _solver_counted() as calls:
        try:
            report = AuditEvaluator(load_system_spec(ROOT / system_file)).evaluate_observed(observed)
        except ValueError as exc:
            if "observed values missing required registered variables" in str(exc):
                return "missing_observed_values_failed", None
            raise
    return ("observed_evaluated_without_solver" if not calls else "solver_attempted"), report.audit_pass


def _hierarchy(mode: str, audit_file: str, observed_file: str | None = None, keep: int | None = None):
    from physicsguard.core.hierarchy import HierarchicalAuditRunner, inspect_hierarchy
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    spec = load_hierarchical_audit_spec(ROOT / audit_file)
    with _solver_counted() as calls:
        if mode == "inspect":
            inspect_hierarchy(spec)
            return ("hierarchy_inspected_without_solver" if not calls else "solver_attempted"), None
        if mode == "run":
            report = HierarchicalAuditRunner(spec).run()
            return ("hierarchy_run_solved_and_reported" if calls else "no_solver_call"), report.audit_pass
        observed = load_observed_values(ROOT / observed_file)
        if keep is not None:
            observed = observed.model_copy(update={"variables": dict(list(observed.variables.items())[:keep])})
        try:
            report = HierarchicalAuditRunner(spec).evaluate_observed(observed)
        except ValueError as exc:
            if "observed values missing required registered variables" in str(exc):
                return "missing_observed_values_failed", None
            raise
    return ("hierarchy_observed_evaluated_without_solver" if not calls else "solver_attempted"), report.audit_pass


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
    listed = unobserved in report.missing_required_variables and bool(report.metadata["skipped_residuals"])
    label = "unobserved_residuals_skipped" if listed and not calls else "unobserved_residuals_hidden"
    return label, report.audit_pass


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
            return "missing_observed_values_failed", None
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


PITCH = "examples/hierarchical/observed_debugging"
REAL_CASES = {
    "clean": lambda: _solve("examples/dummy_system.yaml"),
    "converged_bad_audit": lambda: _solve("examples/dummy_conflict_system.yaml"),
    "bad_schema": _bad_schema,
    "evaluate_clean": lambda: _evaluate("examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_clean.yaml"),
    "evaluate_bad_audit": lambda: _evaluate("examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_conflict.yaml"),
    "evaluate_missing_observed": lambda: _evaluate("examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_clean.yaml", keep=1),
    "hierarchy_clean": lambda: _hierarchy("run", "examples/hierarchical/coolant_loop/level_0_cooling_balance.yaml"),
    "hierarchy_bad_audit": lambda: _hierarchy("run", "examples/hierarchical/coolant_loop/conflict_level_0_heat_rejection.yaml"),
    "hierarchy_evaluate_clean": lambda: _hierarchy("evaluate", f"{PITCH}/pitch_feedback_level_0.yaml", f"{PITCH}/pitch_feedback_observed_clean.yaml"),
    "hierarchy_evaluate_bad_audit": lambda: _hierarchy("evaluate", f"{PITCH}/pitch_feedback_level_0.yaml", f"{PITCH}/pitch_feedback_observed_fault.yaml"),
    "hierarchy_evaluate_missing_observed": lambda: _hierarchy("evaluate", f"{PITCH}/pitch_feedback_level_0.yaml", f"{PITCH}/pitch_feedback_observed_clean.yaml", keep=1),
    "hierarchy_evaluate_zero_product": _zero_product_snapshot,
    "hierarchy_evaluate_partial_snapshot": lambda: _partial_snapshot("examples/hierarchical/coolant_loop/level_1_components.yaml", "cool.Q_stack_heat_W"),
    "hierarchy_inspect": lambda: _hierarchy("inspect", f"{PITCH}/pitch_feedback_level_0.yaml"),
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
        return "\n".join(lines + [f"  mismatch: {line}" for line in self.mismatches[:max_examples]])


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
        real_label, real_audit_pass = real()
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
