"""FlowGuard model for the PhysicsGuard AI workflow upgrade.

Purpose: ensure project adoption, model-understanding preflight, signal intake,
module ledger checks, skill sync, and closure gates happen before broad
PhysicsGuard localization claims.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class WorkflowInput:
    case_id: str
    has_project_record: bool
    preflight_complete: bool
    intake_complete: bool
    mappings_reviewed: bool
    module_ledger_current: bool
    skills_synced: bool
    closure_passed: bool


@dataclass(frozen=True)
class ProjectReady:
    case_id: str
    preflight_complete: bool
    intake_complete: bool
    mappings_reviewed: bool
    module_ledger_current: bool
    skills_synced: bool
    closure_passed: bool


@dataclass(frozen=True)
class UnderstandingReady:
    case_id: str
    intake_complete: bool
    mappings_reviewed: bool
    module_ledger_current: bool
    skills_synced: bool
    closure_passed: bool


@dataclass(frozen=True)
class EvidenceReady:
    case_id: str
    module_ledger_current: bool
    skills_synced: bool
    closure_passed: bool


@dataclass(frozen=True)
class RuntimeEvidenceReady:
    case_id: str
    skills_synced: bool
    closure_passed: bool


@dataclass(frozen=True)
class ClosureReady:
    case_id: str
    skills_synced: bool
    closure_passed: bool


@dataclass(frozen=True)
class DoneClaim:
    case_id: str


@dataclass(frozen=True)
class WorkflowBlocked:
    case_id: str
    reason: str


@dataclass(frozen=True)
class State:
    project_adopted: tuple[str, ...] = ()
    preflight_reviewed: tuple[str, ...] = ()
    intake_reviewed: tuple[str, ...] = ()
    mappings_reviewed: tuple[str, ...] = ()
    module_ledger_checked: tuple[str, ...] = ()
    skills_synced: tuple[str, ...] = ()
    closure_passed: tuple[str, ...] = ()
    done_claims: tuple[str, ...] = ()
    blocked: tuple[str, ...] = ()


class AdoptProject:
    name = "AdoptProject"
    reads = ()
    writes = ("project_adopted", "blocked")
    accepted_input_type = WorkflowInput
    input_description = "PhysicsGuard workflow request"
    output_description = "ProjectReady or WorkflowBlocked"
    idempotency = "Project adoption can be rerun and refreshes the same record."

    def apply(self, input_obj: WorkflowInput, state: State) -> Iterable[FunctionResult]:
        if not input_obj.has_project_record:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "missing_project_record"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="project_record_missing",
            )
            return
        yield FunctionResult(
            output=ProjectReady(
                input_obj.case_id,
                input_obj.preflight_complete,
                input_obj.intake_complete,
                input_obj.mappings_reviewed,
                input_obj.module_ledger_current,
                input_obj.skills_synced,
                input_obj.closure_passed,
            ),
            new_state=replace(state, project_adopted=state.project_adopted + (input_obj.case_id,)),
            label="project_adopted",
        )


class ReviewPreflight:
    name = "ReviewPreflight"
    reads = ("project_adopted",)
    writes = ("preflight_reviewed", "blocked")
    accepted_input_type = ProjectReady
    input_description = "ProjectReady"
    output_description = "UnderstandingReady or WorkflowBlocked"
    idempotency = "Preflight review is deterministic for the same artifact."

    def apply(self, input_obj: ProjectReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.case_id not in state.project_adopted:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "project_not_adopted"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="preflight_missing_project",
            )
            return
        if not input_obj.preflight_complete:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "preflight_incomplete"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="preflight_incomplete",
            )
            return
        yield FunctionResult(
            output=UnderstandingReady(
                input_obj.case_id,
                input_obj.intake_complete,
                input_obj.mappings_reviewed,
                input_obj.module_ledger_current,
                input_obj.skills_synced,
                input_obj.closure_passed,
            ),
            new_state=replace(state, preflight_reviewed=state.preflight_reviewed + (input_obj.case_id,)),
            label="preflight_reviewed",
        )


class ReviewIntake:
    name = "ReviewIntake"
    reads = ("preflight_reviewed",)
    writes = ("intake_reviewed", "mappings_reviewed", "blocked")
    accepted_input_type = UnderstandingReady
    input_description = "UnderstandingReady"
    output_description = "EvidenceReady or WorkflowBlocked"
    idempotency = "Signal intake review is deterministic for the same artifact."

    def apply(self, input_obj: UnderstandingReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.case_id not in state.preflight_reviewed:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "preflight_not_reviewed"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="intake_missing_preflight",
            )
            return
        if not input_obj.intake_complete:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "intake_incomplete"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="intake_incomplete",
            )
            return
        if not input_obj.mappings_reviewed:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "signal_mapping_review_required"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="mapping_review_required",
            )
            return
        yield FunctionResult(
            output=EvidenceReady(
                input_obj.case_id,
                input_obj.module_ledger_current,
                input_obj.skills_synced,
                input_obj.closure_passed,
            ),
            new_state=replace(
                state,
                intake_reviewed=state.intake_reviewed + (input_obj.case_id,),
                mappings_reviewed=state.mappings_reviewed + (input_obj.case_id,),
            ),
            label="intake_and_mappings_reviewed",
        )


class CheckModuleLedger:
    name = "CheckModuleLedger"
    reads = ("intake_reviewed", "mappings_reviewed")
    writes = ("module_ledger_checked", "blocked")
    accepted_input_type = EvidenceReady
    input_description = "EvidenceReady"
    output_description = "RuntimeEvidenceReady or WorkflowBlocked"
    idempotency = "Ledger check is a read-only freshness gate."

    def apply(self, input_obj: EvidenceReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.case_id not in state.mappings_reviewed:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "mapping_review_not_done"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="ledger_missing_mapping_review",
            )
            return
        if not input_obj.module_ledger_current:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "module_ledger_stale"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="module_ledger_stale",
            )
            return
        yield FunctionResult(
            output=RuntimeEvidenceReady(
                input_obj.case_id,
                input_obj.skills_synced,
                input_obj.closure_passed,
            ),
            new_state=replace(state, module_ledger_checked=state.module_ledger_checked + (input_obj.case_id,)),
            label="module_ledger_checked",
        )


class SyncSkills:
    name = "SyncSkills"
    reads = ("module_ledger_checked",)
    writes = ("skills_synced", "blocked")
    accepted_input_type = RuntimeEvidenceReady
    input_description = "RuntimeEvidenceReady"
    output_description = "ClosureReady or WorkflowBlocked"
    idempotency = "Skill sync can be rerun and compared by file content."

    def apply(self, input_obj: RuntimeEvidenceReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.case_id not in state.module_ledger_checked:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "ledger_not_checked"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="skill_sync_missing_ledger",
            )
            return
        if not input_obj.skills_synced:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "installed_skills_not_synced"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="skills_not_synced",
            )
            return
        yield FunctionResult(
            output=ClosureReady(input_obj.case_id, input_obj.skills_synced, input_obj.closure_passed),
            new_state=replace(state, skills_synced=state.skills_synced + (input_obj.case_id,)),
            label="skills_synced",
        )


class ReviewClosure:
    name = "ReviewClosure"
    reads = ("skills_synced",)
    writes = ("closure_passed", "done_claims", "blocked")
    accepted_input_type = ClosureReady
    input_description = "ClosureReady"
    output_description = "DoneClaim or WorkflowBlocked"
    idempotency = "Closure review gates the final claim."

    def apply(self, input_obj: ClosureReady, state: State) -> Iterable[FunctionResult]:
        case_has_closure = input_obj.case_id in state.skills_synced
        if not case_has_closure:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "skills_not_synced"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="closure_missing_skill_sync",
            )
            return
        if not input_obj.closure_passed:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "closure_not_passed"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="closure_not_passed",
            )
            return
        yield FunctionResult(
            output=DoneClaim(input_obj.case_id),
            new_state=replace(
                state,
                closure_passed=state.closure_passed + (input_obj.case_id,),
                done_claims=state.done_claims + (input_obj.case_id,),
            ),
            label="closure_passed_done_allowed",
        )


def terminal_predicate(current_output, state: State, trace) -> bool:
    del state, trace
    return isinstance(current_output, (DoneClaim, WorkflowBlocked))


def no_done_without_preflight(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.done_claims) - set(state.preflight_reviewed)
    if missing:
        return InvariantResult.fail(f"done claim without preflight: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_done_without_mapping_review(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.done_claims) - set(state.mappings_reviewed)
    if missing:
        return InvariantResult.fail(f"done claim without mapping review: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_done_without_ledger_and_skill_sync(state: State, trace) -> InvariantResult:
    del trace
    missing_ledger = set(state.done_claims) - set(state.module_ledger_checked)
    missing_skills = set(state.done_claims) - set(state.skills_synced)
    if missing_ledger or missing_skills:
        return InvariantResult.fail(
            f"done claim without ledger/skill sync: ledger={sorted(missing_ledger)!r} skills={sorted(missing_skills)!r}"
        )
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="no_done_without_preflight",
        description="Localization claims require model-understanding preflight.",
        predicate=no_done_without_preflight,
    ),
    Invariant(
        name="no_done_without_mapping_review",
        description="Localization claims require signal mapping review.",
        predicate=no_done_without_mapping_review,
    ),
    Invariant(
        name="no_done_without_ledger_and_skill_sync",
        description="Localization claims require current module ledger and installed skill sync.",
        predicate=no_done_without_ledger_and_skill_sync,
    ),
)


EXTERNAL_INPUTS = (
    WorkflowInput("clean", True, True, True, True, True, True, True),
    WorkflowInput("missing_project", False, True, True, True, True, True, True),
    WorkflowInput("missing_preflight", True, False, True, True, True, True, True),
    WorkflowInput("mapping_review", True, True, True, False, True, True, True),
    WorkflowInput("stale_ledger", True, True, True, True, False, True, True),
    WorkflowInput("skills_unsynced", True, True, True, True, True, False, True),
    WorkflowInput("closure_partial", True, True, True, True, True, True, False),
)

MAX_SEQUENCE_LENGTH = 1


def initial_state() -> State:
    return State()


def build_workflow() -> Workflow:
    return Workflow(
        (
            AdoptProject(),
            ReviewPreflight(),
            ReviewIntake(),
            CheckModuleLedger(),
            SyncSkills(),
            ReviewClosure(),
        ),
        name="physicsguard_ai_workflow_upgrade",
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
