from __future__ import annotations

from dataclasses import dataclass

from flowguard import (
    BoundedEventuallyProperty,
    ConformanceReport,
    FlowGuardCheckPlan,
    FunctionContract,
    KnownBadProof,
    MinimumModelContract,
    ProgressCheckConfig,
    ReplayObservation,
    RiskIntent,
    RiskProfile,
    Scenario,
    ScenarioExpectation,
    StateClosureDimension,
    StateClosurePlan,
    TemplateHarvestReview,
    TemplateReuseReview,
    run_model_first_checks,
)
from flowguard.loop import GraphEdge

import databank_workflow_model as model


@dataclass(frozen=True)
class ProgressState:
    phase: str


def progress_edge(old: ProgressState, new: ProgressState, label: str) -> GraphEdge:
    return GraphEdge(old_state=old, new_state=new, label=label)


def progress_transition(state: ProgressState) -> tuple[GraphEdge, ...]:
    if state.phase == "start":
        return (progress_edge(state, ProgressState("root_checked"), "check_root"),)
    if state.phase == "root_checked":
        return (progress_edge(state, ProgressState("provider_checked"), "check_provider"),)
    if state.phase == "provider_checked":
        return (progress_edge(state, ProgressState("audit_complete"), "aggregate_audit"),)
    return ()


def build_progress_config() -> ProgressCheckConfig:
    return ProgressCheckConfig(
        initial_states=(ProgressState("start"),),
        transition_fn=progress_transition,
        is_terminal=lambda state: state.phase == "audit_complete",
        is_success=lambda state: state.phase == "audit_complete",
        bounded_eventually=(
            BoundedEventuallyProperty(
                name="audit_complete_within_three_steps",
                description="DataBank audit reaches aggregation after root and provider checks.",
                trigger=lambda state: state.phase == "start",
                target=lambda state: state.phase == "audit_complete",
                max_steps=3,
            ),
        ),
    )


def build_scenarios(workflow) -> tuple[Scenario, ...]:
    return (
        Scenario(
            name="root_provider_catalog_pass",
            description="A ready root and current provider can support a broad catalog claim.",
            initial_state=model.initial_state(),
            external_input_sequence=(
                model.RootCheckInput(True),
                model.ProviderResultInput("physicsguard", "pass"),
                model.CatalogClaimInput("project", "active_validated"),
            ),
            expected=ScenarioExpectation(
                expected_status="ok",
                required_trace_labels=("root_pass", "provider_pass", "allowed_broad_claim"),
                forbidden_trace_labels=("downgraded_catalog_claim",),
            ),
            workflow=workflow,
            invariants=model.INVARIANTS,
        ),
        Scenario(
            name="blocked_provider_downgrades_catalog",
            description="Blocked provider evidence downgrades broad catalog claims.",
            initial_state=model.initial_state(),
            external_input_sequence=(
                model.RootCheckInput(True),
                model.ProviderResultInput("physicsguard", "blocked", has_missing=True),
                model.CatalogClaimInput("project", "active_validated"),
            ),
            expected=ScenarioExpectation(
                expected_status="ok",
                required_trace_labels=("root_pass", "provider_blocked", "downgraded_catalog_claim"),
                forbidden_trace_labels=("allowed_broad_claim",),
            ),
            workflow=workflow,
            invariants=model.INVARIANTS,
        ),
        Scenario(
            name="lifecycle_validated_requires_closure",
            description="Lifecycle broad promotion is blocked when closure has not passed.",
            initial_state=model.initial_state(),
            external_input_sequence=(model.LifecycleRequestInput("project", "active_validated", apply=True),),
            expected=ScenarioExpectation(
                expected_status="ok",
                required_trace_labels=("blocked_lifecycle_promotion",),
                forbidden_trace_labels=("applied_lifecycle_transition",),
            ),
            workflow=workflow,
            invariants=model.INVARIANTS,
        ),
    )


def build_contracts() -> tuple[FunctionContract, ...]:
    return (
        FunctionContract(
            function_name="ApplyDataBankWorkflowEvent",
            accepted_input_type=model.DataBankEvent,
            output_type=model.DataBankDecision,
            reads=("root_ready", "provider_statuses", "closure_status", "allowed_broad_claims", "lifecycle_states"),
            writes=(
                "root_ready",
                "provider_statuses",
                "closure_status",
                "allowed_broad_claims",
                "lifecycle_states",
                "history_events",
                "downgrade_events",
            ),
            forbidden_writes=("raw_data_copy",),
            idempotency_rule="Repeated blocked provider/root inputs keep closure blocked and cannot upgrade broad claims.",
            traceability_rule="Every decision traces to root, provider, catalog, or lifecycle input.",
            failure_modes=("catalog_masks_blocked_closure", "lifecycle_promotes_without_closure"),
        ),
    )


def build_state_closure_plan() -> StateClosurePlan:
    return StateClosurePlan(
        plan_id="databank_workflow_state",
        dimensions=(
            StateClosureDimension("root_ready", "bool", policy="closed_enumeration", known_values=(False, True), representative_unknowns=(), handling="block_before_side_effect", side_effects_before_resolution=False),
            StateClosureDimension("closure_status", "enum", policy="closed_enumeration", known_values=("unknown", "pass", "blocked"), representative_unknowns=(), handling="block_before_side_effect", side_effects_before_resolution=False),
            StateClosureDimension("lifecycle_state", "enum", policy="closed_enumeration", known_values=("candidate", "active_registered", "active_validated", "active_reusable", "blocked"), representative_unknowns=("custom_state",), handling="block_before_side_effect", side_effects_before_resolution=False),
        ),
        claim_scope="bounded_databank_workflow",
        allow_scoped_confidence=True,
        notes="DataBank workflow states are finite for root/provider/catalog/lifecycle closure checks.",
    )


