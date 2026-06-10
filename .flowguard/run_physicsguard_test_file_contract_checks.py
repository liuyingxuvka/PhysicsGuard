"""Run FlowGuard checks for the PhysicsGuard test-file contract route."""

from __future__ import annotations

from flowguard import Explorer

import physicsguard_test_file_contract_model as model


def main() -> int:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        required_labels=(
            "no_test_data_optional_route",
            "test_data_route_selected",
            "manifest_generated",
            "manifest_fresh",
            "testbench_profile_resolved",
            "model_binding_resolved",
            "catalog_complete",
            "role_matrix_complete",
            "mapping_edges_evidenced",
            "coverage_contract_passed",
            "broad_claim_allowed",
            "source_file_missing",
            "manifest_not_generated",
            "manifest_missing_extractor",
            "manifest_stale",
            "testbench_profile_missing",
            "model_binding_missing",
            "catalog_missing_fields",
            "role_matrix_missing_roles",
            "mapping_edges_missing",
            "mapping_missing_evidence",
            "mapping_unknown_targets_model_gap",
            "review_required_partial",
            "planned_child_model_partial",
            "contract_check_failed",
        ),
    ).explore()
    print(report.format_text())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
