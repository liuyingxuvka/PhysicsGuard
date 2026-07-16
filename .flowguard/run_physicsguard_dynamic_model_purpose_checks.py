"""Run FlowGuard exploration for current PhysicsGuard model-purpose closure."""

from flowguard.explorer import Explorer

import physicsguard_dynamic_model_purpose_model as model


def main() -> int:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        required_labels=(
            "current_purpose_frozen",
            "candidate_bound_after_purpose",
            "known_good_passed",
            "every_dynamic_bad_proven",
            "current_model_purpose_closed",
            "baseline_only_blocked",
            "empty_dynamic_failure_blocked",
            "candidate_binding_blocked",
            "known_good_blocked",
            "bad_proof_exhaustion_blocked",
        ),
    ).explore()
    print(report.format_text())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
