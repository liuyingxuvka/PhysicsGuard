"""Existing-model preflight for PhysicsGuard dynamic model-purpose closure."""

from flowguard import (
    ExistingModelPreflight,
    ExistingOwnershipSnapshot,
    ModelContextHit,
    REUSE_DECISION_EXTEND_EXISTING,
    review_existing_model_preflight,
)


def build_preflight() -> ExistingModelPreflight:
    current = ModelContextHit(
        "physicsguard.current-model-purpose-closure.current",
        model_path=".flowguard/models/owners/dynamic_model_purpose/physicsguard_dynamic_model_purpose_model.py",
        evidence_id="filesystem-current-dynamic-purpose-upgrade",
        responsibilities=(
            "AI-selected current modeling purpose",
            "target-local prevented failure universe",
            "actual candidate artifact binding",
            "PhysicsGuard-native current good/bad proof exhaustion",
        ),
        function_blocks=(
            "FreezeCurrentPurpose",
            "BindCandidate",
            "ProveKnownGood",
            "ProveEveryKnownBad",
            "IssueCurrentModelReceipt",
        ),
        state_owned=(
            "purposes_frozen",
            "candidates_bound",
            "good_proofs_passed",
            "bad_proofs_exhausted",
            "closed",
        ),
        fields_owned=(
            "artifact_role:current_model_purpose",
            "prevented_failure_purpose",
            "prevented_failure_classes",
            "physical_or_evidence_boundary",
            "purpose_contract_fingerprint",
            "candidate_artifact_fingerprint",
            "native_oracle_results",
        ),
        side_effects_owned=("issue current model-purpose receipt",),
        public_entrypoints=("PhysicsGuard current model-purpose verifier",),
    )
    return ExistingModelPreflight(
        "physicsguard-dynamic-model-purpose-preflight",
        "Maintain the target-local current purpose, candidate, and failure-case proof owner",
        mode="full",
        model_search_performed=True,
        search_paths=(".flowguard", "src/physicsguard", "skill", "tests", "openspec/changes"),
        relevant_models=(current,),
        ownership_snapshot=ExistingOwnershipSnapshot(
            function_block_owners=tuple(
                (name, current.model_id) for name in current.function_blocks
            ),
            state_owners=tuple((name, current.model_id) for name in current.state_owned),
            field_owners=tuple((name, current.model_id) for name in current.fields_owned),
            side_effect_owners=(
                ("issue current model-purpose receipt", current.model_id),
            ),
            public_entrypoint_owners=(
                ("PhysicsGuard current model-purpose verifier", current.model_id),
            ),
            responsibility_owners=tuple(
                (name, current.model_id) for name in current.responsibilities
            ),
        ),
        reuse_decision=REUSE_DECISION_EXTEND_EXISTING,
        downstream_routes=(
            "field_lifecycle_mesh",
            "development_process_flow",
            "model_test_alignment",
            "test_mesh_maintenance",
        ),
        behavior_field_ids=tuple(current.fields_owned),
        field_lifecycle_required=True,
        field_lifecycle_model_ids=(current.model_id,),
        rationale=("Reuse the current target-owned purpose/candidate/oracle authority; native tests cover shared runtime behavior once."),
    )


if __name__ == "__main__":
    report = review_existing_model_preflight(build_preflight())
    print(report.format_text(max_findings=20))
    raise SystemExit(0 if report.ok else 1)
