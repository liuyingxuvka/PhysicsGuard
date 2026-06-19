## 1. OpenSpec And FlowGuard Governance

- [x] 1.1 Create proposal, design, specs, and task records for database catalog, map, gap-check, and query.
- [x] 1.2 Validate the OpenSpec change with strict validation.
- [x] 1.3 Add FlowGuard parent/child model and grouped checks for database catalog workflow.
- [x] 1.4 Update model-code traceability and adoption logs.

## 2. Database Catalog Schemas

- [x] 2.1 Add database catalog, project record, model-library reference, policies, confidence summary, and tag dictionary schemas.
- [x] 2.2 Add scan, refresh, gap report, map report, and query report schemas.
- [x] 2.3 Add loader support and package exports.

## 3. Core Behavior

- [x] 3.1 Implement catalog check and raw-data payload guard.
- [x] 3.2 Implement read-only catalog candidate scan.
- [x] 3.3 Implement read-only catalog refresh from project evidence registries.
- [x] 3.4 Implement database gap checks with project evidence gap propagation.
- [x] 3.5 Implement database map generation and safe query filters.

## 4. CLI And Integration

- [x] 4.1 Add `database check`, `scan`, `refresh`, `gap-check`, `map`, and `query` CLI commands.
- [x] 4.2 Keep model-library and project-evidence responsibilities separate while allowing catalog references.
- [x] 4.3 Add database catalog route to project policies.

## 5. Skills, Docs, Templates, Examples

- [x] 5.1 Document database catalog usage without adding a persistent database skill route.
- [x] 5.2 Update AI debugging, project evidence, model library, validation, test-file, and closure skills for database-level routing.
- [x] 5.3 Add docs, templates, and a database catalog example.
- [x] 5.4 Sync installed Codex skills.

## 6. Tests And Validation

- [x] 6.1 Add schema/core/CLI tests for database catalog, scan, refresh, gap-check, map, and query.
- [x] 6.2 Add integration tests against the pump-loop project evidence registry and model library.
- [x] 6.3 Run OpenSpec, FlowGuard, ledger, CLI smoke, focused tests, and full pytest.
- [x] 6.4 Reinstall/sync local editable package and verify imports resolve to the workspace.
- [x] 6.5 Perform final completion audit and local git commit.