def build_conformance_report() -> ConformanceReport:
    return ConformanceReport(
        ok=True,
        replayed_steps=(
            ReplayObservation(
                function_name="databank_audit.py",
                observed_output="pass",
                observed_state="fixture root with source contract, provider closure, navigation, and query",
                label="audit_fixture_pass",
            ),
            ReplayObservation(
                function_name="databank_lifecycle.py",
                observed_output="blocked",
                observed_state="active_validated requested without closure",
                label="blocked_lifecycle_promotion",
            ),
            ReplayObservation(
                function_name="databank_provider_adapter.py",
                observed_output="blocked",
                observed_state="provider report includes blocking gaps",
                label="provider_blocked",
            ),
        ),
        summary="Runtime DataBank tests cover fixture audit, lifecycle gate, provider gaps, freshness, closure, navigation, query, and routing cleanup.",
    )


def build_plan(workflow, *, known_bad_proofs=(), include_review_extras: bool = True) -> FlowGuardCheckPlan:
    return FlowGuardCheckPlan(
        workflow=workflow,
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        required_labels=("root_pass", "provider_blocked", "downgraded_catalog_claim", "blocked_lifecycle_promotion", "allowed_broad_claim"),
        scenarios=build_scenarios(workflow) if include_review_extras else (),
        contracts=build_contracts() if include_review_extras else (),
        progress_config=build_progress_config() if include_review_extras else None,
        conformance_status="passed" if include_review_extras else None,
        conformance_report=build_conformance_report() if include_review_extras else None,
        state_closure_plan=build_state_closure_plan() if include_review_extras else None,
        risk_profile=RiskProfile(
            modeled_boundary="DataBank root/provider/catalog/lifecycle audit closure",
            risk_classes=("freshness", "claim_boundary", "lifecycle_consistency", "catalog_consistency"),
            risk_intent=RiskIntent(
                failure_modes=(
                    "catalog masks blocked provider closure",
                    "lifecycle promotes validated without closure",
                    "root missing but audit still passes",
                ),
                protected_error_classes=("stale_evidence_claim", "unsafe_reuse_claim", "lifecycle_overclaim"),
                protected_harms=("future agents trust a database status that lower-level proof no longer supports",),
                must_model_state=("root_ready", "provider_statuses", "closure_status", "allowed_broad_claims", "lifecycle_states"),
                must_model_side_effects=("catalog_claim_decision", "history_event"),
                completion_evidence=("downgrade_events", "history_events", "allowed_broad_claims"),
                adversarial_inputs=("blocked provider result", "validated catalog claim", "validated lifecycle request without closure"),
                hard_invariants=(
                    "broad claims cannot pass without current closure",
                    "validated/reusable lifecycle state requires passing closure",
                ),
                known_bad_cases=("lifecycle_promotes_without_closure",),
                used_template_ids=("side_effect_at_most_once",),
                blindspots=("real provider semantic proof remains provider-owned",),
            ),
            confidence_goal="model_level",
        ),
        template_reuse_review=TemplateReuseReview(
            used_template_ids=("side_effect_at_most_once",),
            searched_layers=("public", "local"),
        ),
        minimum_model_contract=MinimumModelContract(
            protected_error_classes=("stale_evidence_claim", "unsafe_reuse_claim", "lifecycle_overclaim"),
            modeled_state=("root_ready", "provider_statuses", "closure_status", "allowed_broad_claims", "lifecycle_states"),
            modeled_side_effects=("catalog_claim_decision", "history_event"),
            completion_evidence=("downgrade_events", "history_events", "allowed_broad_claims"),
            known_bad_cases=("lifecycle_promotes_without_closure",),
        ),
        known_bad_proofs=known_bad_proofs,
        template_harvest_review=TemplateHarvestReview(
            disposition="not_harvestable",
            not_harvestable_reason="not_reusable_project_specific",
        ),
        scenario_matrix_config={"enabled": False},
    )


def known_bad_proof_from_summary(summary) -> KnownBadProof:
    sections = {section.name: section for section in summary.sections}
    caught = sections["model_check"].status == "failed"
    return KnownBadProof(
        "lifecycle_promotes_without_closure",
        protected_error_class="lifecycle_overclaim",
        method="broken_workflow_variant",
        expected_failure="failed",
        observed_status="failed" if caught else "passed",
        observed_failure=(
            "broken workflow promoted active_validated without root/provider closure"
            if caught
            else "broken workflow unexpectedly passed"
        ),
        evidence_id="databank-workflow:lifecycle-without-closure",
    )


def main() -> int:
    broken_summary = run_model_first_checks(build_plan(model.broken_workflow(), include_review_extras=False))
    proof = known_bad_proof_from_summary(broken_summary)
    report = run_model_first_checks(build_plan(model.build_workflow(), known_bad_proofs=(proof,)))
    sections = {section.name: section for section in report.sections}
    print(report.format_text())
    print(f"known_bad_lifecycle_without_closure_rejected: {'yes' if proof.observed_status == 'failed' else 'no'}")
    model_report = dict(report.metadata)["model_check_report"]
    labels = sorted({label for trace in model_report.traces for label in trace.labels})
    print("labels: " + ",".join(labels))
    expected_labels = {
        "root_pass",
        "provider_blocked",
        "downgraded_catalog_claim",
        "blocked_lifecycle_promotion",
        "allowed_broad_claim",
    }
    return 0 if (
        sections["model_check"].status == "pass"
        and sections["known_bad_proof"].status == "pass"
        and proof.observed_status == "failed"
        and expected_labels.issubset(labels)
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
