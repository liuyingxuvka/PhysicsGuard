"""Run FlowGuard checks for the test-file contract development process."""

from __future__ import annotations

from flowguard.explorer import Explorer

import physicsguard_test_file_contract_development_model as model


def main() -> int:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        required_labels=(
            "openspec_validated",
            "flowguard_models_current",
            "implementation_and_artifacts_complete",
            "validation_current",
            "local_install_synced",
            "git_publish_ready",
            "release_created",
            "openspec_invalid",
            "flowguard_models_stale",
            "implementation_incomplete",
            "docs_skills_examples_incomplete",
            "validation_failed_or_stale",
            "local_install_unsynced",
            "git_publish_not_ready",
            "release_not_created",
        ),
    ).explore()
    print(report.format_text())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

