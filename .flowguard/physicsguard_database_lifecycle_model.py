"""FlowGuard model for explicit PhysicsGuard database lifecycle workflow."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Literal

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


LifecycleIntent = Literal["init", "intake", "admit", "audit", "archive", "handoff"]
ProjectReadiness = Literal["candidate", "placeholder", "active", "validated", "reusable"]


@dataclass(frozen=True)
class DatabaseLifecycleInput:
    case_id: str
    intent: LifecycleIntent
    user_authorized_database: bool
    root_artifacts_present: bool
    policy_present: bool
    catalog_present: bool
    history_present: bool
    raw_data_embedded: bool
    write_apply_requested: bool
    project_candidate_found: bool
    project_level_requirements_met: bool
    project_blocking_gaps: bool
    requested_readiness: ProjectReadiness
    validation_evidence_present: bool
    model_library_evidence_present: bool
    maintenance_audit_ran: bool
    lifecycle_gaps: bool
    history_event_appended: bool
    handoff_rendered: bool
    archive_reason_recorded: bool


@dataclass(frozen=True)
class ExplicitDatabaseContext:
    case_id: str
    intent: LifecycleIntent
    root_artifacts_present: bool
    policy_present: bool
    catalog_present: bool
    history_present: bool
    raw_data_embedded: bool
    write_apply_requested: bool
    project_candidate_found: bool
    project_level_requirements_met: bool
    project_blocking_gaps: bool
    requested_readiness: ProjectReadiness
    validation_evidence_present: bool
    model_library_evidence_present: bool
    maintenance_audit_ran: bool
    lifecycle_gaps: bool
    history_event_appended: bool
    handoff_rendered: bool
    archive_reason_recorded: bool


@dataclass(frozen=True)
class DatabaseRootReady:
    case_id: str
    intent: LifecycleIntent
    write_apply_requested: bool
    project_candidate_found: bool
    project_level_requirements_met: bool
    project_blocking_gaps: bool
    requested_readiness: ProjectReadiness
    validation_evidence_present: bool
    model_library_evidence_present: bool
    maintenance_audit_ran: bool
    lifecycle_gaps: bool
    history_event_appended: bool
    handoff_rendered: bool
    archive_reason_recorded: bool


@dataclass(frozen=True)
class IntakePlanReady:
    case_id: str
    intent: LifecycleIntent
    write_apply_requested: bool
    project_level_requirements_met: bool
    project_blocking_gaps: bool
    requested_readiness: ProjectReadiness
    validation_evidence_present: bool
    model_library_evidence_present: bool
    history_event_appended: bool


@dataclass(frozen=True)
class AdmissionGateReady:
    case_id: str
    intent: LifecycleIntent
    write_apply_requested: bool
    history_event_appended: bool


@dataclass(frozen=True)
class MaintenanceReady:
    case_id: str
    intent: LifecycleIntent
    handoff_rendered: bool


@dataclass(frozen=True)
class ArchiveReady:
    case_id: str
    intent: LifecycleIntent
    write_apply_requested: bool
    history_event_appended: bool


@dataclass(frozen=True)
class HandoffReady:
    case_id: str
    intent: LifecycleIntent


@dataclass(frozen=True)
class LifecycleDryRun:
    case_id: str
    reason: str


@dataclass(frozen=True)
class LifecyclePartial:
    case_id: str
    reason: str


@dataclass(frozen=True)
class LifecycleBlocked:
    case_id: str
    reason: str


@dataclass(frozen=True)
class State:
    explicit_context: tuple[str, ...] = ()
    root_ready: tuple[str, ...] = ()
    intake_planned: tuple[str, ...] = ()
    admission_gate: tuple[str, ...] = ()
    written_with_history: tuple[str, ...] = ()
    maintenance_ready: tuple[str, ...] = ()
    archive_ready: tuple[str, ...] = ()
    handoff_ready: tuple[str, ...] = ()
    dry_run: tuple[str, ...] = ()
    partial: tuple[str, ...] = ()
    blocked: tuple[str, ...] = ()


class RequireExplicitDatabaseIntent:
    name = "RequireExplicitDatabaseIntent"
    reads = ()
    writes = ("explicit_context", "blocked")
    accepted_input_type = DatabaseLifecycleInput
    input_description = "database lifecycle request"
    output_description = "explicit lifecycle context or blocked request"
    idempotency = "Intent review reads the user request and database root only."

    def apply(self, input_obj: DatabaseLifecycleInput, state: State) -> Iterable[FunctionResult]:
        if not input_obj.user_authorized_database:
            yield FunctionResult(
                output=LifecycleBlocked(input_obj.case_id, "database_not_user_authorized"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="implicit_database_blocked",
            )
            return
        yield FunctionResult(
            output=ExplicitDatabaseContext(
                input_obj.case_id,
                input_obj.intent,
                input_obj.root_artifacts_present,
                input_obj.policy_present,
                input_obj.catalog_present,
                input_obj.history_present,
                input_obj.raw_data_embedded,
                input_obj.write_apply_requested,
                input_obj.project_candidate_found,
                input_obj.project_level_requirements_met,
                input_obj.project_blocking_gaps,
                input_obj.requested_readiness,
                input_obj.validation_evidence_present,
                input_obj.model_library_evidence_present,
                input_obj.maintenance_audit_ran,
                input_obj.lifecycle_gaps,
                input_obj.history_event_appended,
                input_obj.handoff_rendered,
                input_obj.archive_reason_recorded,
            ),
            new_state=replace(state, explicit_context=state.explicit_context + (input_obj.case_id,)),
            label="explicit_database_context",
        )


class CheckRootArtifacts:
    name = "CheckRootArtifacts"
    reads = ("explicit_context",)
    writes = ("root_ready", "dry_run", "blocked")
    accepted_input_type = ExplicitDatabaseContext
    input_description = "explicit database context"
    output_description = "database root ready, dry run, or blocked"
    idempotency = "Root artifact review reads database lifecycle files."

    def apply(self, input_obj: ExplicitDatabaseContext, state: State) -> Iterable[FunctionResult]:
        if input_obj.raw_data_embedded:
            yield FunctionResult(
                output=LifecycleBlocked(input_obj.case_id, "raw_data_embedded"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="raw_data_payload_blocked",
            )
            return
        root_complete = input_obj.root_artifacts_present and input_obj.policy_present and input_obj.catalog_present and input_obj.history_present
        if input_obj.intent == "init" and not input_obj.write_apply_requested:
            yield FunctionResult(
                output=LifecycleDryRun(input_obj.case_id, "init_requires_apply_to_write"),
                new_state=replace(state, dry_run=state.dry_run + (input_obj.case_id,)),
                label="init_dry_run_no_write",
            )
            return
        if input_obj.intent != "init" and not root_complete:
            yield FunctionResult(
                output=LifecycleBlocked(input_obj.case_id, "database_root_artifacts_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="root_artifacts_missing_blocked",
            )
            return
        yield FunctionResult(
            output=DatabaseRootReady(
                input_obj.case_id,
                input_obj.intent,
                input_obj.write_apply_requested,
                input_obj.project_candidate_found,
                input_obj.project_level_requirements_met,
                input_obj.project_blocking_gaps,
                input_obj.requested_readiness,
                input_obj.validation_evidence_present,
                input_obj.model_library_evidence_present,
                input_obj.maintenance_audit_ran,
                input_obj.lifecycle_gaps,
                input_obj.history_event_appended,
                input_obj.handoff_rendered,
                input_obj.archive_reason_recorded,
            ),
            new_state=replace(state, root_ready=state.root_ready + (input_obj.case_id,)),
            label="database_root_ready" if input_obj.intent != "init" else "database_initialized_with_apply",
        )


class PlanProjectIntake:
    name = "PlanProjectIntake"
    reads = ("root_ready",)
    writes = ("intake_planned", "partial", "dry_run")
    accepted_input_type = DatabaseRootReady
    input_description = "database root ready"
    output_description = "intake plan or no-op lifecycle path"
    idempotency = "Intake planning is a read-only projection of project evidence."

    def apply(self, input_obj: DatabaseRootReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.intent not in {"intake", "admit"}:
            yield FunctionResult(output=input_obj, new_state=state, label="intake_not_required")
            return
        if not input_obj.project_candidate_found:
            yield FunctionResult(
                output=LifecyclePartial(input_obj.case_id, "no_project_candidate_found"),
                new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                label="no_project_candidate_partial",
            )
            return
        if input_obj.intent == "intake":
            yield FunctionResult(
                output=LifecycleDryRun(input_obj.case_id, "intake_plan_read_only"),
                new_state=replace(
                    state,
                    intake_planned=state.intake_planned + (input_obj.case_id,),
                    dry_run=state.dry_run + (input_obj.case_id,),
                ),
                label="intake_plan_ready",
            )
            return
        yield FunctionResult(
            output=IntakePlanReady(
                input_obj.case_id,
                input_obj.intent,
                input_obj.write_apply_requested,
                input_obj.project_level_requirements_met,
                input_obj.project_blocking_gaps,
                input_obj.requested_readiness,
                input_obj.validation_evidence_present,
                input_obj.model_library_evidence_present,
                input_obj.history_event_appended,
            ),
            new_state=replace(state, intake_planned=state.intake_planned + (input_obj.case_id,)),
            label="intake_plan_for_admission_ready",
        )


class GateProjectAdmission:
    name = "GateProjectAdmission"
    reads = ("intake_planned",)
    writes = ("admission_gate", "dry_run", "blocked")
    accepted_input_type = (IntakePlanReady, DatabaseRootReady)
    input_description = "project intake plan"
    output_description = "admission gate or blocked/dry-run result"
    idempotency = "Admission gate checks project-level PhysicsGuard evidence."

    def apply(self, input_obj, state: State) -> Iterable[FunctionResult]:
        if isinstance(input_obj, DatabaseRootReady):
            yield FunctionResult(output=input_obj, new_state=state, label="admission_not_required")
            return
        if not input_obj.write_apply_requested:
            yield FunctionResult(
                output=LifecycleDryRun(input_obj.case_id, "admission_requires_apply"),
                new_state=replace(state, dry_run=state.dry_run + (input_obj.case_id,)),
                label="admission_dry_run_no_write",
            )
            return
        if input_obj.project_blocking_gaps or not input_obj.project_level_requirements_met:
            if input_obj.requested_readiness in {"active", "validated", "reusable"}:
                yield FunctionResult(
                    output=LifecycleBlocked(input_obj.case_id, "active_admission_missing_project_requirements"),
                    new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                    label="active_admission_requirements_blocked",
                )
                return
        if input_obj.requested_readiness in {"validated", "reusable"} and not input_obj.validation_evidence_present:
            yield FunctionResult(
                output=LifecycleBlocked(input_obj.case_id, "validated_state_without_validation"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="validated_without_validation_blocked",
            )
            return
        if input_obj.requested_readiness == "reusable" and not input_obj.model_library_evidence_present:
            yield FunctionResult(
                output=LifecycleBlocked(input_obj.case_id, "reusable_state_without_model_library"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="reusable_without_model_library_blocked",
            )
            return
        yield FunctionResult(
            output=AdmissionGateReady(input_obj.case_id, input_obj.intent, input_obj.write_apply_requested, input_obj.history_event_appended),
            new_state=replace(state, admission_gate=state.admission_gate + (input_obj.case_id,)),
            label="project_admission_gate_ready",
        )


class CommitMutationHistory:
    name = "CommitMutationHistory"
    reads = ("admission_gate", "root_ready")
    writes = ("written_with_history", "blocked")
    accepted_input_type = (AdmissionGateReady, DatabaseRootReady, ArchiveReady)
    input_description = "write-capable lifecycle transition"
    output_description = "handoff ready or blocked mutation"
    idempotency = "Mutation history requires an appended event for applied writes."

    def apply(self, input_obj, state: State) -> Iterable[FunctionResult]:
        if isinstance(input_obj, DatabaseRootReady) and input_obj.intent not in {"init"}:
            yield FunctionResult(
                output=LifecycleBlocked(input_obj.case_id, "write_path_requires_specific_lifecycle_gate"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="write_path_without_gate_blocked",
            )
            return
        if getattr(input_obj, "write_apply_requested", False) and not input_obj.history_event_appended:
            yield FunctionResult(
                output=LifecycleBlocked(input_obj.case_id, "applied_write_without_history_event"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="write_without_history_blocked",
            )
            return
        yield FunctionResult(
            output=HandoffReady(input_obj.case_id, input_obj.intent),
            new_state=replace(state, written_with_history=state.written_with_history + (input_obj.case_id,), handoff_ready=state.handoff_ready + (input_obj.case_id,)),
            label=f"{input_obj.intent}_write_with_history",
        )


class RunMaintenanceAudit:
    name = "RunMaintenanceAudit"
    reads = ("root_ready",)
    writes = ("maintenance_ready", "partial", "blocked")
    accepted_input_type = (DatabaseRootReady, AdmissionGateReady)
    input_description = "database root ready for audit"
    output_description = "maintenance-ready path, partial, or blocked"
    idempotency = "Maintenance audit reads lifecycle artifacts and project evidence."

    def apply(self, input_obj, state: State) -> Iterable[FunctionResult]:
        if isinstance(input_obj, AdmissionGateReady):
            yield FunctionResult(output=input_obj, new_state=state, label="maintenance_not_required")
            return
        if input_obj.intent != "audit":
            yield FunctionResult(output=input_obj, new_state=state, label="maintenance_not_required")
            return
        if not input_obj.maintenance_audit_ran:
            yield FunctionResult(
                output=LifecycleBlocked(input_obj.case_id, "maintenance_audit_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="maintenance_audit_missing_blocked",
            )
            return
        if input_obj.lifecycle_gaps:
            yield FunctionResult(
                output=LifecyclePartial(input_obj.case_id, "maintenance_lifecycle_gaps"),
                new_state=replace(state, maintenance_ready=state.maintenance_ready + (input_obj.case_id,), partial=state.partial + (input_obj.case_id,)),
                label="maintenance_gaps_partial",
            )
            return
        yield FunctionResult(
            output=MaintenanceReady(input_obj.case_id, input_obj.intent, input_obj.handoff_rendered),
            new_state=replace(state, maintenance_ready=state.maintenance_ready + (input_obj.case_id,)),
            label="maintenance_audit_clean",
        )


class GateArchive:
    name = "GateArchive"
    reads = ("root_ready",)
    writes = ("archive_ready", "dry_run", "blocked")
    accepted_input_type = (DatabaseRootReady, AdmissionGateReady)
    input_description = "database root ready for archive"
    output_description = "archive-ready path or blocked/dry-run"
    idempotency = "Archive gate checks explicit reason and apply state."

    def apply(self, input_obj, state: State) -> Iterable[FunctionResult]:
        if isinstance(input_obj, AdmissionGateReady):
            yield FunctionResult(output=input_obj, new_state=state, label="archive_not_required")
            return
        if input_obj.intent != "archive":
            yield FunctionResult(output=input_obj, new_state=state, label="archive_not_required")
            return
        if not input_obj.archive_reason_recorded:
            yield FunctionResult(
                output=LifecycleBlocked(input_obj.case_id, "archive_reason_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="archive_reason_missing_blocked",
            )
            return
        if not input_obj.write_apply_requested:
            yield FunctionResult(
                output=LifecycleDryRun(input_obj.case_id, "archive_requires_apply"),
                new_state=replace(state, dry_run=state.dry_run + (input_obj.case_id,)),
                label="archive_dry_run_no_write",
            )
            return
        yield FunctionResult(
            output=ArchiveReady(input_obj.case_id, input_obj.intent, input_obj.write_apply_requested, input_obj.history_event_appended),
            new_state=replace(state, archive_ready=state.archive_ready + (input_obj.case_id,)),
            label="archive_gate_ready",
        )


class RenderHandoff:
    name = "RenderHandoff"
    reads = ("root_ready", "maintenance_ready")
    writes = ("handoff_ready", "partial")
    accepted_input_type = (DatabaseRootReady, MaintenanceReady, AdmissionGateReady, ArchiveReady)
    input_description = "database ready for AI handoff"
    output_description = "handoff ready or partial"
    idempotency = "Handoff rendering writes/returns Markdown navigation only."

    def apply(self, input_obj, state: State) -> Iterable[FunctionResult]:
        if input_obj.intent != "handoff" and not isinstance(input_obj, MaintenanceReady):
            yield FunctionResult(output=input_obj, new_state=state, label="handoff_not_required")
            return
        if not input_obj.handoff_rendered:
            yield FunctionResult(
                output=LifecyclePartial(input_obj.case_id, "handoff_not_rendered"),
                new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                label="handoff_missing_partial",
            )
            return
        yield FunctionResult(
            output=HandoffReady(input_obj.case_id, input_obj.intent),
            new_state=replace(state, handoff_ready=state.handoff_ready + (input_obj.case_id,)),
            label="ai_handoff_rendered",
        )


def no_handoff_without_explicit_context(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.handoff_ready) - set(state.explicit_context)
    if missing:
        return InvariantResult.fail(f"handoff without explicit database context: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_write_without_history(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.written_with_history) - set(state.handoff_ready)
    if missing:
        return InvariantResult.fail(f"write state without handoff terminal: {sorted(missing)!r}")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant("no_handoff_without_explicit_context", "Database lifecycle handoff requires explicit database context.", no_handoff_without_explicit_context),
    Invariant("no_write_without_history", "Applied lifecycle writes require history-backed terminal handoff.", no_write_without_history),
)

MAX_SEQUENCE_LENGTH = 6


def initial_state() -> State:
    return State()


def terminal_predicate(current_output, state: State, trace) -> bool:
    del state, trace
    return isinstance(current_output, (HandoffReady, MaintenanceReady, LifecycleDryRun, LifecyclePartial, LifecycleBlocked))


def build_workflow() -> Workflow:
    return Workflow(
        (
            RequireExplicitDatabaseIntent(),
            CheckRootArtifacts(),
            PlanProjectIntake(),
            GateProjectAdmission(),
            RunMaintenanceAudit(),
            GateArchive(),
            RenderHandoff(),
            CommitMutationHistory(),
        ),
        name="physicsguard_database_lifecycle",
    )
