---
name: physicsguard-database-catalog
description: Use for legacy PhysicsGuard-specific catalog reads over physical/test/model evidence registries. For Guard-neutral catalogs, query gates, lifecycle status, AI navigation, freshness, closure, cross-Guard comparison, or database total ledgers, use databank-workflow instead.
---

# PhysicsGuard Database Catalog

Use this route for legacy PhysicsGuard-specific navigation and query over
physical/test/model evidence. For a Guard-neutral database map, query gate, AI
navigation index, lifecycle status, freshness check, or closure claim, route to
`databank-workflow`.

The catalog is a map above project evidence registries. It must not store raw
test data, replace project-level validation, or claim direct comparability by
itself.

If the task is to create a new database root, admit or update a project in the
database ledger, archive/deprecate/supersede/reject/repair/maintain database
status, or hand off a cross-Guard catalog, route to `databank-workflow`.
Use the other PhysicsGuard database skills only when the user explicitly needs
legacy PhysicsGuard CLI compatibility for physical/test/model evidence maps.

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

   Treat this as PhysicsGuard compatibility output. DataBank AI navigation and
   link freshness should be rendered through `databank-workflow`.

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
- Do not claim the catalog is sufficient for cross-Guard closure, reusable
  database proof, or current freshness. Route those claims to DataBank.
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

- Use `databank-workflow` to initialize, query, maintain, refresh, close, or
  hand off the Guard-neutral database ledger.
- Use `physicsguard-database-adoption`, `physicsguard-database-project-intake`,
  and `physicsguard-database-maintenance` only for legacy PhysicsGuard-specific
  compatibility work.
- Use `physicsguard-project-evidence-registry` for one project's files, facts,
  bindings, and gaps.
- Use `physicsguard-test-file-contract-review` for one test file's fields,
  units, roles, and model bindings.
- Use `physicsguard-model-dataset-validation` for residual validation evidence.
- Use `physicsguard-model-library` for reusable model asset indexing.
