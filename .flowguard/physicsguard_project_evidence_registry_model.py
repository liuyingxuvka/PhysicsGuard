"""FlowGuard model for PhysicsGuard project evidence registry workflow."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Literal

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


DownstreamClaim = Literal["none", "validation", "reuse"]


@dataclass(frozen=True)
class ProjectEvidenceInput:
    case_id: str
    project_profile_known: bool
    project_profile_unknowns_recorded: bool
    artifacts_registered: bool
    binding_expectations_reviewed: bool
    bindings_complete_or_exempt: bool
    gap_check_ran: bool
    blocking_gaps: bool
    review_gaps: bool
    evidence_map_generated: bool
    downstream_claim: DownstreamClaim


@dataclass(frozen=True)
class ProfileReady:
    case_id: str
    artifacts_registered: bool
    binding_expectations_reviewed: bool
    bindings_complete_or_exempt: bool
    gap_check_ran: bool
    blocking_gaps: bool
    review_gaps: bool
    evidence_map_generated: bool
    downstream_claim: DownstreamClaim


@dataclass(frozen=True)
class ArtifactsReady:
    case_id: str
    binding_expectations_reviewed: bool
    bindings_complete_or_exempt: bool
    gap_check_ran: bool
    blocking_gaps: bool
    review_gaps: bool
    evidence_map_generated: bool
    downstream_claim: DownstreamClaim


@dataclass(frozen=True)
class BindingMaintenanceReady:
    case_id: str
    gap_check_ran: bool
    blocking_gaps: bool
    review_gaps: bool
    evidence_map_generated: bool
    downstream_claim: DownstreamClaim


@dataclass(frozen=True)
class GapChecked:
    case_id: str
    review_gaps: bool
    evidence_map_generated: bool
    downstream_claim: DownstreamClaim


@dataclass(frozen=True)
class ProjectEvidenceReady:
    case_id: str
    downstream_claim: DownstreamClaim


@dataclass(frozen=True)
class DownstreamHandoffReady:
    case_id: str
    downstream_claim: DownstreamClaim


@dataclass(frozen=True)
class ProjectEvidencePartial:
    case_id: str
    reason: str


@dataclass(frozen=True)
class ProjectEvidenceBlocked:
    case_id: str
    reason: str


@dataclass(frozen=True)
class State:
    profile_reviewed: tuple[str, ...] = ()
    artifacts_registered: tuple[str, ...] = ()
    binding_reviewed: tuple[str, ...] = ()
    gap_checked: tuple[str, ...] = ()
    map_generated: tuple[str, ...] = ()
    project_ready: tuple[str, ...] = ()
    downstream_ready: tuple[str, ...] = ()
    partial: tuple[str, ...] = ()
    blocked: tuple[str, ...] = ()


class ReviewProjectProfile:
    name = "ReviewProjectProfile"
    reads = ()
    writes = ("profile_reviewed", "partial")
    accepted_input_type = ProjectEvidenceInput
    input_description = "project evidence maintenance request"
    output_description = "ProfileReady or ProjectEvidencePartial"
    idempotency = "Project profile review reads registry fields and source references."

    def apply(self, input_obj: ProjectEvidenceInput, state: State) -> Iterable[FunctionResult]:
        if not input_obj.project_profile_known and not input_obj.project_profile_unknowns_recorded:
            yield FunctionResult(
                output=ProjectEvidencePartial(input_obj.case_id, "project_profile_missing"),
                new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                label="profile_missing_partial",
            )
            return
        label = "profile_known" if input_obj.project_profile_known else "profile_unknown_recorded"
        yield FunctionResult(
            output=ProfileReady(
                input_obj.case_id,
                input_obj.artifacts_registered,
                input_obj.binding_expectations_reviewed,
                input_obj.bindings_complete_or_exempt,
                input_obj.gap_check_ran,
                input_obj.blocking_gaps,
                input_obj.review_gaps,
                input_obj.evidence_map_generated,
                input_obj.downstream_claim,
            ),
            new_state=replace(state, profile_reviewed=state.profile_reviewed + (input_obj.case_id,)),
            label=label,
        )


class RegisterArtifacts:
    name = "RegisterArtifacts"
    reads = ("profile_reviewed",)
    writes = ("artifacts_registered", "partial")
    accepted_input_type = ProfileReady
    input_description = "profile-reviewed project evidence"
    output_description = "ArtifactsReady or ProjectEvidencePartial"
    idempotency = "Artifact registration checks current registry records only."

    def apply(self, input_obj: ProfileReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.artifacts_registered:
            yield FunctionResult(
                output=ProjectEvidencePartial(input_obj.case_id, "artifacts_missing"),
                new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                label="artifacts_missing_partial",
            )
            return
        yield FunctionResult(
            output=ArtifactsReady(
                input_obj.case_id,
                input_obj.binding_expectations_reviewed,
                input_obj.bindings_complete_or_exempt,
                input_obj.gap_check_ran,
                input_obj.blocking_gaps,
                input_obj.review_gaps,
                input_obj.evidence_map_generated,
                input_obj.downstream_claim,
            ),
            new_state=replace(state, artifacts_registered=state.artifacts_registered + (input_obj.case_id,)),
            label="artifacts_registered",
        )


class ReviewBindingMaintenance:
    name = "ReviewBindingMaintenance"
    reads = ("artifacts_registered",)
    writes = ("binding_reviewed", "partial")
    accepted_input_type = ArtifactsReady
    input_description = "artifact-registered project evidence"
    output_description = "BindingMaintenanceReady or ProjectEvidencePartial"
    idempotency = "Binding maintenance review checks expectations and summaries."

    def apply(self, input_obj: ArtifactsReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.binding_expectations_reviewed:
            yield FunctionResult(
                output=ProjectEvidencePartial(input_obj.case_id, "binding_expectations_unreviewed"),
                new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                label="binding_unreviewed_partial",
            )
            return
        if not input_obj.bindings_complete_or_exempt:
            yield FunctionResult(
                output=ProjectEvidencePartial(input_obj.case_id, "binding_missing_or_unexempted"),
                new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                label="binding_missing_partial",
            )
            return
        yield FunctionResult(
            output=BindingMaintenanceReady(
                input_obj.case_id,
                input_obj.gap_check_ran,
                input_obj.blocking_gaps,
                input_obj.review_gaps,
                input_obj.evidence_map_generated,
                input_obj.downstream_claim,
            ),
            new_state=replace(state, binding_reviewed=state.binding_reviewed + (input_obj.case_id,)),
            label="binding_complete_or_exempt",
        )


class RunGapCheck:
    name = "RunGapCheck"
    reads = ("binding_reviewed",)
    writes = ("gap_checked", "blocked")
    accepted_input_type = BindingMaintenanceReady
    input_description = "binding-reviewed project evidence"
    output_description = "GapChecked or ProjectEvidenceBlocked"
    idempotency = "Gap check is deterministic for the current registry."

    def apply(self, input_obj: BindingMaintenanceReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.gap_check_ran:
            yield FunctionResult(
                output=ProjectEvidenceBlocked(input_obj.case_id, "gap_check_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="gap_check_missing_blocked",
            )
            return
        if input_obj.blocking_gaps:
            yield FunctionResult(
                output=ProjectEvidenceBlocked(input_obj.case_id, "blocking_evidence_gaps"),
                new_state=replace(state, gap_checked=state.gap_checked + (input_obj.case_id,), blocked=state.blocked + (input_obj.case_id,)),
                label="gap_check_blocking",
            )
            return
        yield FunctionResult(
            output=GapChecked(
                input_obj.case_id,
                input_obj.review_gaps,
                input_obj.evidence_map_generated,
                input_obj.downstream_claim,
            ),
            new_state=replace(state, gap_checked=state.gap_checked + (input_obj.case_id,)),
            label="gap_check_clean" if not input_obj.review_gaps else "gap_check_review_gaps_visible",
        )


class BuildProjectEvidenceMap:
    name = "BuildProjectEvidenceMap"
    reads = ("gap_checked",)
    writes = ("map_generated", "project_ready", "partial")
    accepted_input_type = GapChecked
    input_description = "gap-checked project evidence"
    output_description = "ProjectEvidenceReady or ProjectEvidencePartial"
    idempotency = "Map generation projects registry state into an AI-readable report."

    def apply(self, input_obj: GapChecked, state: State) -> Iterable[FunctionResult]:
        if not input_obj.evidence_map_generated:
            yield FunctionResult(
                output=ProjectEvidencePartial(input_obj.case_id, "evidence_map_missing"),
                new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                label="map_missing_partial",
            )
            return
        if input_obj.review_gaps:
            yield FunctionResult(
                output=ProjectEvidencePartial(input_obj.case_id, "review_gaps_visible"),
                new_state=replace(state, map_generated=state.map_generated + (input_obj.case_id,), partial=state.partial + (input_obj.case_id,)),
                label="map_generated_review_partial",
            )
            return
        yield FunctionResult(
            output=ProjectEvidenceReady(input_obj.case_id, input_obj.downstream_claim),
            new_state=replace(
                state,
                map_generated=state.map_generated + (input_obj.case_id,),
                project_ready=state.project_ready + (input_obj.case_id,),
            ),
            label="map_generated_ready",
        )


class GateDownstreamHandoff:
    name = "GateDownstreamHandoff"
    reads = ("project_ready",)
    writes = ("downstream_ready",)
    accepted_input_type = ProjectEvidenceReady
    input_description = "project evidence ready"
    output_description = "DownstreamHandoffReady"
    idempotency = "Downstream handoff only projects an already-ready evidence state."

    def apply(self, input_obj: ProjectEvidenceReady, state: State) -> Iterable[FunctionResult]:
        label = {
            "none": "project_map_ready",
            "validation": "downstream_validation_allowed",
            "reuse": "downstream_reuse_allowed",
        }[input_obj.downstream_claim]
        yield FunctionResult(
            output=DownstreamHandoffReady(input_obj.case_id, input_obj.downstream_claim),
            new_state=replace(state, downstream_ready=state.downstream_ready + (input_obj.case_id,)),
            label=label,
        )


def no_ready_without_profile(state: State, trace) -> InvariantResult:
    del trace
    missing = (set(state.project_ready) | set(state.downstream_ready)) - set(state.profile_reviewed)
    if missing:
        return InvariantResult.fail(f"project evidence ready without project profile review: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_ready_without_artifacts_and_bindings(state: State, trace) -> InvariantResult:
    del trace
    ready = set(state.artifacts_registered) & set(state.binding_reviewed)
    missing = (set(state.project_ready) | set(state.downstream_ready)) - ready
    if missing:
        return InvariantResult.fail(f"project evidence ready without artifacts/bindings: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_ready_without_gap_check_and_map(state: State, trace) -> InvariantResult:
    del trace
    ready = set(state.gap_checked) & set(state.map_generated)
    missing = (set(state.project_ready) | set(state.downstream_ready)) - ready
    if missing:
        return InvariantResult.fail(f"project evidence ready without gap-check/map: {sorted(missing)!r}")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant("no_ready_without_profile", "Project evidence ready requires profile review.", no_ready_without_profile),
    Invariant("no_ready_without_artifacts_and_bindings", "Project evidence ready requires artifacts and binding maintenance.", no_ready_without_artifacts_and_bindings),
    Invariant("no_ready_without_gap_check_and_map", "Project evidence ready requires gap-check and evidence map.", no_ready_without_gap_check_and_map),
)

EXTERNAL_INPUTS = (
    ProjectEvidenceInput("complete_project_map", True, False, True, True, True, True, False, False, True, "none"),
    ProjectEvidenceInput("unknown_profile_recorded", False, True, True, True, True, True, False, False, True, "none"),
    ProjectEvidenceInput("validation_handoff", True, False, True, True, True, True, False, False, True, "validation"),
    ProjectEvidenceInput("reuse_handoff", True, False, True, True, True, True, False, False, True, "reuse"),
    ProjectEvidenceInput("profile_missing", False, False, True, True, True, True, False, False, True, "none"),
    ProjectEvidenceInput("artifact_missing", True, False, False, True, True, True, False, False, True, "none"),
    ProjectEvidenceInput("binding_unreviewed", True, False, True, False, False, True, False, False, True, "none"),
    ProjectEvidenceInput("binding_missing", True, False, True, True, False, True, False, False, True, "none"),
    ProjectEvidenceInput("gap_check_missing", True, False, True, True, True, False, False, False, True, "validation"),
    ProjectEvidenceInput("blocking_gap", True, False, True, True, True, True, True, False, True, "validation"),
    ProjectEvidenceInput("review_gap", True, False, True, True, True, True, False, True, True, "none"),
    ProjectEvidenceInput("map_missing", True, False, True, True, True, True, False, False, False, "none"),
)
MAX_SEQUENCE_LENGTH = 6


def initial_state() -> State:
    return State()


def terminal_predicate(current_output, state: State, trace) -> bool:
    del state, trace
    return isinstance(current_output, (DownstreamHandoffReady, ProjectEvidencePartial, ProjectEvidenceBlocked))


def build_workflow() -> Workflow:
    return Workflow(
        (
            ReviewProjectProfile(),
            RegisterArtifacts(),
            ReviewBindingMaintenance(),
            RunGapCheck(),
            BuildProjectEvidenceMap(),
            GateDownstreamHandoff(),
        ),
        name="physicsguard_project_evidence_registry",
    )
