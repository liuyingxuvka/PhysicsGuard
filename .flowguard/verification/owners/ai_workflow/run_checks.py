"""Run the PhysicsGuard AI workflow FlowGuard checks."""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "models/owners"))

from flowguard.explorer import Explorer

from ai_workflow import physicsguard_ai_workflow_model as model


def main() -> int:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        required_labels=(
            "project_adopted",
            "preflight_reviewed",
            "intake_and_mappings_reviewed",
            "module_ledger_checked",
            "skills_synced",
            "closure_passed_done_allowed",
            "project_record_missing",
            "preflight_incomplete",
            "mapping_review_required",
            "module_ledger_stale",
            "skills_not_synced",
            "closure_not_passed",
        ),
    ).explore()
    print(report.format_text())
    return 0 if report.ok else 1


if __name__ == "__main__":
    from flowguard.map.runner import run_owner
    raise SystemExit(run_owner(main))

