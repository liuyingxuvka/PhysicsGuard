---
name: physicsguard-database-maintenance
description: Use when auditing, maintaining, refreshing, archiving, deprecating, superseding, rejecting, repairing, or handing off an explicit local PhysicsGuard database. Trigger for database maintenance, database gaps, historical project records, inactive projects, cleanup, deletion policy, or AI database status.
---

# PhysicsGuard Database Maintenance

Use this route to keep an explicit database usable over time. The goal is to
show future AI agents what is active, what is historical, what is missing, and
what claims are allowed.

## Workflow

1. Read the database first-read files:

   - `DATABASE_README.md`
   - `DATABASE_STATUS.md`
   - `database_policy.yaml`
   - `database_catalog.yaml`
   - `database_maintenance_report.yaml`
   - `database_history.jsonl`

2. Run lifecycle maintenance audit:

   ```powershell
   python -m physicsguard.cli database audit DATABASE_ROOT --pretty
   ```

3. Run catalog gap checks when project-level readiness matters:

   ```powershell
   python -m physicsguard.cli database gap-check DATABASE_ROOT/database_catalog.yaml --pretty
   python -m physicsguard.cli database map DATABASE_ROOT/database_catalog.yaml --pretty
   ```

4. Archive, deprecate, supersede, or reject records instead of silently
   deleting them:

   ```powershell
   python -m physicsguard.cli database archive DATABASE_ROOT/database_catalog.yaml PROJECT_ID --reason "reason" --archive-state archived --apply --pretty
   ```

5. Re-render handoff files after meaningful changes:

   ```powershell
   python -m physicsguard.cli database render-handoff DATABASE_ROOT --apply --pretty
   ```

## Rules

- Historical records stay in the catalog with a lifecycle state and reason.
- Default query excludes `archived`, `deprecated`, `superseded`, and `rejected`
  records; use `--include-inactive` only for history searches.
- Missing project basics, missing registries, model binding gaps, validation
  gaps, and reusable-model gaps should remain visible in audit output.
- If a parameter, test field, file, or model target should not bind to a model,
  record an explicit reason through the project evidence route rather than
  letting it disappear.
- Maintenance reports and handoff files are maps and status evidence, not
  physical validation proof.
