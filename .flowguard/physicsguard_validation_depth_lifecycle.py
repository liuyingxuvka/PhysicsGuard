"""FieldLifecycleMesh and DevelopmentProcessFlow plans for validation depth."""

from __future__ import annotations

from flowguard.development_process_flow import (
    DevelopmentProcessPlan,
    FreshnessRule,
    ProcessAction,
    ProcessArtifact,
    ProcessEvidence,
    ValidationRequirement,
    review_development_process_flow,
)
from flowguard.field_lifecycle import (
    FIELD_DISPOSITION_SAME_CONTRACT_REPAIRED,
    FIELD_IMPACT_EXTERNAL_CONTRACT,
    FIELD_IMPACT_REPLAY,
    FIELD_IMPACT_SCHEMA,
    FIELD_IMPACT_STATE,
    FIELD_LIFECYCLE_NEW,
    FIELD_ROLE_METADATA,
    FIELD_ROLE_STATE,
    TEST_KIND_FAILURE_PATH,
    TEST_KIND_HAPPY_PATH,
    TEST_KIND_REPLAY,
    FieldLifecycleGroup,
    FieldLifecyclePlan,
    FieldLifecycleRow,
    FieldProjection,
    review_field_lifecycle,
)
from flowguard.model_test_alignment import (
    CodeContract,
    ModelObligation,
    ModelTestAlignmentPlan,
    TestEvidence,
    review_model_test_alignment,
)
from flowguard.testmesh import (
    TestMeshPlan,
    TestPartitionItem,
    TestSuiteEvidence,
    TestTargetSplitDerivation,
    review_test_mesh,
)


FIELD_IDS = (
    "dataset_identity",
    "mapping_review",
    "observed_series",
    "time_scope",
    "scenario_definitions",
    "calibration_split",
    "residual_series",
    "envelope_evidence",
    "report_identity",
    "depth_receipt",
    "validation_universe",
    "sampling_selection_policy",
    "temporal_signal_adequacy",
    "parameter_availability_denominator",
    "parameter_temporal_class",
    "parameter_temporal_adequacy",
    "parameter_stage_coverage",
    "dynamic_coverage_floor",
    "representative_parameter_evidence",
    "parameter_model_contribution",
    "predictive_rollout",
    "requested_covered_scope",
)

NATIVE_INTEGRATION_FIELD_IDS = (
    "integration_mode",
    "native_route_owner",
    "default_route_id",
    "native_route_bindings",
    "native_check_bindings",
    "depth_profile",
    "may_define_parallel_execution_route",
    "may_define_skillguard_runtime_route",
)


