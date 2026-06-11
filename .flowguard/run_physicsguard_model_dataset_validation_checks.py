"""Run FlowGuard checks for PhysicsGuard model-dataset validation."""

from __future__ import annotations

from flowguard import Explorer

import physicsguard_model_dataset_validation_model as model


def main() -> int:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        required_labels=(
            "contracts_passed",
            "direct_validation_ran",
            "calibration_not_enabled",
            "calibration_bounded",
            "validation_passed",
            "holdout_partial",
            "contracts_block_validation",
            "observed_mutation_blocked",
            "calibration_unbounded_blocked",
        ),
    ).explore()
    print(report.format_text())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
