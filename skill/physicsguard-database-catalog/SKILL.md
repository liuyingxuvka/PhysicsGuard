---
name: physicsguard-database-catalog
description: Use when indexing, scanning, refreshing, querying, or maintaining a database-level PhysicsGuard catalog across multiple projects, historical tests, project evidence registries, model libraries, tested quantities, model targets, generic tags, and cross-project gaps. Trigger for database, many projects, historical test search, cross-project comparison, reusable model discovery, or "what has been tested before" requests.
---

# PhysicsGuard Database Catalog

Use this route for multi-project or database-level questions. The catalog is a
navigation layer above project evidence registries. It must not store raw test
data, replace project-level validation, or claim direct comparability by itself.

## Workflow

1. Locate the database catalog, or create a draft from
   `templates/database_catalog.yaml` when none exists.
2. Run catalog checks:

   ```powershell
   python -m physicsguard.cli database check CATALOG.yaml --pretty
   ```

3. Scan candidate project registries or model libraries when the user asks to
   discover what is present:

   ```powershell
   python -m physicsguard.cli database scan ROOT --catalog CATALOG.yaml --pretty
   ```

4. Refresh the read-only project summaries from referenced project evidence
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

## Rules

- Treat the catalog as a directory map. Keep large datasets in original
  locations and reference them through project evidence registries.
- Use generic tags; do not hardcode an industry taxonomy into the skill.
- If a project lacks a project evidence registry, record the missing reason or
  report a gap instead of pretending the project is complete.
- If a referenced project registry has blocking gaps, database-level validated
  reuse and broad comparison claims are blocked.
- Query matches are related candidates. Inspect project evidence maps,
  validation reports, and comparison scope before making technical conclusions.

## Relationship To Other Routes

- Use `physicsguard-project-evidence-registry` for one project's files, facts,
  bindings, and gaps.
- Use `physicsguard-test-file-contract-review` for one test file's fields,
  units, roles, and model bindings.
- Use `physicsguard-model-dataset-validation` for residual validation evidence.
- Use `physicsguard-model-library` for reusable model asset indexing.
- Use this database catalog route when the question spans projects or history.