def build_field_lifecycle_plan() -> FieldLifecyclePlan:
    evidence_refs = (
        "gate:physicsguard_validation_depth",
        "test:tests/test_validation_depth_receipts.py",
        "test:tests/test_validation_adequacy.py",
        "test:tests/test_predictive_rollout_validation.py",
        "replay:.flowguard/run_physicsguard_validation_depth_checks.py",
    )
    locations = {
        "dataset_identity": ("src/physicsguard/schema/validation_depth.py::DatasetIdentityPlanSpec",),
        "mapping_review": ("src/physicsguard/schema/validation_depth.py::MappingReviewPlanSpec",),
        "observed_series": ("src/physicsguard/schema/validation_depth.py::ObservedSeriesSpec",),
        "time_scope": ("src/physicsguard/schema/validation_depth.py::TimeScopePlanSpec",),
        "scenario_definitions": ("src/physicsguard/schema/validation_depth.py::ScenarioDefinitionSpec",),
        "calibration_split": ("src/physicsguard/schema/validation_depth.py::CalibrationSplitPlanSpec",),
        "residual_series": ("src/physicsguard/schema/validation_depth.py::ResidualSeriesReceiptSpec",),
        "envelope_evidence": ("src/physicsguard/schema/validation_depth.py::EnvelopeEvidenceReceiptSpec",),
        "report_identity": ("src/physicsguard/schema/validation_depth.py::ReportIdentityReceiptSpec",),
        "depth_receipt": ("src/physicsguard/schema/validation_depth.py::ValidationDepthReceiptSpec",),
        "validation_universe": ("src/physicsguard/schema/validation_adequacy.py::ValidationUniverseReceiptSpec",),
        "sampling_selection_policy": ("src/physicsguard/schema/validation_adequacy.py::ValidationAdequacyPlanSpec",),
        "temporal_signal_adequacy": ("src/physicsguard/schema/validation_adequacy.py::ValidationAdequacyReceiptSpec",),
        "parameter_availability_denominator": ("src/physicsguard/schema/validation_adequacy.py::ParameterTemporalPolicySpec",),
        "parameter_temporal_class": ("src/physicsguard/schema/validation_adequacy.py::ParameterTemporalPolicySpec",),
        "parameter_temporal_adequacy": ("src/physicsguard/schema/validation_adequacy.py::PerParameterCoverageReceiptSpec",),
        "parameter_stage_coverage": ("src/physicsguard/schema/validation_adequacy.py::ParameterTimeStratumSpec",),
        "dynamic_coverage_floor": ("src/physicsguard/schema/validation_adequacy.py::CoverageFloorReceiptSpec",),
        "representative_parameter_evidence": ("src/physicsguard/schema/validation_adequacy.py::PerParameterCoverageReceiptSpec",),
        "parameter_model_contribution": ("src/physicsguard/schema/validation_depth.py::ParameterContributionReceiptSpec",),
        "predictive_rollout": ("src/physicsguard/schema/predictive_rollout.py::PredictiveRolloutReceiptSpec",),
        "requested_covered_scope": ("src/physicsguard/core/project_closure.py::_consume_validation_depth_receipt",),
    }
    rows = []
    for field_id in FIELD_IDS:
        output_id = "depth_receipt" if field_id != "depth_receipt" else "closure_consumable_receipt"
        rows.append(
            FieldLifecycleRow(
                field_id=field_id,
                locations=locations[field_id],
                group_id="validation_depth_contract",
                role=FIELD_ROLE_STATE if field_id in {"time_scope", "scenario_definitions", "calibration_split"} else FIELD_ROLE_METADATA,
                lifecycle=FIELD_LIFECYCLE_NEW,
                behavior_impacts=(
                    FIELD_IMPACT_SCHEMA,
                    FIELD_IMPACT_EXTERNAL_CONTRACT,
                    FIELD_IMPACT_STATE,
                    FIELD_IMPACT_REPLAY,
                ),
                reader_ids=("physicsguard.core.validation_depth", "physicsguard.core.project_closure"),
                writer_ids=("physicsguard.core.model_dataset_validation",),
                disposition=FIELD_DISPOSITION_SAME_CONTRACT_REPAIRED,
                disposition_evidence_refs=evidence_refs,
                projection=FieldProjection(
                    projection_id=f"project_{field_id}",
                    field_id=field_id,
                    model_obligation_id=f"validation_depth.{field_id}",
                    transition_cell_id=f"depth_cell.{field_id}",
                    code_contract_id=f"code.validation_depth.{field_id}",
                    required_test_kinds=(
                        TEST_KIND_HAPPY_PATH,
                        TEST_KIND_FAILURE_PATH,
                        TEST_KIND_REPLAY,
                    ),
                    external_inputs=(field_id,),
                    external_outputs=(output_id,),
                    state_reads=(field_id,),
                    state_writes=("validation_depth_status",),
                    error_paths=(f"{field_id}_missing_or_stale",),
                    risk_level="high",
                    evidence_refs=evidence_refs,
                    rationale=(
                        f"{field_id} changes the externally consumable validation claim and must "
                        "project to model, code, negative-test, and replay obligations"
                    ),
                ),
            )
        )
    return FieldLifecyclePlan(
        mesh_id="physicsguard_validation_depth_fields",
        discovered_field_ids=FIELD_IDS,
        groups=(
            FieldLifecycleGroup(
                group_id="validation_depth_contract",
                boundary_kind="schema_and_report_contract",
                field_ids=FIELD_IDS,
                owner_route="model_first_function_flow",
                evidence_refs=evidence_refs,
                rationale="Existing model-dataset validation owns the depth extension and closure receipt.",
            ),
        ),
        fields=tuple(rows),
        claim_scope="full",
        allow_scoped_confidence=False,
        notes="No old public field was replaced; the optional depth block preserves scalar compatibility while narrowing its claim.",
    )


