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
    observed_interval: str = ""
    robust_status: str = ""
    diagnosability_status: str = ""
    recommended_signal: str = ""
    truth_claim_licensed: bool = False


class EvaluateInterval:
    name = "EvaluateInterval"
    accepted_input_type = DiagnosticRequest
    reads = ("observed_interval",)
    writes = ("phase", "observed_interval", "robust_status")
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
            replace(
                state,
                phase="interval_evaluated",
                observed_interval=request.observed_interval,
                robust_status=status,
            ),
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
            # Every pair is separated by some signal; the best one is still recommended.
            status = "isolable"
            signal = "declared-next-signal"
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
        if state.observed_interval == "crossing" and state.robust_status != "indeterminate":
            return InvariantResult.fail(
                f"boundary-crossing interval collapsed to {state.robust_status!r}"
            )
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
        Scenario(
            name="PGD04_outside_fail",
            description="An interval wholly outside acceptance robustly fails.",
            initial_state=DiagnosticState(),
            external_input_sequence=(DiagnosticRequest("outside"),),
            expected=ScenarioExpectation(
                expected_status="ok",
                required_trace_labels=(
                    "interval_robust_fail",
                    "diagnosis_isolable",
                ),
                summary="outside interval fails without truth claim",
            ),
            workflow=current,
            invariants=INVARIANTS,
        ),
    )


__all__ = ["INVARIANTS", "DiagnosticRequest", "DiagnosticState", "scenarios", "workflow"]


# Contract: what this model is about in the real code, its known-bad variants, and the replay on that code.

from pathlib import Path  # noqa: E402
import sys  # noqa: E402

from flowguard.explorer import Explorer  # noqa: E402

MODEL_ID = "interval_diagnosability"
ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTED_BY = {
    "EvaluateInterval": "src/physicsguard/core/diagnosability.py:evaluate_interval_residual",
    "EvaluateDiagnosability": "src/physicsguard/core/diagnosability.py:evaluate_diagnosability",
}
TESTED_BY = {
    "no_interval_collapse": [
        "tests/test_diagnosability.py:test_interval_residual_preserves_robust_statuses",
    ],
    "no_true_fault_claim": [
        "tests/test_diagnosability.py:test_diagnosability_reports_pairwise_evidence_and_next_signal",
        "tests/test_diagnosability.py:test_task_model_diagnose_cli_exits_1_when_hypotheses_cannot_be_separated",
    ],
}


def _explorer(flow: Workflow) -> Explorer:
    return Explorer(
        workflow=flow,
        initial_states=(DiagnosticState(),),
        external_inputs=tuple(scenario.external_input_sequence[0] for scenario in scenarios()),
        invariants=INVARIANTS,
        max_sequence_length=1,
        required_labels=tuple(label for scenario in scenarios() for label in scenario.expected.required_trace_labels),
    )


def build_explorer() -> Explorer:
    return _explorer(workflow())


class _CollapsesCrossingInterval(EvaluateInterval):
    """Known bad: a boundary-crossing interval is reported as a robust pass."""

    def apply(self, request, state):
        for result in super().apply(request, state):
            if request.observed_interval == "crossing":
                result = replace(result, new_state=replace(result.new_state, robust_status="robust_pass"))
            yield result


class _LicensesTrueFault(EvaluateDiagnosability):
    """Known bad: task-local diagnosability claims the true physical fault."""

    def apply(self, request, state):
        for result in super().apply(request, state):
            yield replace(result, new_state=replace(result.new_state, truth_claim_licensed=True))


def broken_variants() -> dict[str, Explorer]:
    """Known-bad variants; each must violate an invariant of the design."""

    return {
        "crossing_interval_collapsed": _explorer(
            Workflow((_CollapsesCrossingInterval(), EvaluateDiagnosability()), name="crossing_interval_collapsed")
        ),
        "diagnosability_licenses_true_fault": _explorer(
            Workflow((EvaluateInterval(), _LicensesTrueFault()), name="diagnosability_licenses_true_fault")
        ),
    }


def _interval(observed):
    return {
        "residual_id": "conformance",
        "observed": observed,
        "acceptable": {"lower": -1.0, "upper": 1.0},
        "source_ref": "conformance:interval",
    }


def _signatures(*speeds):
    return {
        "diagnosis_id": "conformance",
        "fault_signatures": [
            {"hypothesis_id": f"h{index}", "predicted_intervals": {"speed": {"lower": low, "upper": low + 1.0}}}
            for index, low in enumerate(speeds)
        ],
        "available_signal_ids": ["speed"],
    }


# Scenario name -> (interval residual input, diagnosability request) for the real code.
REAL_CASES = {
    "PGD01_inside_pass": (_interval({"lower": -0.2, "upper": 0.4}), _signatures(0.0, 5.0)),
    "PGD02_crossing_indeterminate": (_interval({"lower": 0.5, "upper": 1.5}), _signatures(0.0, 0.5, 5.0)),
    "PGD03_indistinguishable_visible": (_interval(None), _signatures(0.0, 0.0)),
    "PGD04_outside_fail": (_interval({"lower": 1.5, "upper": 2.0}), _signatures(0.0, 5.0)),
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
    """Run each scenario's inputs through the real diagnosability code and compare the outcomes."""

    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from physicsguard.core.diagnosability import evaluate_diagnosability, evaluate_interval_residual
    from physicsguard.schema.diagnosability import DiagnosabilityRequestSpec, IntervalResidualSpec

    mismatches = []
    for scenario in scenarios():
        residual, request = REAL_CASES[scenario.name]
        path = workflow().execute(DiagnosticState(), scenario.external_input_sequence[0]).completed_paths[0]
        labels = [step.label for step in path.trace.steps]
        interval = evaluate_interval_residual(IntervalResidualSpec.model_validate(residual))
        diagnosis = evaluate_diagnosability(DiagnosabilityRequestSpec.model_validate(request))
        if f"interval_{interval['status']}" not in labels:
            mismatches.append(f"{scenario.name}: real interval {interval['status']!r}, model labels {labels}")
        if f"diagnosis_{diagnosis['status']}" not in labels:
            mismatches.append(f"{scenario.name}: real diagnosis {diagnosis['status']!r}, model labels {labels}")
        if bool(diagnosis["recommended_next_signal_id"]) != bool(path.state.recommended_signal):
            mismatches.append(
                f"{scenario.name}: real next signal {diagnosis['recommended_next_signal_id']!r}, "
                f"model {path.state.recommended_signal!r}"
            )
    return ReplayReport(len(REAL_CASES), mismatches)


if __name__ == "__main__":
    print(build_explorer().explore().format_text())
    for name, variant in broken_variants().items():
        print(f"known-bad {name}: {'caught' if not variant.explore().ok else 'MISSED'}")
    print(conformance().format_text())
