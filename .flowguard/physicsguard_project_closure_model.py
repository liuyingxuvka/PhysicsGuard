"""FlowGuard model for PhysicsGuard project closure gates."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Literal

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


ClaimScope = Literal[
    "project_ready",
    "analysis_ready",
    "validation_ready",
    "validated_reuse_ready",
    "fault_localization_ready",
]


@dataclass(frozen=True)
class ProjectClosureInput:
    case_id: str
    claim_scope: ClaimScope
    project_audit_ok: bool
    evidence_check_ok: bool
    gap_check_ran: bool
    blocking_gaps: bool
    review_gaps: bool
    evidence_map_ok: bool
    required_checks_supplied: bool
    test_contracts_ok: bool
    validation_ok: bool
    model_library_ok: bool
    hierarchy_closure_ok: bool
    evidence_mesh_required: bool
    evidence_mesh_ok: bool


@dataclass(frozen=True)
class AuditReady:
    case_id: str
    claim_scope: ClaimScope
    evidence_check_ok: bool
    gap_check_ran: bool
    blocking_gaps: bool
    review_gaps: bool
    evidence_map_ok: bool
    required_checks_supplied: bool
    test_contracts_ok: bool
    validation_ok: bool
    model_library_ok: bool
    hierarchy_closure_ok: bool
    evidence_mesh_required: bool
    evidence_mesh_ok: bool


@dataclass(frozen=True)
class EvidenceReady:
    case_id: str
    claim_scope: ClaimScope
    review_gaps: bool
    required_checks_supplied: bool
    test_contracts_ok: bool
    validation_ok: bool
    model_library_ok: bool
    hierarchy_closure_ok: bool
    evidence_mesh_required: bool
    evidence_mesh_ok: bool


@dataclass(frozen=True)
class DownstreamReady:
    case_id: str
    claim_scope: ClaimScope
    review_gaps: bool


@dataclass(frozen=True)
class ClosurePassed:
    case_id: str


@dataclass(frozen=True)
class ClosurePartial:
    case_id: str
    reason: str


@dataclass(frozen=True)
class ClosureBlocked:
    case_id: str
    reason: str


@dataclass(frozen=True)
class State:
    audited: tuple[str, ...] = ()
    evidence_checked: tuple[str, ...] = ()
    gap_checked: tuple[str, ...] = ()
    map_checked: tuple[str, ...] = ()
    downstream_checked: tuple[str, ...] = ()
    evidence_mesh_checked: tuple[str, ...] = ()
    closure_passed: tuple[str, ...] = ()
    closure_partial: tuple[str, ...] = ()
    closure_blocked: tuple[str, ...] = ()


class RunProjectAudit:
    name = "RunProjectAudit"
    reads = ()
    writes = ("audited", "closure_blocked")
    accepted_input_type = ProjectClosureInput
    input_description = "project closure request"
    output_description = "AuditReady or ClosureBlocked"
    idempotency = "Project audit reads current adoption records and installed package metadata."

    def apply(self, input_obj: ProjectClosureInput, state: State) -> Iterable[FunctionResult]:
        if not input_obj.project_audit_ok:
            yield FunctionResult(
                output=ClosureBlocked(input_obj.case_id, "project_audit_failed"),
                new_state=replace(state, closure_blocked=state.closure_blocked + (input_obj.case_id,)),
                label="project_audit_blocks",
            )
            return
        yield FunctionResult(
            output=AuditReady(
                input_obj.case_id,
                input_obj.claim_scope,
                input_obj.evidence_check_ok,
                input_obj.gap_check_ran,
                input_obj.blocking_gaps,
                input_obj.review_gaps,
                input_obj.evidence_map_ok,
                input_obj.required_checks_supplied,
                input_obj.test_contracts_ok,
                input_obj.validation_ok,
                input_obj.model_library_ok,
                input_obj.hierarchy_closure_ok,
                input_obj.evidence_mesh_required,
                input_obj.evidence_mesh_ok,
            ),
            new_state=replace(state, audited=state.audited + (input_obj.case_id,)),
            label="project_audit_ready",
        )


class RunEvidenceGate:
    name = "RunEvidenceGate"
    reads = ("audited",)
    writes = ("evidence_checked", "gap_checked", "map_checked", "closure_blocked", "closure_partial")
    accepted_input_type = AuditReady
    input_description = "audit-ready closure request"
    output_description = "EvidenceReady, ClosurePartial, or ClosureBlocked"
    idempotency = "Evidence gate reads current registry, gap report, and map report."

    def apply(self, input_obj: AuditReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.evidence_check_ok:
            yield FunctionResult(
                output=ClosureBlocked(input_obj.case_id, "evidence_check_failed"),
                new_state=replace(state, closure_blocked=state.closure_blocked + (input_obj.case_id,)),
                label="evidence_check_blocks",
            )
            return
        if not input_obj.gap_check_ran:
            yield FunctionResult(
                output=ClosureBlocked(input_obj.case_id, "gap_check_missing"),
                new_state=replace(state, evidence_checked=state.evidence_checked + (input_obj.case_id,), closure_blocked=state.closure_blocked + (input_obj.case_id,)),
                label="map_alone_cannot_pass",
            )
            return
        if input_obj.blocking_gaps:
            yield FunctionResult(
                output=ClosureBlocked(input_obj.case_id, "blocking_evidence_gaps"),
                new_state=replace(state, evidence_checked=state.evidence_checked + (input_obj.case_id,), gap_checked=state.gap_checked + (input_obj.case_id,), closure_blocked=state.closure_blocked + (input_obj.case_id,)),
                label="blocking_gap_blocks",
            )
            return
        if not input_obj.evidence_map_ok:
            yield FunctionResult(
                output=ClosurePartial(input_obj.case_id, "evidence_map_missing_or_partial"),
                new_state=replace(state, evidence_checked=state.evidence_checked + (input_obj.case_id,), gap_checked=state.gap_checked + (input_obj.case_id,), closure_partial=state.closure_partial + (input_obj.case_id,)),
                label="map_missing_partial",
            )
            return
        yield FunctionResult(
            output=EvidenceReady(
                input_obj.case_id,
                input_obj.claim_scope,
                input_obj.review_gaps,
                input_obj.required_checks_supplied,
                input_obj.test_contracts_ok,
                input_obj.validation_ok,
                input_obj.model_library_ok,
                input_obj.hierarchy_closure_ok,
                input_obj.evidence_mesh_required,
                input_obj.evidence_mesh_ok,
            ),
            new_state=replace(
                state,
                evidence_checked=state.evidence_checked + (input_obj.case_id,),
                gap_checked=state.gap_checked + (input_obj.case_id,),
                map_checked=state.map_checked + (input_obj.case_id,),
            ),
            label="evidence_gate_clean" if not input_obj.review_gaps else "review_gap_downgrades",
        )


class RunDownstreamChecks:
    name = "RunDownstreamChecks"
    reads = ("evidence_checked", "gap_checked", "map_checked")
    writes = ("downstream_checked", "closure_blocked")
    accepted_input_type = EvidenceReady
    input_description = "evidence-ready closure request"
    output_description = "DownstreamReady or ClosureBlocked"
    idempotency = "Downstream checks reuse current route-owned reports."

    def apply(self, input_obj: EvidenceReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.required_checks_supplied:
            yield FunctionResult(
                output=ClosureBlocked(input_obj.case_id, "required_checks_skipped"),
                new_state=replace(state, closure_blocked=state.closure_blocked + (input_obj.case_id,)),
                label="skipped_required_blocks",
            )
            return
        if not input_obj.test_contracts_ok:
            yield FunctionResult(
                output=ClosureBlocked(input_obj.case_id, "test_contracts_failed"),
                new_state=replace(state, closure_blocked=state.closure_blocked + (input_obj.case_id,)),
                label="test_contract_blocks",
            )
            return
        if input_obj.claim_scope in {"validation_ready", "validated_reuse_ready"} and not input_obj.validation_ok:
            yield FunctionResult(
                output=ClosureBlocked(input_obj.case_id, "validation_failed"),
                new_state=replace(state, closure_blocked=state.closure_blocked + (input_obj.case_id,)),
                label="validation_blocks",
            )
            return
        if input_obj.claim_scope == "validated_reuse_ready" and not input_obj.model_library_ok:
            yield FunctionResult(
                output=ClosureBlocked(input_obj.case_id, "model_library_failed"),
                new_state=replace(state, closure_blocked=state.closure_blocked + (input_obj.case_id,)),
                label="model_library_blocks",
            )
            return
        if input_obj.claim_scope == "fault_localization_ready" and not input_obj.hierarchy_closure_ok:
            yield FunctionResult(
                output=ClosureBlocked(input_obj.case_id, "hierarchy_closure_failed"),
                new_state=replace(state, closure_blocked=state.closure_blocked + (input_obj.case_id,)),
                label="hierarchy_closure_blocks",
            )
            return
        if input_obj.evidence_mesh_required and not input_obj.evidence_mesh_ok:
            yield FunctionResult(
                output=ClosureBlocked(input_obj.case_id, "evidence_mesh_failed"),
                new_state=replace(state, closure_blocked=state.closure_blocked + (input_obj.case_id,)),
                label="evidence_mesh_blocks",
            )
            return
        evidence_mesh_checked = state.evidence_mesh_checked
        if input_obj.evidence_mesh_required:
            evidence_mesh_checked = evidence_mesh_checked + (input_obj.case_id,)
        yield FunctionResult(
            output=DownstreamReady(input_obj.case_id, input_obj.claim_scope, input_obj.review_gaps),
            new_state=replace(
                state,
                downstream_checked=state.downstream_checked + (input_obj.case_id,),
                evidence_mesh_checked=evidence_mesh_checked,
            ),
            label="downstream_checks_ready" if not input_obj.evidence_mesh_required else "downstream_checks_with_evidence_mesh",
        )


class FinalizeClosure:
    name = "FinalizeClosure"
    reads = ("downstream_checked",)
    writes = ("closure_passed", "closure_partial")
    accepted_input_type = DownstreamReady
    input_description = "downstream-ready closure request"
    output_description = "ClosurePassed or ClosurePartial"
    idempotency = "Finalization derives claim readiness from checked route evidence."

    def apply(self, input_obj: DownstreamReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.review_gaps:
            yield FunctionResult(
                output=ClosurePartial(input_obj.case_id, "review_gaps_visible"),
                new_state=replace(state, closure_partial=state.closure_partial + (input_obj.case_id,)),
                label="review_gaps_partial",
            )
            return
        yield FunctionResult(
            output=ClosurePassed(input_obj.case_id),
            new_state=replace(state, closure_passed=state.closure_passed + (input_obj.case_id,)),
            label="closure_passed",
        )


def no_pass_without_audit(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.closure_passed) - set(state.audited)
    if missing:
        return InvariantResult.fail(f"closure passed without project audit: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_pass_without_gap_check_and_map(state: State, trace) -> InvariantResult:
    del trace
    ready = set(state.gap_checked) & set(state.map_checked)
    missing = set(state.closure_passed) - ready
    if missing:
        return InvariantResult.fail(f"closure passed without gap check and map: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_pass_without_downstream_checks(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.closure_passed) - set(state.downstream_checked)
    if missing:
        return InvariantResult.fail(f"closure passed without downstream checks: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_case_both_passed_and_blocked(state: State, trace) -> InvariantResult:
    del trace
    overlap = set(state.closure_passed) & set(state.closure_blocked)
    if overlap:
        return InvariantResult.fail(f"closure both passed and blocked: {sorted(overlap)!r}")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant("no_pass_without_audit", "Closure pass requires project audit.", no_pass_without_audit),
    Invariant("no_pass_without_gap_check_and_map", "Closure pass requires gap-check and map.", no_pass_without_gap_check_and_map),
    Invariant("no_pass_without_downstream_checks", "Closure pass requires downstream checks.", no_pass_without_downstream_checks),
    Invariant("no_case_both_passed_and_blocked", "Closure cannot both pass and block.", no_case_both_passed_and_blocked),
)

MAX_SEQUENCE_LENGTH = 5


def initial_state() -> State:
    return State()


def terminal_predicate(current_output, state: State, trace) -> bool:
    del state, trace
    return isinstance(current_output, (ClosurePassed, ClosurePartial, ClosureBlocked))


def build_workflow() -> Workflow:
    return Workflow(
        (
            RunProjectAudit(),
            RunEvidenceGate(),
            RunDownstreamChecks(),
            FinalizeClosure(),
        ),
        name="physicsguard_project_closure",
    )