def build_native_integration_field_lifecycle_plan() -> FieldLifecyclePlan:
    """Model the target-owned identity projected into generic SkillGuard supervision."""

    evidence_refs = (
        "gate:physicsguard_native_integration_identity",
        "generator:scripts/upgrade_purpose_contracts.py",
        "model:.flowguard/physicsguard_skill_suite_mesh.json",
        "test:tests/test_guard_model_contract.py",
        "test:tests/test_skill_execution_depth.py",
        "audit:tests/test_skillguard_v2_runtime_authority_audit.py",
        "replay:.flowguard/check_physicsguard_skill_suite_mesh.py",
    )
    error_paths = {
        "integration_mode": "native_integration_mode_missing_or_wrong",
        "native_route_owner": "native_route_owner_missing_or_wrong",
        "default_route_id": "default_route_missing_or_wrong",
        "native_route_bindings": "native_route_binding_missing_or_wrong",
        "native_check_bindings": "declared_check_binding_missing_or_wrong",
        "depth_profile": "compiled_depth_profile_missing_or_inconsistent",
        "may_define_parallel_execution_route": "parallel_execution_route_allowed",
        "may_define_skillguard_runtime_route": "skillguard_runtime_route_allowed",
    }
    rows = tuple(
        FieldLifecycleRow(
            field_id=field_id,
            locations=(
                "scripts/upgrade_purpose_contracts.py::upgrade_target_current",
                "skill/*/.skillguard/contract-source.json",
            ),
            group_id="native_integration_identity",
            role=FIELD_ROLE_METADATA,
            lifecycle=FIELD_LIFECYCLE_NEW,
            behavior_impacts=(
                FIELD_IMPACT_SCHEMA,
                FIELD_IMPACT_EXTERNAL_CONTRACT,
                FIELD_IMPACT_REPLAY,
            ),
            reader_ids=(
                "skillguard.compiler",
                "skillguard.global_router_projection",
                "physicsguard.skill_suite_mesh",
            ),
            writer_ids=("physicsguard.upgrade_purpose_contracts",),
            disposition=FIELD_DISPOSITION_SAME_CONTRACT_REPAIRED,
            disposition_evidence_refs=evidence_refs,
            projection=FieldProjection(
                projection_id=f"project_native_integration_{field_id}",
                field_id=field_id,
                model_obligation_id=f"native_integration.{field_id}",
                transition_cell_id=f"native_integration_cell.{field_id}",
                code_contract_id=f"code.native_integration.{field_id}",
                required_test_kinds=(
                    TEST_KIND_HAPPY_PATH,
                    TEST_KIND_FAILURE_PATH,
                    TEST_KIND_REPLAY,
                ),
                external_inputs=(field_id,),
                external_outputs=("skillguard_native_integration_projection",),
                state_reads=(field_id,),
                state_writes=("native_integration_admission",),
                error_paths=(error_paths[field_id],),
                risk_level="high",
                evidence_refs=evidence_refs,
                rationale=(
                    f"{field_id} preserves PhysicsGuard target ownership while allowing only "
                    "generic SkillGuard compilation, supervision, and projection"
                ),
            ),
        )
        for field_id in NATIVE_INTEGRATION_FIELD_IDS
    )
    return FieldLifecyclePlan(
        mesh_id="physicsguard_native_integration_identity_fields",
        discovered_field_ids=NATIVE_INTEGRATION_FIELD_IDS,
        groups=(
            FieldLifecycleGroup(
                group_id="native_integration_identity",
                boundary_kind="target_owned_supervision_identity",
                field_ids=NATIVE_INTEGRATION_FIELD_IDS,
                owner_route="physicsguard.guard-family.family-baseline-regression.current",
                evidence_refs=evidence_refs,
                rationale=(
                    "PhysicsGuard owns the family baseline route and every declared native "
                    "baseline check; SkillGuard consumes this identity without defining a "
                    "parallel route or current-model meaning."
                ),
            ),
        ),
        fields=rows,
        claim_scope="full",
        allow_scoped_confidence=False,
        notes=(
            "This is a direct current-contract repair. It does not add a selectable mode, "
            "fallback, compatibility reader, or SkillGuard-owned domain route."
        ),
    )


