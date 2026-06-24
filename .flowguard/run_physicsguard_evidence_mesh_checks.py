"""Run FlowGuard checks for PhysicsGuard evidence mesh gates."""

from __future__ import annotations

from flowguard.explorer import Explorer

import physicsguard_evidence_mesh_model as model


def _case(case_id: str, **overrides: bool) -> model.EvidenceMeshInput:
    values = {
        "parent_current": True,
        "child_current": True,
        "child_consumed_by_parent": True,
        "obligations_have_contracts": True,
        "tests_current_and_bound": True,
        "contract_cases_generated": True,
        "contract_cases_have_oracles": True,
        "contract_cases_consumed_downstream": True,
        "parent_suite_current": True,
        "child_suites_current": True,
        "parent_consumes_child_suites": True,
        "fields_projected": True,
        "old_fields_closed": True,
        "risk_ledger_current": True,
        "risk_consumes_all_routes": True,
    }
    values.update(overrides)
    return model.EvidenceMeshInput(case_id=case_id, **values)


def main() -> int:
    groups = (
        (
            "clean_mesh",
            (_case("clean"),),
            (
                "model_mesh_ready",
                "model_test_alignment_ready",
                "contract_exhaustion_ready",
                "test_mesh_ready",
                "field_lifecycle_ready",
                "evidence_mesh_passed",
            ),
        ),
        (
            "model_mesh_blocks",
            (
                _case("parent_stale", parent_current=False),
                _case("child_stale", child_current=False),
                _case("child_local_only", child_consumed_by_parent=False),
            ),
            ("parent_mesh_blocks", "stale_child_blocks", "child_local_only_blocks"),
        ),
        (
            "alignment_blocks",
            (
                _case("missing_contract", obligations_have_contracts=False),
                _case("missing_test", tests_current_and_bound=False),
            ),
            ("mta_missing_contract_blocks", "mta_missing_test_blocks"),
        ),
        (
            "contract_exhaustion_blocks",
            (
                _case("handwritten_case", contract_cases_generated=False),
                _case("missing_oracle", contract_cases_have_oracles=False),
                _case("case_not_consumed", contract_cases_consumed_downstream=False),
            ),
            ("handwritten_case_blocks", "missing_oracle_blocks", "case_not_consumed_blocks"),
        ),
        (
            "test_mesh_blocks",
            (
                _case("parent_suite_stale", parent_suite_current=False),
                _case("child_suite_progress", child_suites_current=False),
                _case("child_suite_local_only", parent_consumes_child_suites=False),
            ),
            ("parent_suite_blocks", "progress_only_child_suite_blocks", "child_suite_local_only_blocks"),
        ),
        (
            "field_and_risk_blocks",
            (
                _case("field_missing_projection", fields_projected=False),
                _case("old_field_open", old_fields_closed=False),
                _case("risk_not_current", risk_ledger_current=False),
                _case("risk_missing_route", risk_consumes_all_routes=False),
            ),
            (
                "field_projection_blocks",
                "old_field_disposition_blocks",
                "risk_ledger_status_blocks",
                "risk_ledger_missing_route_blocks",
            ),
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
