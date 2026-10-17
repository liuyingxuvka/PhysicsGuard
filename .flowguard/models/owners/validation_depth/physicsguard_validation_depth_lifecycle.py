"""Native dataset/mapping/time/split/adequacy/predictive field relationships."""

from __future__ import annotations

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



def build_field_lifecycle_plan() -> FieldLifecyclePlan:
    evidence_refs = (
        "gate:physicsguard_validation_depth",
        "test:tests/test_validation_depth_receipts.py",
        "test:tests/test_validation_adequacy.py",
        "test:tests/test_predictive_rollout_validation.py",
        "replay:.flowguard/verification/owners/validation_depth/run_checks.py",
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




__all__ = ["build_field_lifecycle_plan"]
