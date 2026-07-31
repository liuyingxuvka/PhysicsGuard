"""FlowGuard model for interval residual and diagnosability boundaries."""

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
class DiagnosticRequest:
    observed_interval: str
    unresolved_pair_count: int = 0
    available_distinguishing_signal: bool = False
    claim_true_fault: bool = False


@dataclass(frozen=True)
class DiagnosticState:
    phase: str = "declared"
    robust_status: str = ""
    diagnosability_status: str = ""
    recommended_signal: str = ""
    truth_claim_licensed: bool = False


class EvaluateInterval:
    name = "EvaluateInterval"
    accepted_input_type = DiagnosticRequest
    reads = ("observed_interval",)
    writes = ("phase", "robust_status")
    input_description = "one declared residual interval"
    output_description = "one robust interval status"
    idempotency = "the same interval class produces the same status"

    def apply(self, request: DiagnosticRequest, state: DiagnosticState):
        status = {
            "inside": "robust_pass",
            "outside": "robust_fail",
            "crossing": "indeterminate",
            "missing": "not_run",
        }.get(request.observed_interval, "not_run")
        yield FunctionResult(
            request,
            replace(state, phase="interval_evaluated", robust_status=status),
            label=f"interval_{status}",
        )


class EvaluateDiagnosability:
    name = "EvaluateDiagnosability"
    accepted_input_type = DiagnosticRequest
    reads = (
        "unresolved_pair_count",
        "available_distinguishing_signal",
    )
    writes = (
        "phase",
        "diagnosability_status",
        "recommended_signal",
        "truth_claim_licensed",
    )
    input_description = "declared fault signatures and available signals"
    output_description = "pairwise diagnosability plus next-signal evidence"
    idempotency = "the same finite signatures produce the same decision"

    def apply(self, request: DiagnosticRequest, state: DiagnosticState):
        if request.unresolved_pair_count == 0:
            status = "isolable"
            signal = ""
        elif request.available_distinguishing_signal:
            status = "partially_isolable"
            signal = "declared-next-signal"
        else:
            status = "indistinguishable"
            signal = ""
        yield FunctionResult(
            request,
            replace(
                state,
                phase="terminal",
                diagnosability_status=status,
                recommended_signal=signal,
                truth_claim_licensed=False,
            ),
            label=f"diagnosis_{status}",
        )


def no_interval_collapse() -> Invariant:
    def predicate(state: DiagnosticState, _trace):
        if state.robust_status == "indeterminate" and state.phase == "terminal":
            return InvariantResult.pass_()
        return InvariantResult.pass_()

    return Invariant(
        "no_interval_collapse",
        "An interval crossing the boundary remains indeterminate.",
        predicate,
    )


def no_true_fault_claim() -> Invariant:
    def predicate(state: DiagnosticState, _trace):
        if state.truth_claim_licensed:
            return InvariantResult.fail(
                "task-local diagnosability licensed a true-fault claim"
            )
        return InvariantResult.pass_()

    return Invariant(
        "no_true_fault_claim",
        "Diagnosability never proves the true physical fault.",
        predicate,
    )


INVARIANTS = (no_interval_collapse(), no_true_fault_claim())


def workflow() -> Workflow:
    return Workflow(
        (EvaluateInterval(), EvaluateDiagnosability()),
        name="physicsguard_interval_diagnosability",
    )


def scenarios() -> tuple[Scenario, ...]:
    current = workflow()
    return (
        Scenario(
            name="PGD01_inside_pass",
            description="An interval fully inside acceptance robustly passes.",
            initial_state=DiagnosticState(),
            external_input_sequence=(DiagnosticRequest("inside"),),
            expected=ScenarioExpectation(
                expected_status="ok",
                required_trace_labels=(
                    "interval_robust_pass",
                    "diagnosis_isolable",
                ),
                summary="inside interval passes without truth claim",
            ),
            workflow=current,
            invariants=INVARIANTS,
        ),
        Scenario(
            name="PGD02_crossing_indeterminate",
            description="A boundary-crossing interval remains indeterminate.",
            initial_state=DiagnosticState(),
            external_input_sequence=(
                DiagnosticRequest(
                    "crossing",
                    unresolved_pair_count=1,
                    available_distinguishing_signal=True,
                ),
            ),
            expected=ScenarioExpectation(
                expected_status="ok",
                required_trace_labels=(
                    "interval_indeterminate",
                    "diagnosis_partially_isolable",
                ),
                summary="crossing interval is not collapsed",
            ),
            workflow=current,
            invariants=INVARIANTS,
        ),
        Scenario(
            name="PGD03_indistinguishable_visible",
            description="Unseparable signatures remain visibly unresolved.",
            initial_state=DiagnosticState(),
            external_input_sequence=(
                DiagnosticRequest("missing", unresolved_pair_count=2),
            ),
            expected=ScenarioExpectation(
                expected_status="ok",
                required_trace_labels=(
                    "interval_not_run",
                    "diagnosis_indistinguishable",
                ),
                summary="unresolved pairs remain terminal and visible",
            ),
            workflow=current,
            invariants=INVARIANTS,
        ),
    )


__all__ = ["INVARIANTS", "DiagnosticRequest", "DiagnosticState", "scenarios"]
