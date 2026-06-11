---
name: physicsguard-database-catalog
description: Use when indexing, scanning, refreshing, querying, or reading a database-level PhysicsGuard catalog across multiple projects, historical tests, project evidence registries, model libraries, tested quantities, model targets, generic tags, and cross-project gaps. Trigger for database map, many projects, historical test search, cross-project comparison, reusable model discovery, or "what has been tested before" requests.
---

# PhysicsGuard Database Catalog

Use this route for database-level navigation and query. The catalog is the map
above project evidence registries. It must not store raw test data, replace
project-level validation, or claim direct comparability by itself.

If the task is to create a new database root, route to
`physicsguard-database-adoption`. If the task is to add or update one project
inside a database, route to `physicsguard-database-project-intake`. If the task
is archive/deprecate/supersede/reject/repair/maintain, route to
`physicsguard-database-maintenance`.

## Workflow

1. Read first-read files when present:

   - `DATABASE_README.md`
   - `DATABASE_STATUS.md`
   - `database_policy.yaml`
   - `database_catalog.yaml`
   - `database_maintenance_report.yaml`

2. Check the catalog:

   ```powershell
   python -m physicsguard.cli database check CATALOG.yaml --pretty
   ```

3. Scan candidate project registries or model libraries when discovery is
   needed:

   ```powershell
   python -m physicsguard.cli database scan ROOT --catalog CATALOG.yaml --pretty
   ```

4. Refresh read-only project summaries from referenced project evidence
   registries:

   ```powershell
   python -m physicsguard.cli database refresh CATALOG.yaml --pretty
   ```

5. Run gap checking before broad database, reuse, or comparison claims:

   ```powershell
   python -m physicsguard.cli database gap-check CATALOG.yaml --pretty
   ```

6. Build the AI onboarding map:

   ```powershell
   python -m physicsguard.cli database map CATALOG.yaml --pretty
   ```

7. Query by tag, tested quantity, component, model target, validation state, or
   test-data state:

   ```powershell
   python -m physicsguard.cli database query CATALOG.yaml --tag TAG --pretty
   ```

   Use `--include-inactive` only when the user needs historical archived,
   deprecated, superseded, or rejected records.

## Rules

- Treat the catalog as a directory map. Keep large datasets in original
  locations and reference them through project evidence registries.
- Use generic tags; do not hardcode an industry taxonomy into the skill.
- Active projects should have project evidence registries and current gap
  status. Candidate and placeholder projects can exist, but must not be used
  for broad active claims.
- If a referenced project registry has blocking gaps, database-level validated
  reuse and broad comparison claims are blocked.
- Query matches are related candidates. Inspect project evidence maps,
  validation reports, model-library records, project closure, and comparison
  scope before making technical conclusions.

## Relationship To Other Routes

- Use `physicsguard-database-adoption` to initialize an explicit local database
  root.
- Use `physicsguard-database-project-intake` to admit, update, or stage one
  project.
- Use `physicsguard-database-maintenance` for audit, archive, supersession,
  rejection, and AI handoff refresh.
- Use `physicsguard-project-evidence-registry` for one project's files, facts,
  bindings, and gaps.
- Use `physicsguard-test-file-contract-review` for one test file's fields,
  units, roles, and model bindings.
- Use `physicsguard-model-dataset-validation` for residual validation evidence.
- Use `physicsguard-model-library` for reusable model asset indexing.
