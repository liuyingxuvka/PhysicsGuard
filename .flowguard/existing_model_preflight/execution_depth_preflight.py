"""Full existing-model preflight for PhysicsGuard validation depth."""

from flowguard import ExistingModelPreflight, ExistingOwnershipSnapshot, ModelContextHit, REUSE_DECISION_EXTEND_EXISTING, review_existing_model_preflight


def build_preflight() -> ExistingModelPreflight:
    validation = ModelContextHit(
        "physicsguard-model-dataset-validation",
        model_path=".flowguard/physicsguard_model_dataset_validation_model.py",
        evidence_id="filesystem-current-prechange",
        responsibilities=(
            "contract gate",
            "direct validation",
            "bounded calibration",
            "holdout gate",
            "quantitative validation adequacy",
            "stateful predictive rollout gate",
        ),
        function_blocks=("CheckContracts", "RunDirectValidation", "OptionalCalibration", "GateValidationClaim"),
        state_owned=(
            "contracts_ready",
            "depth_inputs_ready",
            "adequacy_passed",
            "predictive_rollout_passed",
            "direct_validation_ran",
            "holdout_passed",
            "validation_passed",
        ),
        fields_owned=(
            "contracts_passed",
            "coverage_universe",
            "temporal_adequacy",
            "per_signal_adequacy",
            "parameter_temporal_classification",
            "per_parameter_adequacy",
            "parameter_availability_denominator",
            "parameter_stage_coverage",
            "representative_parameter_evidence",
            "sampling_selection_policy",
            "model_semantics",
            "predictive_rollout_receipt",
            "covered_scope",
            "holdout_passed",
            "confidence_feedback_recorded",
        ),
        side_effects_owned=("issue validation status",),
        public_entrypoints=("physicsguard model-dataset validation",),
    )
    registry = ModelContextHit(
        "physicsguard-project-evidence-registry",
        model_path=".flowguard/physicsguard_project_evidence_registry_model.py",
        evidence_id="filesystem-current-prechange",
        responsibilities=("dataset and evidence identity", "coverage-universe authority"),
        function_blocks=("RegisterEvidence", "ScanEvidenceGaps"),
        state_owned=("evidence_registry",),
        fields_owned=("evidence_id", "file_map", "binding_expectations", "critical_members", "family_membership"),
    )
    suite = ModelContextHit(
        "physicsguard.guard-family.family-baseline-regression.current",
        model_path=".flowguard/physicsguard_skill_suite_mesh.json",
        evidence_id="filesystem-current-prechange",
        responsibilities=(
            "PhysicsGuard-owned family baseline regression proof",
            "target-native execution identity",
            "declared-check binding before closure",
        ),
        function_blocks=(
            "FreezePreventedFailureContract",
            "BindCandidate",
            "ProveKnownGood",
            "ProveEveryKnownBad",
            "IssueNativeReceipt",
        ),
        state_owned=("native_integration_admission",),
        fields_owned=(
            "integration_mode",
            "native_route_owner",
            "default_route_id",
            "native_route_bindings",
            "native_check_bindings",
            "depth_profile",
            "may_define_parallel_execution_route",
            "may_define_skillguard_runtime_route",
        ),
        side_effects_owned=("issue family baseline regression receipt",),
        public_entrypoints=("PhysicsGuard skill suite family baseline route",),
    )
    return ExistingModelPreflight(
        "physicsguard-validation-depth-preflight",
        "Extend PhysicsGuard model-dataset validation with target-owned quantitative adequacy and stateful future-rollout receipts",
        mode="full",
        model_search_performed=True,
        search_paths=("physicsguard", ".flowguard", "skill", "openspec/changes"),
        relevant_models=(validation, registry, suite),
        ownership_snapshot=ExistingOwnershipSnapshot(
            function_block_owners=(("CheckContracts", validation.model_id), ("RunDirectValidation", validation.model_id), ("GateValidationClaim", validation.model_id), ("RegisterEvidence", registry.model_id)),
            state_owners=(("validation_passed", validation.model_id), ("adequacy_passed", validation.model_id), ("predictive_rollout_passed", validation.model_id), ("holdout_passed", validation.model_id), ("evidence_registry", registry.model_id), ("native_integration_admission", suite.model_id)),
            field_owners=(("dataset_receipt", registry.model_id), ("mapping_receipt", registry.model_id), ("coverage_universe", registry.model_id), ("time_scenario_receipt", validation.model_id), ("adequacy_receipt", validation.model_id), ("parameter_availability_denominator", validation.model_id), ("parameter_stage_coverage", validation.model_id), ("representative_parameter_evidence", validation.model_id), ("sampling_selection_policy", validation.model_id), ("predictive_rollout_receipt", validation.model_id), ("covered_scope", validation.model_id), ("depth_receipt", validation.model_id), *((field_id, suite.model_id) for field_id in suite.fields_owned)),
            side_effect_owners=(("issue validation status", validation.model_id), ("issue family baseline regression receipt", suite.model_id)),
            public_entrypoint_owners=(("physicsguard model-dataset validation", validation.model_id), ("PhysicsGuard skill suite family baseline route", suite.model_id)),
            responsibility_owners=(("direct validation", validation.model_id), ("quantitative validation adequacy", validation.model_id), ("stateful predictive rollout gate", validation.model_id), ("dataset and evidence identity", registry.model_id), ("coverage-universe authority", registry.model_id), ("PhysicsGuard-owned family baseline regression proof", suite.model_id), ("target-native execution identity", suite.model_id), ("declared-check binding before closure", suite.model_id)),
        ),
        reuse_decision=REUSE_DECISION_EXTEND_EXISTING,
        downstream_routes=("field_lifecycle_mesh", "development_process_flow", "model_test_alignment", "test_mesh_maintenance"),
        behavior_field_ids=("dataset_receipt", "mapping_receipt", "coverage_universe", "time_window_receipt", "scenario_receipt", "split_receipt", "sampling_selection_policy", "parameter_temporal_classification", "parameter_availability_denominator", "parameter_stage_coverage", "representative_parameter_evidence", "per_parameter_adequacy", "adequacy_receipt", "model_semantics", "predictive_rollout_receipt", "covered_scope", "depth_receipt", *suite.fields_owned),
        field_lifecycle_required=True,
        field_lifecycle_model_ids=(validation.model_id, registry.model_id, suite.model_id),
        rationale="Extend existing validation, evidence-registry, and family-baseline owners; target-local current model purpose is governed separately, while SkillGuard supervises receipts without recomputing target-owned adequacy, prediction, physics, or route identity.",
    )


if __name__ == "__main__":
    report = review_existing_model_preflight(build_preflight())
    print(report.format_text(max_findings=20))
    raise SystemExit(0 if report.ok else 1)
