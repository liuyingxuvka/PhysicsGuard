"""Finite model for PhysicsGuard purpose-template-pack selection."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import (
    FlowGuardCheckPlan,
    FunctionResult,
    Invariant,
    InvariantResult,
    KnownBadProof,
    MinimumModelContract,
    RiskIntent,
    RiskProfile,
    SkippedCheck,
    TemplateHarvestReview,
    TemplateReuseReview,
    Workflow,
    run_model_first_checks,
)


@dataclass(frozen=True)
class SelectionInput:
    request_id: str
    candidate_count: int
    has_base: bool = True
    pairwise_compatible: bool = False
    field_collision: bool = False
    has_strict_dominator: bool = False


@dataclass(frozen=True)
class SelectionOutput:
    disposition: str
    selected_ids: tuple[str, ...]
    receipt_fingerprint: str
    reason: str = ""


@dataclass(frozen=True)
class State:
    receipts: tuple[tuple[str, str], ...] = ()
    last_disposition: str = ""
    selected_ids: tuple[str, ...] = ()
    field_owners: tuple[tuple[str, str], ...] = ()
    instance_authorized: bool = False
    last_pairwise_compatible: bool = False
    last_field_collision: bool = False


def request_fingerprint(item: SelectionInput) -> str:
    return "|".join(
        (
            item.request_id,
            str(item.candidate_count),
            str(item.has_base),
            str(item.pairwise_compatible),
            str(item.field_collision),
            str(item.has_strict_dominator),
        )
    )


def stable_receipt_fingerprint(item: SelectionInput, disposition: str, selected_ids: tuple[str, ...]) -> str:
    return f"receipt:{request_fingerprint(item)}:{disposition}:{','.join(selected_ids)}"


class ResolveTemplateCandidates:
    """Input x State -> Set(Output x State) for the correct selector."""

    name = "ResolveTemplateCandidates"
    reads = ("receipts",)
    writes = (
        "receipts",
        "last_disposition",
        "selected_ids",
        "field_owners",
        "instance_authorized",
    )
    accepted_input_type = SelectionInput
    input_description = "frozen candidate-set facts from the target-native route"
    output_description = "one finite decision plus immutable selection-receipt identity"
    idempotency = "The same request and catalog facts produce one receipt fingerprint."

    def apply(self, input_obj: SelectionInput, state: State) -> Iterable[FunctionResult]:
        if input_obj.candidate_count == 0:
            if input_obj.has_base:
                disposition = "base_no_match"
                selected = ("physicsguard.base.audit-blueprint",)
                owners = (("workflow_kind", selected[0]),)
                authorized = True
                reason = "no_domain_match_harvest_required"
            else:
                disposition = "ambiguous_template_selection"
                selected = ()
                owners = ()
                authorized = False
                reason = "no_approved_base"
        elif input_obj.candidate_count == 1:
            disposition = "single_selected"
            selected = ("candidate-1",)
            owners = (("workflow_kind", selected[0]),)
            authorized = True
            reason = ""
        elif input_obj.has_strict_dominator:
            disposition = "strictly_dominated_selection"
            selected = ("candidate-1",)
            owners = (("workflow_kind", selected[0]),)
            authorized = True
            reason = "target_authored_strict_dominance"
        elif input_obj.pairwise_compatible and not input_obj.field_collision:
            disposition = "composed"
            selected = ("candidate-1", "candidate-2")
            owners = (("mapping_context", selected[0]), ("evidence_contract", selected[1]))
            authorized = True
            reason = ""
        else:
            disposition = "ambiguous_template_selection"
            selected = ()
            owners = ()
            authorized = False
            reason = "field_owner_conflict" if input_obj.field_collision else "incompatible_candidates"

        receipt = stable_receipt_fingerprint(input_obj, disposition, selected)
        new_state = replace(
            state,
            receipts=state.receipts + ((request_fingerprint(input_obj), receipt),),
            last_disposition=disposition,
            selected_ids=selected,
            field_owners=owners,
            instance_authorized=authorized,
            last_pairwise_compatible=input_obj.pairwise_compatible,
            last_field_collision=input_obj.field_collision,
        )
        yield FunctionResult(
            SelectionOutput(disposition, selected, receipt, reason),
            new_state,
            label=disposition,
        )


class BrokenResolveTemplateCandidates(ResolveTemplateCandidates):
    """Representative broken variant with blank, conflict, ambiguity, and freshness bugs."""

    name = "BrokenResolveTemplateCandidates"

    def apply(self, input_obj: SelectionInput, state: State) -> Iterable[FunctionResult]:
        if input_obj.candidate_count == 0:
            disposition = "base_no_match"
            selected: tuple[str, ...] = ()
            owners: tuple[tuple[str, str], ...] = ()
        elif input_obj.candidate_count == 1:
            disposition = "single_selected"
            selected = ("candidate-1",)
            owners = (("workflow_kind", selected[0]),)
        else:
            disposition = "composed"
            selected = ("candidate-1", "candidate-2")
            owners = (
                ("evidence_contract", "candidate-1"),
                ("evidence_contract", "candidate-2"),
            ) if input_obj.field_collision else (
                ("mapping_context", "candidate-1"),
                ("evidence_contract", "candidate-2"),
            )
        receipt = (
            stable_receipt_fingerprint(input_obj, disposition, selected)
            + f":attempt-{len(state.receipts)}"
        )
        new_state = replace(
            state,
            receipts=state.receipts + ((request_fingerprint(input_obj), receipt),),
            last_disposition=disposition,
            selected_ids=selected,
            field_owners=owners,
            instance_authorized=True,
            last_pairwise_compatible=input_obj.pairwise_compatible,
            last_field_collision=input_obj.field_collision,
        )
        yield FunctionResult(
            SelectionOutput(disposition, selected, receipt, "broken_variant"),
            new_state,
            label=disposition,
        )


def blocked_never_authorizes(state: State, _trace) -> InvariantResult:
    if state.last_disposition == "ambiguous_template_selection" and state.instance_authorized:
        return InvariantResult.fail("ambiguous selection authorized instantiation")
    return InvariantResult.pass_()


def success_has_selection(state: State, _trace) -> InvariantResult:
    if state.instance_authorized and not state.selected_ids:
        return InvariantResult.fail("blank or missing-base selection authorized instantiation")
    return InvariantResult.pass_()


def every_field_has_one_owner(state: State, _trace) -> InvariantResult:
    fields = tuple(field_id for field_id, _owner_id in state.field_owners)
    if len(fields) != len(set(fields)):
        return InvariantResult.fail("a generated field has more than one template owner")
    return InvariantResult.pass_()


def unsafe_many_never_composes(state: State, _trace) -> InvariantResult:
    if state.last_disposition == "composed" and (
        not state.last_pairwise_compatible or state.last_field_collision
    ):
        return InvariantResult.fail("incompatible or colliding candidates composed")
    return InvariantResult.pass_()


def one_receipt_per_request_identity(state: State, _trace) -> InvariantResult:
    observed: dict[str, set[str]] = {}
    for request_id, receipt_id in state.receipts:
        observed.setdefault(request_id, set()).add(receipt_id)
    if any(len(receipts) != 1 for receipts in observed.values()):
        return InvariantResult.fail("one request identity produced multiple receipt fingerprints")
    return InvariantResult.pass_()


PROTECTED_ERRORS = (
    "ambiguous_selection_authorized",
    "blank_fallback_authorized",
    "field_owner_collision_accepted",
    "nondeterministic_selection_receipt",
)


def risk_profile() -> RiskProfile:
    return RiskProfile(
        modeled_boundary="PhysicsGuard purpose-template-pack decision and instance authorization",
        risk_classes=("selection", "composition", "field_ownership", "freshness"),
        risk_intent=RiskIntent(
            failure_modes=(
                "ambiguous or incompatible candidates authorize instantiation",
                "zero candidates silently falls back to a blank artifact",
                "two fragments own the same generated field",
                "the same frozen request receives different selection identities",
            ),
            protected_error_classes=PROTECTED_ERRORS,
            protected_harms=(
                "an AI begins from the wrong PhysicsGuard workflow contract",
                "generated work looks current while selection evidence is stale",
            ),
            must_model_state=(
                "selection receipts",
                "decision disposition",
                "selected template ids",
                "field-owner map",
                "instance authorization",
            ),
            must_model_side_effects=("immutable selection receipt write",),
            completion_evidence=(
                "one finite decision",
                "complete selected ids",
                "one field-owner map",
                "stable request-bound receipt fingerprint",
            ),
            adversarial_inputs=(
                "zero candidates without a base",
                "multiple incompatible candidates",
                "multiple compatible candidates with a field collision",
                "repeated identical request",
            ),
            hard_invariants=(
                "blocked decisions never authorize instantiation",
                "authorized decisions select at least one template",
                "every generated field has exactly one owner",
                "unsafe many-candidate sets never compose",
                "one request identity has one receipt fingerprint",
            ),
            known_bad_cases=(
                "broken_ambiguous_many_authorized",
                "broken_no_base_blank_authorized",
                "broken_field_collision_composed",
                "broken_repeat_changes_receipt",
            ),
            template_no_match_reason="No public or local FlowGuard risk template matched this target-specific selection instance.",
            blindspots=(
                "production manifest parsing and artifact rendering require focused conformance tests",
                "project-level FlowGuard adoption remains separately blocked",
            ),
        ),
        confidence_goal="model_level",
        skipped_checks=(
            SkippedCheck(
                "production_conformance_replay",
                "the production adapter and focused tests are implemented after this pre-code model",
            ),
        ),
    )


def invariants() -> tuple[Invariant, ...]:
    return (
        Invariant("blocked_never_authorizes", "ambiguous decisions cannot instantiate", blocked_never_authorizes),
        Invariant("success_has_selection", "authorization requires at least one selected template", success_has_selection),
        Invariant("one_field_owner", "each generated field has one owner", every_field_has_one_owner),
        Invariant("unsafe_many_never_composes", "incompatible/colliding candidates cannot compose", unsafe_many_never_composes),
        Invariant("one_receipt_per_request", "one request identity has one receipt identity", one_receipt_per_request_identity),
    )


def external_inputs() -> tuple[SelectionInput, ...]:
    return (
        SelectionInput("zero-with-base", 0, has_base=True),
        SelectionInput("zero-no-base", 0, has_base=False),
        SelectionInput("single", 1),
        SelectionInput("compose", 2, pairwise_compatible=True),
        SelectionInput("incompatible", 2, pairwise_compatible=False),
        SelectionInput("collision", 2, pairwise_compatible=True, field_collision=True),
        SelectionInput("dominance", 2, has_strict_dominator=True),
        SelectionInput("repeat-stability", 1),
    )


def known_bad_proofs() -> tuple[KnownBadProof, ...]:
    return (
        KnownBadProof(
            "broken_ambiguous_many_authorized",
            protected_error_class="ambiguous_selection_authorized",
            method="broken_workflow_variant",
            observed_status="failed",
            observed_failure="incompatible-candidate trace violates unsafe_many_never_composes",
            evidence_id="physicsguard-template-pack:model-known-bad:ambiguous",
        ),
        KnownBadProof(
            "broken_no_base_blank_authorized",
            protected_error_class="blank_fallback_authorized",
            method="broken_workflow_variant",
            observed_status="failed",
            observed_failure="zero-no-base trace violates success_has_selection",
            evidence_id="physicsguard-template-pack:model-known-bad:no-base",
        ),
        KnownBadProof(
            "broken_field_collision_composed",
            protected_error_class="field_owner_collision_accepted",
            method="broken_workflow_variant",
            observed_status="failed",
            observed_failure="field-collision trace violates one_field_owner",
            evidence_id="physicsguard-template-pack:model-known-bad:field-collision",
        ),
        KnownBadProof(
            "broken_repeat_changes_receipt",
            protected_error_class="nondeterministic_selection_receipt",
            method="broken_workflow_variant",
            observed_status="failed",
            observed_failure="repeated-input trace violates one_receipt_per_request",
            evidence_id="physicsguard-template-pack:model-known-bad:receipt",
        ),
    )


def build_check_plan(*, broken: bool = False) -> FlowGuardCheckPlan:
    block = BrokenResolveTemplateCandidates() if broken else ResolveTemplateCandidates()
    return FlowGuardCheckPlan(
        workflow=Workflow((block,), name="physicsguard_purpose_template_pack_selection"),
        initial_states=(State(),),
        external_inputs=external_inputs(),
        invariants=invariants(),
        max_sequence_length=2,
        risk_profile=risk_profile(),
        template_reuse_review=TemplateReuseReview(
            used_template_ids=(),
            no_match_reason="No matching public or local risk template was found for this PhysicsGuard-specific instance.",
            searched_layers=("public", "local"),
            match_template_ids=(),
        ),
        template_harvest_review=TemplateHarvestReview(
            disposition="not_harvestable",
            not_harvestable_reason="not_reusable_project_specific",
            metadata={
                "rationale": "The target-neutral pattern is owned by the wider Guard program; this model binds PhysicsGuard semantics only.",
            },
        ),
        minimum_model_contract=MinimumModelContract(
            protected_error_classes=PROTECTED_ERRORS,
            modeled_state=(
                "selection receipts",
                "decision disposition",
                "selected template ids",
                "field-owner map",
                "instance authorization",
            ),
            modeled_side_effects=("immutable selection receipt write",),
            completion_evidence=(
                "one finite decision",
                "stable request-bound receipt fingerprint",
            ),
            known_bad_cases=tuple(proof.case_id for proof in known_bad_proofs()),
        ),
        known_bad_proofs=known_bad_proofs(),
        metadata={
            "model_instance_id": "physicsguard-purpose-template-pack-selection-v1",
            "native_good_case_id": "compose-compatible-disjoint-fragments",
            "native_oracle_ids": (
                "oracle:finite-disposition",
                "oracle:one-field-owner",
                "oracle:request-bound-receipt",
            ),
            "candidate_fingerprint": "openspec:add-physicsguard-purpose-pack-builder@model-v1",
            "claim_boundary": "finite abstract selector only; production parser/rendering and project adoption remain separate evidence",
        },
    )


def run_checks():
    return (
        run_model_first_checks(build_check_plan()),
        run_model_first_checks(build_check_plan(broken=True)),
    )
