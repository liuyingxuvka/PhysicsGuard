"""FlowGuard model for current PhysicsGuard model-purpose closure.

The bundled skill baseline is deliberately outside the success path.  A real
model reaches success only through a target-local purpose, candidate binding,
good proof, and exhaustive bad proof.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class ModelRequest:
    model_id: str
    current_purpose_contract: bool
    prevented_failure_count: int
    candidate_bound: bool
    good_proof_passed: bool
    proven_bad_failure_count: int


@dataclass(frozen=True)
class PurposeReady:
    model_id: str
    prevented_failure_count: int
    candidate_bound: bool
    good_proof_passed: bool
    proven_bad_failure_count: int


@dataclass(frozen=True)
class CandidateReady:
    model_id: str
    prevented_failure_count: int
    good_proof_passed: bool
    proven_bad_failure_count: int


@dataclass(frozen=True)
class GoodProofReady:
    model_id: str
    prevented_failure_count: int
    proven_bad_failure_count: int


@dataclass(frozen=True)
class ClosureReady:
    model_id: str


@dataclass(frozen=True)
class ModelPurposeClosed:
    model_id: str


@dataclass(frozen=True)
class ModelPurposeBlocked:
    model_id: str
    reason: str


@dataclass(frozen=True)
class State:
    purposes_frozen: tuple[str, ...] = ()
    candidates_bound: tuple[str, ...] = ()
    good_proofs_passed: tuple[str, ...] = ()
    bad_proofs_exhausted: tuple[str, ...] = ()
    closed: tuple[str, ...] = ()
    blocked: tuple[str, ...] = ()


def _blocked(state: State, model_id: str) -> State:
    return replace(state, blocked=state.blocked + (model_id,))


class FreezeCurrentPurpose:
    name = "FreezeCurrentPurpose"
    reads = ()
    writes = ("purposes_frozen", "blocked")
    accepted_input_type = ModelRequest
    input_description = "Concrete PhysicsGuard model request"
    output_description = "PurposeReady or ModelPurposeBlocked"
    idempotency = "The same target-local contract fingerprint freezes the same purpose."

    def apply(self, input_obj: ModelRequest, state: State) -> Iterable[FunctionResult]:
        if not input_obj.current_purpose_contract:
            yield FunctionResult(
                output=ModelPurposeBlocked(input_obj.model_id, "baseline_or_missing_current_purpose"),
                new_state=_blocked(state, input_obj.model_id),
                label="baseline_only_blocked",
            )
            return
        if input_obj.prevented_failure_count < 1:
            yield FunctionResult(
                output=ModelPurposeBlocked(input_obj.model_id, "no_dynamic_prevented_failure"),
                new_state=_blocked(state, input_obj.model_id),
                label="empty_dynamic_failure_blocked",
            )
            return
        yield FunctionResult(
            output=PurposeReady(
                input_obj.model_id,
                input_obj.prevented_failure_count,
                input_obj.candidate_bound,
                input_obj.good_proof_passed,
                input_obj.proven_bad_failure_count,
            ),
            new_state=replace(
                state, purposes_frozen=state.purposes_frozen + (input_obj.model_id,)
            ),
            label="current_purpose_frozen",
        )


class BindCandidate:
    name = "BindCandidate"
    reads = ("purposes_frozen",)
    writes = ("candidates_bound", "blocked")
    accepted_input_type = PurposeReady
    input_description = "Frozen current model purpose"
    output_description = "CandidateReady or ModelPurposeBlocked"
    idempotency = "Candidate binding is deterministic for exact artifact fingerprints."

    def apply(self, input_obj: PurposeReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.model_id not in state.purposes_frozen or not input_obj.candidate_bound:
            yield FunctionResult(
                output=ModelPurposeBlocked(input_obj.model_id, "candidate_not_bound_to_current_purpose"),
                new_state=_blocked(state, input_obj.model_id),
                label="candidate_binding_blocked",
            )
            return
        yield FunctionResult(
            output=CandidateReady(
                input_obj.model_id,
                input_obj.prevented_failure_count,
                input_obj.good_proof_passed,
                input_obj.proven_bad_failure_count,
            ),
            new_state=replace(
                state, candidates_bound=state.candidates_bound + (input_obj.model_id,)
            ),
            label="candidate_bound_after_purpose",
        )


class ProveKnownGood:
    name = "ProveKnownGood"
    reads = ("candidates_bound",)
    writes = ("good_proofs_passed", "blocked")
    accepted_input_type = CandidateReady
    input_description = "Candidate bound to current purpose"
    output_description = "GoodProofReady or ModelPurposeBlocked"
    idempotency = "A good proof is reusable only for unchanged governed inputs."

    def apply(self, input_obj: CandidateReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.model_id not in state.candidates_bound or not input_obj.good_proof_passed:
            yield FunctionResult(
                output=ModelPurposeBlocked(input_obj.model_id, "known_good_not_proven"),
                new_state=_blocked(state, input_obj.model_id),
                label="known_good_blocked",
            )
            return
        yield FunctionResult(
            output=GoodProofReady(
                input_obj.model_id,
                input_obj.prevented_failure_count,
                input_obj.proven_bad_failure_count,
            ),
            new_state=replace(
                state, good_proofs_passed=state.good_proofs_passed + (input_obj.model_id,)
            ),
            label="known_good_passed",
        )


class ProveEveryKnownBad:
    name = "ProveEveryKnownBad"
    reads = ("good_proofs_passed",)
    writes = ("bad_proofs_exhausted", "blocked")
    accepted_input_type = GoodProofReady
    input_description = "Passing current-model good proof"
    output_description = "ClosureReady or ModelPurposeBlocked"
    idempotency = "Bad proof exhaustion is set equality over the frozen failure universe."

    def apply(self, input_obj: GoodProofReady, state: State) -> Iterable[FunctionResult]:
        if (
            input_obj.model_id not in state.good_proofs_passed
            or input_obj.proven_bad_failure_count != input_obj.prevented_failure_count
        ):
            yield FunctionResult(
                output=ModelPurposeBlocked(input_obj.model_id, "dynamic_bad_proofs_not_exhaustive"),
                new_state=_blocked(state, input_obj.model_id),
                label="bad_proof_exhaustion_blocked",
            )
            return
        yield FunctionResult(
            output=ClosureReady(input_obj.model_id),
            new_state=replace(
                state, bad_proofs_exhausted=state.bad_proofs_exhausted + (input_obj.model_id,)
            ),
            label="every_dynamic_bad_proven",
        )


class IssueCurrentModelReceipt:
    name = "IssueCurrentModelReceipt"
    reads = ("purposes_frozen", "candidates_bound", "good_proofs_passed", "bad_proofs_exhausted")
    writes = ("closed", "blocked")
    accepted_input_type = ClosureReady
    input_description = "Exhaustive current model proof closure"
    output_description = "ModelPurposeClosed or ModelPurposeBlocked"
    idempotency = "Receipt identity is derived from exact current proof inputs."

    def apply(self, input_obj: ClosureReady, state: State) -> Iterable[FunctionResult]:
        required = (
            state.purposes_frozen,
            state.candidates_bound,
            state.good_proofs_passed,
            state.bad_proofs_exhausted,
        )
        if any(input_obj.model_id not in rows for rows in required):
            yield FunctionResult(
                output=ModelPurposeBlocked(input_obj.model_id, "closure_chain_incomplete"),
                new_state=_blocked(state, input_obj.model_id),
                label="current_receipt_blocked",
            )
            return
        yield FunctionResult(
            output=ModelPurposeClosed(input_obj.model_id),
            new_state=replace(state, closed=state.closed + (input_obj.model_id,)),
            label="current_model_purpose_closed",
        )


def terminal_predicate(current_output, state: State, trace) -> bool:
    del state, trace
    return isinstance(current_output, (ModelPurposeClosed, ModelPurposeBlocked))


def no_closure_from_baseline_only(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.closed) - set(state.purposes_frozen)
    return (
        InvariantResult.fail(f"closure without current purpose: {sorted(missing)!r}")
        if missing
        else InvariantResult.pass_()
    )


def no_closure_without_exhaustive_bad_proofs(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.closed) - set(state.bad_proofs_exhausted)
    return (
        InvariantResult.fail(f"closure without exhaustive bad proofs: {sorted(missing)!r}")
        if missing
        else InvariantResult.pass_()
    )


INVARIANTS = (
    Invariant(
        name="no_closure_from_baseline_only",
        description="Family baseline regression cannot close a current model.",
        predicate=no_closure_from_baseline_only,
    ),
    Invariant(
        name="no_closure_without_exhaustive_bad_proofs",
        description="Every dynamically declared failure requires a blocking proof.",
        predicate=no_closure_without_exhaustive_bad_proofs,
    ),
)

EXTERNAL_INPUTS = (
    ModelRequest("clean", True, 2, True, True, 2),
    ModelRequest("baseline_only", False, 2, True, True, 2),
    ModelRequest("no_failure", True, 0, True, True, 0),
    ModelRequest("candidate_unbound", True, 2, False, True, 2),
    ModelRequest("good_failed", True, 2, True, False, 2),
    ModelRequest("bad_incomplete", True, 2, True, True, 1),
)

MAX_SEQUENCE_LENGTH = 1


def initial_state() -> State:
    return State()


def build_workflow() -> Workflow:
    return Workflow(
        (
            FreezeCurrentPurpose(),
            BindCandidate(),
            ProveKnownGood(),
            ProveEveryKnownBad(),
            IssueCurrentModelReceipt(),
        ),
        name="physicsguard_dynamic_model_purpose_closure",
    )


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "State",
    "build_workflow",
    "initial_state",
    "terminal_predicate",
]
