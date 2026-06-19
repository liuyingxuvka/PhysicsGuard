from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


BROAD_CLAIMS = ("active_validated", "active_reusable", "validated", "reusable", "pass")
BROAD_LIFECYCLE_STATES = ("active_validated", "active_reusable")


@dataclass(frozen=True)
class DataBankEvent:
    pass


@dataclass(frozen=True)
class RootCheckInput(DataBankEvent):
    root_ready: bool


@dataclass(frozen=True)
class ProviderResultInput(DataBankEvent):
    provider_id: str
    status: str
    has_stale: bool = False
    has_missing: bool = False
    has_skipped: bool = False


@dataclass(frozen=True)
class CatalogClaimInput(DataBankEvent):
    project_id: str
    claim: str


@dataclass(frozen=True)
class LifecycleRequestInput(DataBankEvent):
    project_id: str
    target_state: str
    apply: bool = False


@dataclass(frozen=True)
class DataBankDecision:
    subject_id: str
    status: str
    reason: str


@dataclass(frozen=True)
class State:
    root_ready: bool = False
    provider_statuses: tuple[str, ...] = ()
    closure_status: str = "unknown"
    allowed_broad_claims: tuple[str, ...] = ()
    lifecycle_states: tuple[str, ...] = ()
    history_events: tuple[str, ...] = ()
    downgrade_events: tuple[str, ...] = ()


class ApplyDataBankWorkflowEvent:
    name = "ApplyDataBankWorkflowEvent"
    reads = ("root_ready", "provider_statuses", "closure_status", "allowed_broad_claims", "lifecycle_states")
    writes = (
        "root_ready",
        "provider_statuses",
        "closure_status",
        "allowed_broad_claims",
        "lifecycle_states",
        "history_events",
        "downgrade_events",
    )
    accepted_input_type = DataBankEvent
    input_description = "DataBank root/provider/catalog/lifecycle event"
    output_description = "DataBank workflow decision"
    idempotency = "Repeated blocked provider/root inputs keep closure blocked and cannot upgrade broad claims."

    def apply(self, input_obj: DataBankEvent, state: State) -> Iterable[FunctionResult]:
        if isinstance(input_obj, RootCheckInput):
            if not input_obj.root_ready:
                yield FunctionResult(
                    output=DataBankDecision("root", "blocked", "root_missing_or_incomplete"),
                    new_state=replace(
                        state,
                        root_ready=False,
                        closure_status="blocked",
                        allowed_broad_claims=(),
                        downgrade_events=state.downgrade_events + state.allowed_broad_claims,
                    ),
                    label="root_blocked",
                )
                return
            yield FunctionResult(
                output=DataBankDecision("root", "pass", "root_ready"),
                new_state=replace(state, root_ready=True),
                label="root_pass",
            )
            return

        if isinstance(input_obj, ProviderResultInput):
            blocked = (
                input_obj.status == "blocked"
                or input_obj.has_stale
                or input_obj.has_missing
                or input_obj.has_skipped
            )
            provider_status = "blocked" if blocked else input_obj.status
            statuses = state.provider_statuses + (provider_status,)
            closure_status = "blocked" if blocked or not state.root_ready else "pass"
            allowed_broad_claims = state.allowed_broad_claims
            downgrade_events = state.downgrade_events
            if closure_status == "blocked" and state.allowed_broad_claims:
                downgrade_events = state.downgrade_events + state.allowed_broad_claims
                allowed_broad_claims = ()
            yield FunctionResult(
                output=DataBankDecision(input_obj.provider_id, provider_status, "provider_not_current" if blocked else "provider_current"),
                new_state=replace(
                    state,
                    provider_statuses=statuses,
                    closure_status=closure_status,
                    allowed_broad_claims=allowed_broad_claims,
                    downgrade_events=downgrade_events,
                ),
                label="provider_blocked" if blocked else "provider_pass",
            )
            return

        if isinstance(input_obj, CatalogClaimInput):
            broad = input_obj.claim in BROAD_CLAIMS
            if broad and (not state.root_ready or state.closure_status != "pass"):
                yield FunctionResult(
                    output=DataBankDecision(input_obj.project_id, "downgraded", input_obj.claim),
                    new_state=replace(state, downgrade_events=state.downgrade_events + (input_obj.project_id,)),
                    label="downgraded_catalog_claim",
                )
                return
            if broad:
                yield FunctionResult(
                    output=DataBankDecision(input_obj.project_id, "pass", input_obj.claim),
                    new_state=replace(state, allowed_broad_claims=state.allowed_broad_claims + (input_obj.project_id,)),
                    label="allowed_broad_claim",
                )
                return
            yield FunctionResult(
                output=DataBankDecision(input_obj.project_id, "partial", input_obj.claim),
                new_state=state,
                label="scoped_catalog_claim",
            )
            return

        if isinstance(input_obj, LifecycleRequestInput):
            broad = input_obj.target_state in BROAD_LIFECYCLE_STATES
            if broad and (not state.root_ready or state.closure_status != "pass"):
                yield FunctionResult(
                    output=DataBankDecision(input_obj.project_id, "blocked", "lifecycle_requires_passing_closure"),
                    new_state=state,
                    label="blocked_lifecycle_promotion",
                )
                return
            next_lifecycle = state.lifecycle_states + (input_obj.target_state,)
            next_history = state.history_events + (input_obj.project_id,) if input_obj.apply else state.history_events
            yield FunctionResult(
                output=DataBankDecision(input_obj.project_id, "pass", input_obj.target_state),
                new_state=replace(state, lifecycle_states=next_lifecycle, history_events=next_history),
                label="applied_lifecycle_transition" if input_obj.apply else "dry_run_lifecycle_transition",
            )


