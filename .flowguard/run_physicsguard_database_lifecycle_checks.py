"""Run FlowGuard checks for explicit PhysicsGuard database lifecycle workflow."""

from __future__ import annotations

from flowguard.explorer import Explorer

import physicsguard_database_lifecycle_model as model


def main() -> int:
    groups = (
        (
            "explicit_init_and_handoff",
            (
                model.DatabaseLifecycleInput(
                    "init_dry_run", "init", True, False, False, False, False, False, False, False, False, False, "candidate", False, False, False, False, False, False, False
                ),
                model.DatabaseLifecycleInput(
                    "init_apply", "init", True, False, False, False, False, False, True, False, False, False, "candidate", False, False, False, False, True, False, False
                ),
                model.DatabaseLifecycleInput(
                    "handoff", "handoff", True, True, True, True, True, False, False, False, False, False, "candidate", False, False, False, False, False, True, False
                ),
            ),
            ("init_dry_run_no_write", "database_initialized_with_apply", "init_write_with_history", "ai_handoff_rendered"),
        ),
        (
            "implicit_and_root_blocks",
            (
                model.DatabaseLifecycleInput(
                    "implicit", "audit", False, True, True, True, True, False, False, False, True, False, "active", False, False, True, False, False, True, False
                ),
                model.DatabaseLifecycleInput(
                    "root_missing", "audit", True, False, False, False, False, False, False, False, True, False, "active", False, False, True, False, False, True, False
                ),
                model.DatabaseLifecycleInput(
                    "raw_payload", "audit", True, True, True, True, True, True, False, False, True, False, "active", False, False, True, False, False, True, False
                ),
            ),
            ("implicit_database_blocked", "root_artifacts_missing_blocked", "raw_data_payload_blocked"),
        ),
        (
            "intake_and_admission",
            (
                model.DatabaseLifecycleInput(
                    "intake", "intake", True, True, True, True, True, False, False, True, True, False, "active", True, False, False, False, False, False, False
                ),
                model.DatabaseLifecycleInput(
                    "admit_dry_run", "admit", True, True, True, True, True, False, False, True, True, False, "active", True, False, False, False, False, False, False
                ),
                model.DatabaseLifecycleInput(
                    "admit_active", "admit", True, True, True, True, True, False, True, True, True, False, "active", True, False, False, False, True, False, False
                ),
            ),
            ("intake_plan_ready", "admission_dry_run_no_write", "project_admission_gate_ready", "admit_write_with_history"),
        ),
        (
            "admission_blocks",
            (
                model.DatabaseLifecycleInput(
                    "active_missing_requirements", "admit", True, True, True, True, True, False, True, True, False, True, "active", False, False, False, False, True, False, False
                ),
                model.DatabaseLifecycleInput(
                    "validated_missing_validation", "admit", True, True, True, True, True, False, True, True, True, False, "validated", False, False, False, False, True, False, False
                ),
                model.DatabaseLifecycleInput(
                    "reusable_missing_library", "admit", True, True, True, True, True, False, True, True, True, False, "reusable", True, False, False, False, True, False, False
                ),
            ),
            ("active_admission_requirements_blocked", "validated_without_validation_blocked", "reusable_without_model_library_blocked"),
        ),
        (
            "maintenance_and_archive",
            (
                model.DatabaseLifecycleInput(
                    "audit_clean", "audit", True, True, True, True, True, False, False, False, True, False, "active", True, True, True, False, False, True, False
                ),
                model.DatabaseLifecycleInput(
                    "audit_gaps", "audit", True, True, True, True, True, False, False, False, True, False, "active", True, True, True, True, False, True, False
                ),
                model.DatabaseLifecycleInput(
                    "archive_apply", "archive", True, True, True, True, True, False, True, False, True, False, "active", True, True, False, False, True, False, True
                ),
                model.DatabaseLifecycleInput(
                    "archive_no_reason", "archive", True, True, True, True, True, False, True, False, True, False, "active", True, True, False, False, True, False, False
                ),
            ),
            ("maintenance_audit_clean", "maintenance_gaps_partial", "archive_gate_ready", "archive_write_with_history", "archive_reason_missing_blocked"),
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