def build_development_process_plan() -> DevelopmentProcessPlan:
    artifacts = (
        ProcessArtifact(
            "depth_requirement",
            "requirement",
            "1",
            "openspec/changes/enforce-validation-adequacy-and-predictive-rollout",
            "OpenSpec",
        ),
        ProcessArtifact(
            "depth_field_lifecycle",
            "field_lifecycle",
            "1",
            ".flowguard/physicsguard_validation_depth_lifecycle.py",
            "field_lifecycle_mesh",
            ("depth_requirement",),
        ),
        ProcessArtifact(
            "depth_flow_model",
            "model",
            "1",
            ".flowguard/physicsguard_model_dataset_validation_model.py",
            "model_first_function_flow",
            ("depth_field_lifecycle",),
        ),
        ProcessArtifact(
            "depth_implementation",
            "code",
            "1",
            "src/physicsguard/core/validation_depth.py",
            "physicsguard-model-dataset-validation",
            ("depth_flow_model",),
        ),
        ProcessArtifact(
            "depth_tests",
            "test",
            "1",
            "tests/test_validation_adequacy.py + tests/test_predictive_rollout_validation.py",
            "pytest",
            ("depth_implementation",),
        ),
        ProcessArtifact(
            "depth_receipt_contract",
            "report",
            "1",
            "src/physicsguard/schema/validation_depth.py",
            "physicsguard-audit-closure",
            ("depth_implementation", "depth_tests"),
        ),
    )
    actions = (
        ProcessAction(
            "capture_depth_requirements",
            "plan",
            writes_artifacts=("depth_requirement",),
            description="Capture dataset/mapping/time/scenario/split/series/receipt obligations.",
        ),
        ProcessAction(
            "review_depth_fields",
            "model",
            reads_artifacts=("depth_requirement",),
            writes_artifacts=("depth_field_lifecycle",),
            produced_evidence_ids=("field_lifecycle_evidence",),
            order_after=("capture_depth_requirements",),
        ),
        ProcessAction(
            "extend_existing_validation_owner",
            "model",
            reads_artifacts=("depth_field_lifecycle",),
            writes_artifacts=("depth_flow_model",),
            order_after=("review_depth_fields",),
        ),
        ProcessAction(
            "implement_native_depth",
            "edit",
            reads_artifacts=("depth_flow_model",),
            writes_artifacts=("depth_implementation", "depth_receipt_contract", "depth_tests"),
            order_after=("extend_existing_validation_owner",),
        ),
        ProcessAction(
            "validate_native_depth",
            "validate",
            reads_artifacts=("depth_implementation", "depth_tests", "depth_receipt_contract"),
            produced_evidence_ids=("flowguard_depth_evidence", "pytest_depth_evidence"),
            order_after=("implement_native_depth",),
        ),
        ProcessAction(
            "bounded_depth_claim",
            "done",
            reads_artifacts=("depth_receipt_contract",),
            required_evidence_ids=("field_lifecycle_evidence", "flowguard_depth_evidence", "pytest_depth_evidence"),
            required_validation_ids=("validation_depth_requirement",),
            order_after=("validate_native_depth",),
            decision_scope="routine",
        ),
    )
    versions = {artifact.artifact_id: artifact.current_version for artifact in artifacts}
    evidence = (
        ProcessEvidence(
            "field_lifecycle_evidence",
            "field_lifecycle_mesh",
            "field_lifecycle_mesh",
            "passed",
            covers_artifacts=("depth_requirement", "depth_field_lifecycle"),
            covered_versions={key: versions[key] for key in ("depth_requirement", "depth_field_lifecycle")},
            produced_by_action_id="review_depth_fields",
            command="python .flowguard/run_physicsguard_validation_depth_checks.py",
            result_path="stdout:field_lifecycle",
        ),
        ProcessEvidence(
            "flowguard_depth_evidence",
            "replay",
            "model_first_function_flow",
            "passed",
            covers_artifacts=("depth_flow_model", "depth_implementation", "depth_receipt_contract"),
            covered_versions={key: versions[key] for key in ("depth_flow_model", "depth_implementation", "depth_receipt_contract")},
            validation_requirement_ids=("validation_depth_requirement",),
            produced_by_action_id="validate_native_depth",
            command="python .flowguard/run_physicsguard_validation_depth_checks.py",
            result_path="stdout:flowguard_validation_depth",
        ),
        ProcessEvidence(
            "pytest_depth_evidence",
            "test",
            "pytest",
            "passed",
            covers_artifacts=("depth_implementation", "depth_tests", "depth_receipt_contract"),
            covered_versions={key: versions[key] for key in ("depth_implementation", "depth_tests", "depth_receipt_contract")},
            validation_requirement_ids=("validation_depth_requirement",),
            produced_by_action_id="validate_native_depth",
            command="python -m pytest tests/test_validation_adequacy.py tests/test_predictive_rollout_validation.py -q",
            result_path="stdout:pytest_validation_depth",
        ),
    )
    freshness_rules = tuple(
        FreshnessRule(
            f"{artifact.artifact_id}_freshness",
            artifact.artifact_id,
            invalidates_artifact_ids=tuple(
                item.artifact_id for item in artifacts if artifact.artifact_id in item.upstream_artifact_ids
            ),
            invalidates_evidence_kinds=("field_lifecycle_mesh", "replay", "test"),
            description=f"Changes to {artifact.artifact_id} invalidate downstream depth evidence.",
        )
        for artifact in artifacts
        if any(artifact.artifact_id in item.upstream_artifact_ids for item in artifacts)
    )
    return DevelopmentProcessPlan(
        process_id="physicsguard_validation_depth_process",
        artifacts=artifacts,
        actions=actions,
        evidence=evidence,
        validation_requirements=(
            ValidationRequirement(
                "validation_depth_requirement",
                required_artifact_ids=("depth_implementation", "depth_tests", "depth_receipt_contract"),
                evidence_ids=("pytest_depth_evidence",),
                scope="routine",
                v_model_pair=True,
                command="python -m pytest tests/test_validation_adequacy.py tests/test_predictive_rollout_validation.py -q",
                description="Native depth implementation and receipt contract require current negative and receipt tests.",
            ),
        ),
        freshness_rules=freshness_rules,
        decision_scope="routine",
        require_proof_artifacts=False,
    )


