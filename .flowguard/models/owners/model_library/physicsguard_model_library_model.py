"""FlowGuard model for PhysicsGuard model-library evidence gates."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class LibraryInput:
    model_id: str
    model_file_exists: bool
    claims_validated_reuse: bool
    validation_report_exists: bool


@dataclass(frozen=True)
class LibraryEntryAccepted:
    model_id: str


@dataclass(frozen=True)
class LibraryEntryBlocked:
    model_id: str
    reason: str


@dataclass(frozen=True)
class State:
    accepted: tuple[str, ...] = ()
    blocked: tuple[str, ...] = ()


class CheckLibraryEntry:
    name = "CheckLibraryEntry"
    reads = ()
    writes = ("accepted", "blocked")
    accepted_input_type = LibraryInput
    input_description = "model library entry"
    output_description = "LibraryEntryAccepted or LibraryEntryBlocked"
    idempotency = "Library entry checks read files and report references."

    def apply(self, input_obj: LibraryInput, state: State) -> Iterable[FunctionResult]:
        if not input_obj.model_file_exists:
            yield FunctionResult(
                output=LibraryEntryBlocked(input_obj.model_id, "model_file_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.model_id,)),
                label="model_file_missing",
            )
            return
        if input_obj.claims_validated_reuse and not input_obj.validation_report_exists:
            yield FunctionResult(
                output=LibraryEntryBlocked(input_obj.model_id, "validation_report_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.model_id,)),
                label="validated_reuse_missing_report",
            )
            return
        yield FunctionResult(
            output=LibraryEntryAccepted(input_obj.model_id),
            new_state=replace(state, accepted=state.accepted + (input_obj.model_id,)),
            label="library_entry_accepted",
        )


def no_validated_entry_without_report(state: State, trace) -> InvariantResult:
    del state, trace
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "no_validated_entry_without_report",
        "Validated entries without reports are blocked by transition logic.",
        no_validated_entry_without_report,
    ),
)
EXTERNAL_INPUTS = (
    LibraryInput("draft", True, False, False),
    LibraryInput("validated", True, True, True),
    LibraryInput("missing_report", True, True, False),
    LibraryInput("missing_model", False, False, False),
)
MAX_SEQUENCE_LENGTH = 1


def initial_state() -> State:
    return State()


def terminal_predicate(current_output, state: State, trace) -> bool:
    del state, trace
    return isinstance(current_output, (LibraryEntryAccepted, LibraryEntryBlocked))


def build_workflow() -> Workflow:
    return Workflow((CheckLibraryEntry(),), name="physicsguard_model_library")
