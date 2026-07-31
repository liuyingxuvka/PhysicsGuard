"""Executable FlowGuard model for strict task-local model deepening.

The model protects the boundary between an AI-authored explanation and
target-owned evidence.  Gap transitions are derived from native receipts and
closure requires exact candidate-bound regression, independent holdout, and
predictive evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from flowguard import (
    FunctionResult,
    Invariant,
    InvariantResult,
    Scenario,
    ScenarioExpectation,
    Workflow,
)


FLOWGUARD_MODEL_MARKER = "flowguard-executable-model"


@dataclass(frozen=True)
class TaskModelInput:
    all_hypotheses_contradicted: bool = False
    candidate_identity_current: bool = True
    regression_pass: bool = True
    holdout_pass: bool = True
    holdout_independent: bool = True
    predictive_pass: bool = True
    base_gaps: tuple[str, ...] = ()
    candidate_gaps: tuple[str, ...] = ()
    external_input_required: bool = False
    scope_excluded: bool = False
    iteration: int = 1
    max_iterations: int = 3
    caller_claimed_progress: bool = False


@dataclass(frozen=True)
class TaskModelState:
    phase: str = "unplanned"
    purpose_bound: bool = False
    coverage_bound: bool = False
    assumptions_declared: bool = False
    unknowns_declared: bool = False
    native_receipt_bound: bool = False
    model_miss: bool = False
    resolved_gaps: tuple[str, ...] = ()
    persisted_gaps: tuple[str, ...] = ()
    introduced_gaps: tuple[str, ...] = ()
    terminal: str = ""


class FreezeStrictPlan:
    name = "FreezeStrictPlan"
    accepted_input_type = TaskModelInput
    reads = ()
    writes = (
        "phase",
        "purpose_bound",
        "coverage_bound",
        "assumptions_declared",
        "unknowns_declared",
        "native_receipt_bound",
    )
    input_description = "non-trivial task and current target-owned plan inputs"
    output_description = "frozen strict task-local plan"
    idempotency = "the same declared plan inputs freeze to the same authority boundary"

    def apply(self, request: TaskModelInput, state: TaskModelState):
        yield FunctionResult(
            request,
            replace(
                state,
                phase="planned",
                purpose_bound=True,
                coverage_bound=True,
                assumptions_declared=True,
                unknowns_declared=True,
                native_receipt_bound=True,
            ),
            label="plan_strict_bound",
        )


class CompareFrozenPrediction:
    name = "CompareFrozenPrediction"
    accepted_input_type = TaskModelInput
    reads = ("phase",)
    writes = ("phase", "model_miss")
    input_description = "independent observation bound to the frozen plan"
    output_description = "surviving hypothesis set or explicit model miss"
    idempotency = "the same bound observation gives the same hypothesis disposition"

    def apply(self, request: TaskModelInput, state: TaskModelState):
        missed = request.all_hypotheses_contradicted
        yield FunctionResult(
            request,
            replace(state, phase="observed", model_miss=missed),
            label="observation_model_miss" if missed else "observation_has_survivor",
        )


class DeriveCandidateDisposition:
    name = "DeriveCandidateDisposition"
    accepted_input_type = TaskModelInput
    reads = ("phase", "model_miss")
    writes = (
        "phase",
        "resolved_gaps",
        "persisted_gaps",
        "introduced_gaps",
        "terminal",
    )
    input_description = "base/candidate native receipts and exact typed check receipts"
    output_description = "derived gap transition and bounded terminal disposition"
    idempotency = "the same immutable receipts derive the same transition and terminal"

    def apply(self, request: TaskModelInput, state: TaskModelState):
        base = set(request.base_gaps)
        candidate = set(request.candidate_gaps)
        resolved = tuple(sorted(base - candidate))
        persisted = tuple(sorted(base & candidate))
        introduced = tuple(sorted(candidate - base))

        checks_pass = (
            request.regression_pass
            and request.holdout_pass
            and request.holdout_independent
            and request.predictive_pass
        )
        if not request.candidate_identity_current:
            terminal = "blocked_identity"
        elif state.model_miss:
            terminal = "model_miss"
        elif not checks_pass:
            terminal = "candidate_rejected"
        elif not candidate:
            terminal = "model_closed_for_task"
        elif request.external_input_required:
            terminal = "external_input_required"
        elif request.scope_excluded:
            terminal = "scope_excluded"
        elif request.iteration >= request.max_iterations:
            terminal = "iteration_limit"
        elif not resolved:
            terminal = "progress_stalled"
        else:
            terminal = "continue_iteration"

        yield FunctionResult(
            request,
            replace(
                state,
                phase="terminal",
                resolved_gaps=resolved,
                persisted_gaps=persisted,
                introduced_gaps=introduced,
                terminal=terminal,
            ),
            label=f"terminal_{terminal}",
        )


def strict_plan_before_observation() -> Invariant:
    def predicate(state: TaskModelState, _trace):
        if state.phase in {"observed", "terminal"} and not all(
            (
                state.purpose_bound,
                state.coverage_bound,
                state.assumptions_declared,
                state.unknowns_declared,
                state.native_receipt_bound,
            )
        ):
            return InvariantResult.fail("observation escaped the strict frozen plan")
        return InvariantResult.pass_()

    return Invariant(
        "strict_plan_before_observation",
        "Evidence comparison follows a purpose-, coverage-, and receipt-bound plan.",
        predicate,
    )


def closure_requires_zero_native_gaps() -> Invariant:
    def predicate(state: TaskModelState, _trace):
        if state.terminal == "model_closed_for_task" and (
            state.persisted_gaps or state.introduced_gaps or state.model_miss
        ):
            return InvariantResult.fail("closure retained a native gap or model miss")
        return InvariantResult.pass_()

    return Invariant(
        "closure_requires_zero_native_gaps",
        "A task closes only when the candidate native receipt has no open gap.",
        predicate,
    )


def progress_is_receipt_derived() -> Invariant:
    def predicate(state: TaskModelState, _trace):
        if state.terminal == "continue_iteration" and not state.resolved_gaps:
            return InvariantResult.fail("continuation claimed progress without a resolved gap")
        return InvariantResult.pass_()

    return Invariant(
        "progress_is_receipt_derived",
        "Continuation progress requires a base gap absent from the candidate receipt.",
        predicate,
    )


def contradiction_becomes_model_miss() -> Invariant:
    def predicate(state: TaskModelState, _trace):
        if state.model_miss and state.terminal != "model_miss":
            return InvariantResult.fail("zero surviving hypotheses did not remain a model miss")
        return InvariantResult.pass_()

    return Invariant(
        "contradiction_becomes_model_miss",
        "Contradicting every hypothesis cannot select an undeclared physical cause.",
        predicate,
    )


INVARIANTS = (
    strict_plan_before_observation(),
    closure_requires_zero_native_gaps(),
    progress_is_receipt_derived(),
    contradiction_becomes_model_miss(),
)


def workflow() -> Workflow:
    return Workflow(
        (FreezeStrictPlan(), CompareFrozenPrediction(), DeriveCandidateDisposition()),
        name="physicsguard_task_local_model_deepening",
    )


def _scenario(name: str, description: str, request: TaskModelInput, terminal: str) -> Scenario:
    observation_label = (
        "observation_model_miss"
        if request.all_hypotheses_contradicted
        else "observation_has_survivor"
    )
    return Scenario(
        name=name,
        description=description,
        initial_state=TaskModelState(),
        external_input_sequence=(request,),
        expected=ScenarioExpectation(
            expected_status="ok",
            required_trace_labels=(
                "plan_strict_bound",
                observation_label,
                f"terminal_{terminal}",
            ),
            summary=description,
        ),
        workflow=workflow(),
        invariants=INVARIANTS,
    )


def scenarios() -> tuple[Scenario, ...]:
    return (
        _scenario(
            "PGT01_close_only_after_exact_evidence",
            "The exact candidate closes only with zero native gaps and all typed checks.",
            TaskModelInput(base_gaps=("gap:execution",), candidate_gaps=()),
            "model_closed_for_task",
        ),
        _scenario(
            "PGT02_derived_progress_continues",
            "A receipt-derived resolved gap with a remaining gap continues the iteration.",
            TaskModelInput(
                base_gaps=("gap:execution", "gap:mapping"),
                candidate_gaps=("gap:mapping",),
            ),
            "continue_iteration",
        ),
        _scenario(
            "PGT03_self_report_does_not_make_progress",
            "An AI progress claim cannot change an unchanged native gap inventory.",
            TaskModelInput(
                base_gaps=("gap:residual",),
                candidate_gaps=("gap:residual",),
                caller_claimed_progress=True,
            ),
            "progress_stalled",
        ),
        _scenario(
            "PGT04_zero_survivors_is_model_miss",
            "Contradicting every frozen hypothesis exposes a model miss.",
            TaskModelInput(all_hypotheses_contradicted=True),
            "model_miss",
        ),
        _scenario(
            "PGT05_external_gap_is_visible",
            "A native external-input gap remains an explicit non-success terminal.",
            TaskModelInput(
                base_gaps=("gap:uncertainty",),
                candidate_gaps=("gap:uncertainty",),
                external_input_required=True,
            ),
            "external_input_required",
        ),
        _scenario(
            "PGT06_iteration_limit_is_visible",
            "Remaining gaps at the declared bound stop at the iteration limit.",
            TaskModelInput(
                base_gaps=("gap:diagnosability", "gap:predictive"),
                candidate_gaps=("gap:predictive",),
                iteration=3,
                max_iterations=3,
            ),
            "iteration_limit",
        ),
        _scenario(
            "PGT07_wrong_candidate_receipt_blocks",
            "A receipt bound to another candidate cannot authorize this revision.",
            TaskModelInput(candidate_identity_current=False),
            "blocked_identity",
        ),
        _scenario(
            "PGT08_failed_typed_check_rejects",
            "A failed independent holdout check rejects and rolls back the candidate.",
            TaskModelInput(holdout_pass=False),
            "candidate_rejected",
        ),
        _scenario(
            "PGT09_scope_boundary_is_visible",
            "A native scope exclusion remains a bounded non-success result.",
            TaskModelInput(
                base_gaps=("gap:execution",),
                candidate_gaps=("gap:execution",),
                scope_excluded=True,
            ),
            "scope_excluded",
        ),
    )


__all__ = ["INVARIANTS", "TaskModelInput", "TaskModelState", "scenarios"]
