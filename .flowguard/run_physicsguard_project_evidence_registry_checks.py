"""Run FlowGuard checks for PhysicsGuard project evidence registry workflow."""

from __future__ import annotations

from flowguard.explorer import Explorer

import physicsguard_project_evidence_registry_model as model


def main() -> int:
    groups = (
        (
            "clean_map",
            (model.ProjectEvidenceInput("complete_project_map", True, False, True, True, True, True, False, False, True, "none"),),
            ("profile_known", "artifacts_registered", "binding_complete_or_exempt", "gap_check_clean", "map_generated_ready", "project_map_ready"),
        ),
        (
            "unknown_profile",
            (model.ProjectEvidenceInput("unknown_profile_recorded", False, True, True, True, True, True, False, False, True, "none"),),
            ("profile_unknown_recorded", "project_map_ready"),
        ),
        (
            "downstream_handoffs",
            (
                model.ProjectEvidenceInput("validation_handoff", True, False, True, True, True, True, False, False, True, "validation"),
                model.ProjectEvidenceInput("reuse_handoff", True, False, True, True, True, True, False, False, True, "reuse"),
            ),
            ("downstream_validation_allowed", "downstream_reuse_allowed"),
        ),
        (
            "profile_missing",
            (model.ProjectEvidenceInput("profile_missing", False, False, True, True, True, True, False, False, True, "none"),),
            ("profile_missing_partial",),
        ),
        (
            "artifacts_missing",
            (model.ProjectEvidenceInput("artifact_missing", True, False, False, True, True, True, False, False, True, "none"),),
            ("artifacts_missing_partial",),
        ),
        (
            "bindings_missing",
            (
                model.ProjectEvidenceInput("binding_unreviewed", True, False, True, False, False, True, False, False, True, "none"),
                model.ProjectEvidenceInput("binding_missing", True, False, True, True, False, True, False, False, True, "none"),
            ),
            ("binding_unreviewed_partial", "binding_missing_partial"),
        ),
        (
            "gap_failures",
            (
                model.ProjectEvidenceInput("gap_check_missing", True, False, True, True, True, False, False, False, True, "validation"),
                model.ProjectEvidenceInput("blocking_gap", True, False, True, True, True, True, True, False, True, "validation"),
            ),
            ("gap_check_missing_blocked", "gap_check_blocking"),
        ),
        (
            "review_and_map_gaps",
            (
                model.ProjectEvidenceInput("review_gap", True, False, True, True, True, True, False, True, True, "none"),
                model.ProjectEvidenceInput("map_missing", True, False, True, True, True, True, False, False, False, "none"),
            ),
            ("gap_check_review_gaps_visible", "map_generated_review_partial", "map_missing_partial"),
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