class BrokenApplyDataBankWorkflowEvent(ApplyDataBankWorkflowEvent):
    name = "BrokenApplyDataBankWorkflowEvent"

    def apply(self, input_obj: DataBankEvent, state: State) -> Iterable[FunctionResult]:
        if isinstance(input_obj, LifecycleRequestInput) and input_obj.target_state in BROAD_LIFECYCLE_STATES:
            yield FunctionResult(
                output=DataBankDecision(input_obj.project_id, "pass", input_obj.target_state),
                new_state=replace(state, lifecycle_states=state.lifecycle_states + (input_obj.target_state,)),
                label="broken_lifecycle_promotion",
            )
            return
        yield from super().apply(input_obj, state)


def no_broad_claim_allowed_without_current_closure(state: State, trace) -> InvariantResult:
    del trace
    if (not state.root_ready or state.closure_status == "blocked") and state.allowed_broad_claims:
        return InvariantResult.fail("catalog allowed broad claims without current passing closure")
    return InvariantResult.pass_()


def lifecycle_broad_state_requires_current_closure(state: State, trace) -> InvariantResult:
    del trace
    if any(item in BROAD_LIFECYCLE_STATES for item in state.lifecycle_states):
        if not state.root_ready or state.closure_status != "pass":
            return InvariantResult.fail("lifecycle promoted validated/reusable without passing closure")
    return InvariantResult.pass_()


def blocked_provider_plus_broad_claim_downgrades(state: State, trace) -> InvariantResult:
    blocked_seen = any(step.label == "provider_blocked" for step in trace.steps)
    broad_claim_seen = any(
        isinstance(step.function_input, CatalogClaimInput) and step.function_input.claim in BROAD_CLAIMS
        for step in trace.steps
    )
    downgrade_seen = any(step.label == "downgraded_catalog_claim" for step in trace.steps)
    if blocked_seen and broad_claim_seen and not (downgrade_seen or state.downgrade_events):
        return InvariantResult.fail("blocked provider plus broad catalog claim did not downgrade")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="no_broad_claim_allowed_without_current_closure",
        description="Broad catalog claims require root and current passing closure.",
        predicate=no_broad_claim_allowed_without_current_closure,
    ),
    Invariant(
        name="lifecycle_broad_state_requires_current_closure",
        description="active_validated and active_reusable require current passing closure.",
        predicate=lifecycle_broad_state_requires_current_closure,
    ),
    Invariant(
        name="blocked_provider_plus_broad_claim_downgrades",
        description="Blocked provider evidence plus broad catalog claim downgrades.",
        predicate=blocked_provider_plus_broad_claim_downgrades,
    ),
)


EXTERNAL_INPUTS = (
    RootCheckInput(True),
    RootCheckInput(False),
    ProviderResultInput("physicsguard", "pass"),
    ProviderResultInput("physicsguard", "blocked", has_missing=True),
    CatalogClaimInput("project", "active_validated"),
    CatalogClaimInput("project", "candidate"),
    LifecycleRequestInput("project", "active_registered", apply=True),
    LifecycleRequestInput("project", "active_validated", apply=True),
)


MAX_SEQUENCE_LENGTH = 3


def initial_state() -> State:
    return State()


def build_workflow() -> Workflow:
    return Workflow((ApplyDataBankWorkflowEvent(),), name="databank_workflow")


def broken_workflow() -> Workflow:
    return Workflow((BrokenApplyDataBankWorkflowEvent(),), name="databank_workflow_broken")


def terminal_predicate(current_output, state, trace) -> bool:
    del state, trace
    return isinstance(current_output, DataBankDecision)
