"""Run FlowGuard checks for PhysicsGuard database catalog workflow."""

from __future__ import annotations

from flowguard.explorer import Explorer

import physicsguard_database_catalog_model as model


def main() -> int:
    groups = (
        (
            "clean_map",
            (
                model.DatabaseCatalogInput(
                    "clean_map", True, True, False, True, True, True, False, False, True, True, "none"
                ),
            ),
            (
                "catalog_found",
                "project_references_registered",
                "project_registries_loaded",
                "cross_project_indexes_built",
                "catalog_gap_check_clean",
                "database_map_ready",
                "database_map_navigation_ready",
            ),
        ),
        (
            "query_and_reuse",
            (
                model.DatabaseCatalogInput("query", True, True, False, True, True, True, False, False, True, True, "query"),
                model.DatabaseCatalogInput("reuse", True, True, False, True, True, True, False, False, True, True, "reuse"),
            ),
            ("database_query_ready", "database_reuse_search_ready"),
        ),
        (
            "comparison_scope",
            (
                model.DatabaseCatalogInput(
                    "comparison_ready", True, True, False, True, True, True, False, False, True, True, "comparison"
                ),
                model.DatabaseCatalogInput(
                    "comparison_blocked", True, True, False, True, True, True, False, False, True, False, "comparison"
                ),
            ),
            ("database_comparison_ready", "comparison_scope_unknown_blocked"),
        ),
        (
            "missing_catalog_or_projects",
            (
                model.DatabaseCatalogInput("catalog_missing", False, True, False, True, True, True, False, False, True, True, "query"),
                model.DatabaseCatalogInput("projects_missing", True, False, False, True, True, True, False, False, True, True, "query"),
            ),
            ("catalog_missing_blocked", "project_references_missing_partial"),
        ),
        (
            "raw_data_and_registry_gaps",
            (
                model.DatabaseCatalogInput("raw_payload", True, True, True, True, True, True, False, False, True, True, "query"),
                model.DatabaseCatalogInput("registries_unloaded", True, True, False, False, True, True, False, False, True, True, "query"),
            ),
            ("raw_data_payload_blocked", "project_registries_unloaded_partial"),
        ),
        (
            "index_and_gap_failures",
            (
                model.DatabaseCatalogInput("indexes_missing", True, True, False, True, False, True, False, False, True, True, "query"),
                model.DatabaseCatalogInput("gap_missing", True, True, False, True, True, False, False, False, True, True, "query"),
                model.DatabaseCatalogInput("blocking_gaps", True, True, False, True, True, True, True, False, True, True, "query"),
            ),
            ("indexes_missing_partial", "catalog_gap_check_missing_blocked", "catalog_blocking_gaps"),
        ),
        (
            "review_and_map_gaps",
            (
                model.DatabaseCatalogInput("review_query", True, True, False, True, True, True, False, True, True, True, "query"),
                model.DatabaseCatalogInput("map_missing", True, True, False, True, True, True, False, False, False, True, "query"),
            ),
            ("catalog_review_gaps_visible", "database_map_ready_with_review_gaps", "handoff_review_gaps_partial", "database_map_missing_partial"),
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