def review_lifecycle_and_process():
    field_report = review_field_lifecycle(build_field_lifecycle_plan())
    process_report = review_development_process_flow(build_development_process_plan())
    return field_report, process_report


def review_native_integration_lifecycle():
    return review_field_lifecycle(build_native_integration_field_lifecycle_plan())


def build_model_test_alignment_plan() -> ModelTestAlignmentPlan:
    obligations = (
        ModelObligation(
            "validation_depth.quantitative_adequacy",
            "coverage",
            "Manifest-derived point/signal/parameter/family adequacy resolves the strictest native/project/convergence floor and rejects shallow selection.",
            required_test_kinds=("happy_path", "failure_path"),
            risk_level="high",
            external_inputs=("manifest", "role_matrix", "observed_series", "hierarchy"),
            external_outputs=("physicsguard_validation_adequacy_receipt",),
            error_paths=("shallow_points", "three_of_thousand", "shallow_signals", "duplicate_time", "missing_event", "unclassified_parameter"),
        ),
        ModelObligation(
            "validation_depth.per_parameter_adequacy",
            "coverage",
            "Every parameter is classed; static uses binding-only evidence while each time-varying parameter proves its raw denominator, resolved dynamic floor, own time/gap/stages, and executable model contribution or bounded non-sensitive disposition.",
            required_test_kinds=("happy_path", "failure_path"),
            risk_level="high",
            external_inputs=("hierarchy", "executable_model_parameters", "parameter_bindings", "manifest", "observed_series", "parameter_temporal_policies", "counterfactual_residual_replay"),
            external_outputs=("per_parameter_coverage_receipts", "parameter_contribution_receipts"),
            error_paths=("one_or_two_of_thousand", "three_of_thousand", "same_stage_only", "one_shallow_among_deep", "ten_thousand_parameters_two_bound", "static_binding_missing", "representative_direction_or_envelope_missing", "disconnected_parameter", "effectless_sensitive_parameter", "unbounded_non_sensitive_disposition"),
        ),
        ModelObligation(
            "validation_depth.predictive_rollout",
            "trajectory",
            "Only stateful disjoint future-holdout rollouts can authorize prediction.",
            required_test_kinds=("happy_path", "failure_path"),
            risk_level="high",
            external_inputs=("prediction_series", "future_holdout", "initial_state", "horizon"),
            external_outputs=("physicsguard_predictive_rollout_receipt",),
            error_paths=("pointwise_prediction", "identity_overlap", "drift", "stability"),
        ),
        ModelObligation(
            "validation_depth.claim_scope_closure",
            "closure",
            "Requested claim scope must be compatible with covered scope and semantics.",
            required_test_kinds=("failure_path",),
            risk_level="high",
            external_inputs=("requested_claim_scope", "depth_receipt"),
            external_outputs=("project_closure_decision",),
            error_paths=("snapshot_scope_incompatible", "predictive_rollout_not_pass"),
        ),
    )
    contracts = (
        CodeContract(
            "code.validation_adequacy",
            "src/physicsguard/core/validation_adequacy.py",
            "evaluate_validation_adequacy",
            implements_obligations=("validation_depth.quantitative_adequacy", "validation_depth.per_parameter_adequacy"),
            external_inputs=("manifest", "hierarchy", "executable_model_parameters", "role_matrix", "observed_series", "parameter_bindings", "parameter_temporal_policies", "counterfactual_residual_replay"),
            external_outputs=("physicsguard_validation_adequacy_receipt", "per_parameter_coverage_receipts", "parameter_contribution_receipts"),
            error_paths=("shallow_points", "three_of_thousand", "shallow_signals", "duplicate_time", "missing_event", "unclassified_parameter", "one_or_two_of_thousand", "same_stage_only", "one_shallow_among_deep", "ten_thousand_parameters_two_bound", "static_binding_missing", "representative_direction_or_envelope_missing", "disconnected_parameter", "effectless_sensitive_parameter", "unbounded_non_sensitive_disposition"),
        ),
        CodeContract(
            "code.predictive_rollout",
            "src/physicsguard/core/predictive_rollout.py",
            "evaluate_predictive_rollout",
            implements_obligations=("validation_depth.predictive_rollout",),
            external_inputs=("prediction_series", "future_holdout", "initial_state", "horizon", "model_semantics"),
            external_outputs=("physicsguard_predictive_rollout_receipt",),
            error_paths=("pointwise_prediction", "identity_overlap", "drift", "stability"),
        ),
        CodeContract(
            "code.claim_scope_closure",
            "src/physicsguard/core/project_closure.py",
            "_consume_validation_depth_receipt",
            implements_obligations=("validation_depth.claim_scope_closure",),
            external_inputs=("requested_claim_scope", "depth_receipt"),
            external_outputs=("project_closure_decision",),
            error_paths=("snapshot_scope_incompatible", "predictive_rollout_not_pass"),
        ),
    )
    evidence = (
        TestEvidence("test.adequacy.happy", "adequacy positive", "tests/test_validation_adequacy.py", "python -m pytest tests/test_validation_adequacy.py -q", "passed", True, "happy_path", ("validation_depth.quantitative_adequacy", "validation_depth.per_parameter_adequacy"), ("code.validation_adequacy",)),
        TestEvidence("test.adequacy.failure", "adequacy shallow negatives", "tests/test_validation_adequacy.py", "python -m pytest tests/test_validation_adequacy.py -q", "passed", True, "failure_path", ("validation_depth.quantitative_adequacy", "validation_depth.per_parameter_adequacy", "validation_depth.claim_scope_closure"), ("code.validation_adequacy", "code.claim_scope_closure")),
        TestEvidence("test.predictive.happy", "predictive positive", "tests/test_predictive_rollout_validation.py", "python -m pytest tests/test_predictive_rollout_validation.py -q", "passed", True, "happy_path", ("validation_depth.predictive_rollout",), ("code.predictive_rollout",)),
        TestEvidence("test.predictive.failure", "predictive negatives", "tests/test_predictive_rollout_validation.py", "python -m pytest tests/test_predictive_rollout_validation.py -q", "passed", True, "failure_path", ("validation_depth.predictive_rollout",), ("code.predictive_rollout",)),
    )
    return ModelTestAlignmentPlan(
        model_id="physicsguard_validation_adequacy_predictive_alignment",
        obligations=obligations,
        code_contracts=contracts,
        test_evidence=evidence,
    )


