"""Existing-model preflight for PhysicsGuard dynamic model-purpose closure."""

from flowguard import (
    ExistingModelPreflight,
    ExistingOwnershipSnapshot,
    ModelContextHit,
    REUSE_DECISION_EXTEND_EXISTING,
    review_existing_model_preflight,
)


def build_preflight() -> ExistingModelPreflight:
    baseline = ModelContextHit(
        "physicsguard.guard-family.family-baseline-regression.current",
        model_path="skill/physicsguard-ai-debugging/.skillguard/contract_model.py",
        evidence_id="filesystem-current-dynamic-purpose-upgrade",
        responsibilities=(
            "maintained family capability regression",
            "baseline native good/bad fixture execution",
        ),
        function_blocks=(
            "ValidateFamilyBaselineContract",
            "BindFamilyBaselineCandidate",
            "ProveFamilyBaselineGood",
            "ProveFamilyBaselineBad",
        ),
        state_owned=("family_baseline_current",),
        fields_owned=("artifact_role:family_baseline_regression",),
        side_effects_owned=("issue family baseline regression receipt",),
        public_entrypoints=("PhysicsGuard maintained-skill baseline checks",),
    )
    current = ModelContextHit(
        "physicsguard.current-model-purpose-closure.current",
        model_path=".flowguard/physicsguard_dynamic_model_purpose_model.py",
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
        "Separate immutable family baseline regression from target-local, AI-declared current model-purpose authority",
        mode="full",
        model_search_performed=True,
        search_paths=(".flowguard", "src/physicsguard", "skill", "tests", "openspec/changes"),
        relevant_models=(baseline, current),
        ownership_snapshot=ExistingOwnershipSnapshot(
            function_block_owners=tuple(
                (name, current.model_id) for name in current.function_blocks
            )
            + tuple((name, baseline.model_id) for name in baseline.function_blocks),
            state_owners=tuple((name, current.model_id) for name in current.state_owned)
            + (("family_baseline_current", baseline.model_id),),
            field_owners=tuple((name, current.model_id) for name in current.fields_owned)
            + (("artifact_role:family_baseline_regression", baseline.model_id),),
            side_effect_owners=(
                ("issue family baseline regression receipt", baseline.model_id),
                ("issue current model-purpose receipt", current.model_id),
            ),
            public_entrypoint_owners=(
                ("PhysicsGuard maintained-skill baseline checks", baseline.model_id),
                ("PhysicsGuard current model-purpose verifier", current.model_id),
            ),
            responsibility_owners=tuple(
                (name, current.model_id) for name in current.responsibilities
            )
            + tuple((name, baseline.model_id) for name in baseline.responsibilities),
        ),
        reuse_decision=REUSE_DECISION_EXTEND_EXISTING,
        downstream_routes=(
            "field_lifecycle_mesh",
            "development_process_flow",
            "model_test_alignment",
            "test_mesh_maintenance",
        ),
        behavior_field_ids=tuple(current.fields_owned) + tuple(baseline.fields_owned),
        field_lifecycle_required=True,
        field_lifecycle_model_ids=(baseline.model_id, current.model_id),
        rationale=(
            "Extend the existing purpose-before-candidate proof chain by splitting its two authorities. "
            "The prior fixed suite remains the family baseline owner; the new current-model owner alone can license a concrete model. "
            "SkillGuard remains a generic declared-check and receipt supervisor."
        ),
    )


if __name__ == "__main__":
    report = review_existing_model_preflight(build_preflight())
    print(report.format_text(max_findings=20))
    raise SystemExit(0 if report.ok else 1)
