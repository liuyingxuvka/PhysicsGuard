---
name: physicsguard-database-adoption
description: Use only for legacy or PhysicsGuard-specific local database roots that store physical/test/model evidence maps. For Guard-neutral database roots, catalogs, lifecycle ledgers, AI navigation, freshness, closure, or cross-Guard project collections, use databank-workflow instead.
---

# PhysicsGuard Database Adoption

Use this route only when the user explicitly wants a local PhysicsGuard
database for physical/test/model evidence maps. For a general project evidence
database, database status ledger, cross-Guard handoff, query gate, freshness
check, or AI navigation index, route to `databank-workflow`.

Do not treat the user's whole computer, previous chats, or all PhysicsGuard
projects as an implicit hidden database.

## Workflow

1. Confirm the user intends an explicit local database root.
2. Dry-run database creation first:

   ```powershell
   python -m physicsguard.cli database init DATABASE_ROOT --database-id DATABASE_ID --pretty
   ```

3. If the dry-run looks correct and the user has asked you to proceed, apply:

   ```powershell
   python -m physicsguard.cli database init DATABASE_ROOT --database-id DATABASE_ID --apply --pretty
   ```

4. Check the created policy and model-template index:

   ```powershell
   python -m physicsguard.cli database policy-check DATABASE_ROOT/database_policy.yaml --pretty
   python -m physicsguard.cli database template-index-check DATABASE_ROOT/model_template_index.yaml --pretty
   ```

5. Render or refresh the AI handoff map:

   ```powershell
   python -m physicsguard.cli database render-handoff DATABASE_ROOT --apply --pretty
   ```

## Required Files

The legacy PhysicsGuard database root should contain:

- `DATABASE_README.md`
- `DATABASE_STATUS.md`
- `database_policy.yaml`
- `database_catalog.yaml`
- `database_history.jsonl`
- `database_maintenance_report.yaml`
- `model_template_index.yaml`

## Rules

- Database writes require explicit apply intent.
- The database stores maps, policies, summaries, history, and references. It
  does not store raw test datasets.
- This route is compatibility/provider guidance. A successful
  `physicsguard.cli database` command is not sufficient for DataBank freshness,
  cross-Guard closure, or reusable database claims.
- `DATABASE_README.md` and `DATABASE_STATUS.md` are the first-read files for AI
  agents that do not have the PhysicsGuard skill installed.
- Model templates in `model_template_index.yaml` are reusable starting points,
  not proof that a new project is validated.
- After creation, route project additions through
  `databank-workflow` for database-ledger admission and through
  `physicsguard-database-project-intake` only for PhysicsGuard-specific
  compatibility.
