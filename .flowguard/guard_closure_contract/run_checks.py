"""Run the Guard closure contract FlowGuard checks."""

from __future__ import annotations

from flowguard import Explorer
import model


def main() -> int:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        required_labels=(
            "clean_closure_report",
            "done_claim_allowed",
            "obligation_stale_evidence",
            "obligation_non_pass",
        ),
    ).explore()
    print(report.format_text())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
