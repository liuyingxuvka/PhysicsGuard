"""Run FlowGuard checks for PhysicsGuard project closure gates."""

from __future__ import annotations

from flowguard.explorer import Explorer

import physicsguard_project_closure_model as model


def main() -> int:
    groups = (
        (
            "clean_validation_closure",
            (
                model.ProjectClosureInput(
                    "clean_validation",
                    "validation_ready",
                    True,
                    True,
                    True,
                    False,
                    False,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                ),
            ),
            ("project_audit_ready", "evidence_gate_clean", "downstream_checks_with_evidence_mesh", "closure_passed"),
        ),
        (
            "evidence_blocks",
            (
                model.ProjectClosureInput("audit_fail", "project_ready", False, True, True, False, False, True, True, True, True, True, True, False, True),
                model.ProjectClosureInput("map_only", "project_ready", True, True, False, False, False, True, True, True, True, True, True, False, True),
                model.ProjectClosureInput("blocking_gap", "project_ready", True, True, True, True, False, True, True, True, True, True, True, False, True),
            ),
            ("project_audit_blocks", "map_alone_cannot_pass", "blocking_gap_blocks"),
        ),
        (
            "review_and_skipped",
            (
                model.ProjectClosureInput("review_gap", "project_ready", True, True, True, False, True, True, True, True, True, True, True, False, True),
                model.ProjectClosureInput("skipped_required", "validation_ready", True, True, True, False, False, True, False, True, True, True, True, False, True),
            ),
            ("review_gap_downgrades", "review_gaps_partial", "skipped_required_blocks"),
        ),
        (
            "downstream_blocks",
            (
                model.ProjectClosureInput("contract_fail", "analysis_ready", True, True, True, False, False, True, True, False, True, True, True, False, True),
                model.ProjectClosureInput("validation_fail", "validation_ready", True, True, True, False, False, True, True, True, False, True, True, False, True),
                model.ProjectClosureInput("library_fail", "validated_reuse_ready", True, True, True, False, False, True, True, True, True, False, True, False, True),
                model.ProjectClosureInput("hierarchy_fail", "fault_localization_ready", True, True, True, False, False, True, True, True, True, True, False, False, True),
                model.ProjectClosureInput("evidence_mesh_fail", "validation_ready", True, True, True, False, False, True, True, True, True, True, True, True, False),
            ),
            ("test_contract_blocks", "validation_blocks", "model_library_blocks", "hierarchy_closure_blocks", "evidence_mesh_blocks"),
        ),
        (
            "native_depth_receipt_supervision",
            (
                model.ProjectClosureInput("depth_receipt_fail", "validation_ready", True, True, True, False, False, True, True, True, True, True, True, False, True, validation_depth_receipt_ok=False),
                model.ProjectClosureInput("supervisor_recomputes_physics", "validation_ready", True, True, True, False, False, True, True, True, True, True, True, False, True, supervisory_physics_recomputed=True),
            ),
            ("validation_depth_receipt_blocks", "supervisory_physics_recompute_blocked"),
        ),
        (
            "adequacy_scope_and_prediction_closure",
            (
                model.ProjectClosureInput("snapshot_mismatch", "validation_ready", True, True, True, False, False, True, True, True, True, True, True, False, True, covered_scope_compatible=False),
                model.ProjectClosureInput("adequacy_fail", "validation_ready", True, True, True, False, False, True, True, True, True, True, True, False, True, adequacy_passed=False),
                model.ProjectClosureInput("pointwise_prediction", "prediction_ready", True, True, True, False, False, True, True, True, True, True, True, False, True, stateful_dynamic=False, predictive_rollout_passed=False),
                model.ProjectClosureInput("predictive_fail", "prediction_ready", True, True, True, False, False, True, True, True, True, True, True, False, True, stateful_dynamic=True, predictive_rollout_passed=False),
                model.ProjectClosureInput("predictive_pass", "prediction_ready", True, True, True, False, False, True, True, True, True, True, True, False, True, stateful_dynamic=True, predictive_rollout_passed=True),
            ),
            ("requested_covered_scope_mismatch_blocks", "validation_adequacy_blocks", "pointwise_prediction_closure_blocked", "predictive_rollout_closure_blocked", "closure_passed"),
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
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
