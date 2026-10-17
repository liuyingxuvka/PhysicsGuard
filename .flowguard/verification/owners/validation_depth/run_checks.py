"""Run focused FlowGuard checks for native PhysicsGuard validation depth."""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "models/owners"))


from flowguard.explorer import Explorer

from model_dataset_validation import physicsguard_model_dataset_validation_model as model
from project_evidence_registry import physicsguard_project_evidence_registry_model as evidence_model
from validation_depth import physicsguard_validation_depth_lifecycle as lifecycle




def main() -> int:
    depth_cases = {item.case_id: item for item in model.DEPTH_EXTERNAL_INPUTS}
    groups = (
        (
            "passing_depth",
            (model.ValidationInput("passing_depth", True, True, False, True, False, False, True, True),),
            ("validation_depth_inputs_ready", "direct_validation_ran", "validation_passed"),
        ),
        (
            "stale_dataset",
            (depth_cases["stale_dataset"],),
            ("dataset_identity_stale_blocked",),
        ),
        (
            "uncertain_mapping",
            (depth_cases["uncertain_mapping"],),
            ("mapping_review_uncertain_blocked",),
        ),
        (
            "scope_overclaim",
            (depth_cases["snapshot_overclaim"],),
            ("claim_scope_overreach_blocked",),
        ),
        (
            "split_overlap",
            (depth_cases["split_overlap"],),
            ("split_overlap_blocked",),
        ),
        (
            "series_and_envelope_evidence",
            (depth_cases["series_missing"], depth_cases["envelope_intervals_missing"]),
            ("residual_series_missing_blocked", "envelope_intervals_missing_blocked"),
        ),
        (
            "native_receipt",
            (depth_cases["depth_receipt_missing"],),
            ("depth_receipt_missing_blocked",),
        ),
        (
            "coverage_universe",
            (depth_cases["shallow_point_universe"],),
            ("coverage_universe_incomplete_blocked",),
        ),
        (
            "temporal_adequacy",
            (depth_cases["endpoint_or_duplicate_time"],),
            ("temporal_adequacy_failed_blocked",),
        ),
        (
            "critical_family_coverage",
            (depth_cases["shallow_signal_family"],),
            ("critical_family_coverage_failed_blocked",),
        ),
        (
            "parameter_temporal_adequacy",
            (depth_cases["one_point_time_varying_parameter"],),
            ("parameter_temporal_adequacy_failed_blocked",),
        ),
        (
            "parameter_universe_and_denominator",
            (
                depth_cases["ten_thousand_parameters_two_bound"],
                depth_cases["parameter_denominator_missing"],
                depth_cases["manifest_point_count_mismatch"],
            ),
            (
                "parameter_universe_incomplete_blocked",
                "per_parameter_denominator_missing_blocked",
                "manifest_point_denominator_mismatch_blocked",
            ),
        ),
        (
            "parameter_stage_and_individual_depth",
            (
                depth_cases["parameter_endpoints_or_same_stage"],
                depth_cases["one_shallow_parameter_among_deep"],
            ),
            (
                "parameter_strata_incomplete_blocked",
                "parameter_temporal_adequacy_failed_blocked",
            ),
        ),
        (
            "dynamic_floor_anti_degeneracy",
            (
                depth_cases["three_of_thousand"],
                depth_cases["representative_32_of_1000"],
            ),
            (
                "dynamic_coverage_floor_insufficient_blocked",
                "validation_passed",
            ),
        ),
        (
            "parameter_representative_and_sensitive_contribution_boundaries",
            (
                depth_cases["representative_parameter_without_direction_envelope"],
                depth_cases["disconnected_time_varying_parameter"],
                depth_cases["effectless_sensitive_parameter"],
            ),
            (
                "representative_parameter_evidence_missing_blocked",
                "parameter_model_contribution_missing_blocked",
                "parameter_model_contribution_missing_blocked",
            ),
        ),
        (
            "verified_non_sensitive_contribution_boundary",
            (
                depth_cases["unbounded_non_sensitive_disposition"],
                depth_cases["verified_non_sensitive_parameter"],
            ),
            (
                "non_sensitive_parameter_disposition_unbounded_blocked",
                "validation_passed",
            ),
        ),
        (
            "static_parameter_binding_boundary",
            (
                depth_cases["static_parameter_without_binding"],
            ),
            (
                "static_parameter_binding_missing_blocked",
            ),
        ),
        (
            "pointwise_prediction",
            (depth_cases["pointwise_prediction"],),
            ("pointwise_prediction_forbidden_blocked",),
        ),
        (
            "stateful_predictive_rollout",
            (depth_cases["stateful_rollout_failed"], depth_cases["stateful_rollout_pass"]),
            ("predictive_rollout_failed_blocked", "validation_passed"),
        ),
    )
    ok = True
    for group_name, external_inputs, required_labels in groups:
        report = Explorer(
            workflow=model.build_workflow(),
            initial_states=(model.initial_state(),),
            external_inputs=external_inputs,
            invariants=model.INVARIANTS,
            max_sequence_length=model.MAX_SEQUENCE_LENGTH,
            terminal_predicate=model.terminal_predicate,
            required_labels=required_labels,
        ).explore()
        print(f"=== {group_name} ===")
        print(report.format_text())
        ok = ok and report.ok
    evidence_groups = zip(
        evidence_model.VALIDATION_DEPTH_EXTERNAL_INPUTS,
        (
            "exact_dataset_identity_missing_partial",
            "mapping_review_missing_partial",
            "observed_series_missing_partial",
            "validation_depth_receipt_missing_partial",
        ),
        strict=True,
    )
    for evidence_input, required_label in evidence_groups:
        evidence_report = Explorer(
            workflow=evidence_model.build_workflow(),
            initial_states=(evidence_model.initial_state(),),
            external_inputs=(evidence_input,),
            invariants=evidence_model.INVARIANTS,
            max_sequence_length=evidence_model.MAX_SEQUENCE_LENGTH,
            terminal_predicate=evidence_model.terminal_predicate,
            required_labels=(required_label,),
        ).explore()
        print(f"=== evidence_registry_{evidence_input.case_id} ===")
        print(evidence_report.format_text())
        ok = ok and evidence_report.ok
    from flowguard.field_lifecycle import review_field_lifecycle
    field_report = review_field_lifecycle(lifecycle.build_field_lifecycle_plan())
    print(field_report.format_text())
    ok = ok and field_report.ok
    return 0 if ok else 1


if __name__ == "__main__":
    from flowguard.map.runner import run_owner
    raise SystemExit(run_owner(main))