def build_test_mesh_plan() -> TestMeshPlan:
    partitions = (
        TestPartitionItem("adequacy", "coverage", "suite.adequacy", touched_paths=("src/physicsguard/core/validation_adequacy.py",)),
        TestPartitionItem("predictive", "trajectory", "suite.predictive", touched_paths=("src/physicsguard/core/predictive_rollout.py",)),
        TestPartitionItem("regression", "compatibility", "suite.regression", touched_paths=("src/physicsguard/core/validation_depth.py", "src/physicsguard/core/project_closure.py")),
    )
    suites = (
        TestSuiteEvidence("suite.adequacy", "python -m pytest tests/test_validation_adequacy.py -q", result_status="passed", evidence_tier="abstract_green", test_count=24, selected_count=24, exit_code=0, result_path="stdout:adequacy"),
        TestSuiteEvidence("suite.predictive", "python -m pytest tests/test_predictive_rollout_validation.py -q", result_status="passed", evidence_tier="abstract_green", test_count=6, selected_count=6, exit_code=0, result_path="stdout:predictive"),
        TestSuiteEvidence("suite.regression", "python -m pytest tests/test_validation_depth_receipts.py tests/test_model_dataset_validation.py tests/test_project_closure.py -q", result_status="passed", evidence_tier="abstract_green", test_count=31, selected_count=31, exit_code=0, result_path="stdout:regression"),
    )
    return TestMeshPlan(
        parent_suite_id="physicsguard_validation_depth_parent",
        partition_items=partitions,
        child_suites=suites,
        target_split_derivation=TestTargetSplitDerivation(
            source_model_id="physicsguard_model_dataset_validation",
            target_suite_ids=tuple(item.suite_id for item in suites),
            covered_partition_item_ids=tuple(item.item_id for item in partitions),
            source_model_path=".flowguard/physicsguard_model_dataset_validation_model.py",
            rationale="Separate quantitative adequacy, predictive trajectory, and compatibility evidence while preserving one parent claim gate.",
        ),
        required_evidence_tier="abstract_green",
    )


def review_alignment_and_test_mesh():
    return (
        review_model_test_alignment(build_model_test_alignment_plan()),
        review_test_mesh(build_test_mesh_plan()),
    )


__all__ = [
    "build_development_process_plan",
    "build_field_lifecycle_plan",
    "build_native_integration_field_lifecycle_plan",
    "review_lifecycle_and_process",
    "review_native_integration_lifecycle",
    "build_model_test_alignment_plan",
    "build_test_mesh_plan",
    "review_alignment_and_test_mesh",
]
