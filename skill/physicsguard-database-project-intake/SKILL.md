---
name: physicsguard-database-project-intake
description: Use for legacy PhysicsGuard-specific project intake into physical/test/model evidence catalogs. For Guard-neutral project admission, lifecycle state, query index updates, AI navigation, freshness, closure, or database ledger intake, use databank-workflow instead.
---

# PhysicsGuard Database Project Intake

Use this route when one project should enter or update a legacy
PhysicsGuard-specific database. For Guard-neutral database admission, lifecycle
ledger state, query index updates, AI navigation, freshness, or closure, route
to `databank-workflow`.

The database is a collection of projects, but each project still needs its own
project-level PhysicsGuard evidence before broad active claims.

## Workflow

1. Read the database policy, catalog, status, and maintenance report if they
   exist.
2. Generate an intake plan:

   ```powershell
   python -m physicsguard.cli database intake-plan DATABASE_ROOT PROJECT_ROOT --requested-state candidate --pretty
   ```

3. Choose the lifecycle state conservatively:

   - `candidate` for discovered or proposed projects.
   - `placeholder` when the database should remember a missing or incomplete
     project.
   - `active_registered` only when project evidence is present.
   - `active_validated` only when validation evidence has been reviewed and
     DataBank closure supports the claim.
   - `active_reusable` only when reusable model-library evidence, limits, and
     DataBank closure support the claim.

4. Save or update a `DatabaseProjectIntakePlan` YAML. Do not invent missing
   project name, run period, location, test scope, or evidence. Record unknown
   reasons.
5. Dry-run admission:

   ```powershell
   python -m physicsguard.cli database admit DATABASE_PROJECT_INTAKE_PLAN.yaml --pretty
   ```

6. Apply only after review:

   ```powershell
   python -m physicsguard.cli database admit DATABASE_PROJECT_INTAKE_PLAN.yaml --apply --pretty
   ```

7. Run maintenance audit and refresh the handoff files:

   ```powershell
   python -m physicsguard.cli database audit DATABASE_ROOT --pretty
   python -m physicsguard.cli database render-handoff DATABASE_ROOT --apply --pretty
   ```

## Rules

- Active projects should point to a project evidence registry.
- Database ledger admission should be recorded through DataBank. This route may
  produce or inspect PhysicsGuard provider evidence that DataBank later consumes.
- A database project card is symmetric and lightweight. It should not pretend
  one test file or project is the base version of another unless evidence says
  so.
- Multiple projects or files may bind to similar model targets. Keep each
  project's own evidence and confidence/gap status visible.
- If the project is not ready, keep it as candidate, placeholder, or blocked
  instead of forcing active state.
- `active_validated` and `active_reusable` are not allowed unless current
  provider evidence and DataBank closure support those claims.
- Every admission or update should leave a history event.
