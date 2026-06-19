# Database Lifecycle And Catalog

The PhysicsGuard database is an explicit local folder that a user chooses to
create. It is not a hidden global database and it does not automatically absorb
every project on a computer.

For Guard-neutral database roots, cross-Guard catalogs, lifecycle ledgers,
freshness, closure, AI navigation, or reusable database claims, use the
`databank-workflow` Codex skill. The PhysicsGuard database remains a legacy
provider/compatibility route for physical, test, and model evidence maps.

The database stores maps, policies, project cards, history, maintenance reports,
and reusable model-template pointers. Large raw test files stay where they are.
Project-level details stay in project evidence registries.

## Files In One Database

```text
DATABASE_README.md              AI-readable map and first-read guide
DATABASE_STATUS.md              concise blockers and review gaps
database_policy.yaml            rules for this database
database_catalog.yaml           project cards and model-library pointers
database_history.jsonl          append-only lifecycle events
database_maintenance_report.yaml latest maintenance audit output
model_template_index.yaml       reusable template/model-asset pointers
```

`database_catalog.yaml` is still the main search map, but it now belongs to a
larger lifecycle. It records each project's lifecycle state:

- `candidate`: found or proposed, not yet trusted for active database claims.
- `placeholder`: kept as a known missing or incomplete project.
- `active_registered`: active project with project-level evidence.
- `active_validated`: active project with reviewed validation evidence.
- `active_reusable`: active project whose model evidence is reusable with
  stated limits.
- `blocked`: active work is blocked by missing evidence.
- `archived`, `deprecated`, `superseded`, `rejected`: historical states kept
  for traceability and excluded from default query results.

## Create A Database

Dry-run first:

```powershell
python -m physicsguard.cli database init DATABASE_ROOT --database-id local_database --pretty
```

Write the files only with explicit apply intent:

```powershell
python -m physicsguard.cli database init DATABASE_ROOT --database-id local_database --apply --pretty
```

This creates the seven database files listed above. It does not copy raw test
datasets or move project files.

## Add A Project

Plan intake first:

```powershell
python -m physicsguard.cli database intake-plan DATABASE_ROOT PROJECT_ROOT --requested-state candidate --pretty
```

The intake plan looks for project evidence registry and project adoption files.
For active states, missing project evidence is a blocking issue. Candidate and
placeholder states can be used when the database should remember a project that
is not ready yet.

After reviewing the plan, save it as YAML and apply it:

```powershell
python -m physicsguard.cli database admit DATABASE_PROJECT_INTAKE_PLAN.yaml --apply --pretty
```

Admission updates `database_catalog.yaml` and appends an event to
`database_history.jsonl`.

## Maintain The Database

Run lifecycle audit:

```powershell
python -m physicsguard.cli database audit DATABASE_ROOT --pretty
```

Run catalog-specific checks and maps:

```powershell
python -m physicsguard.cli database check CATALOG.yaml --pretty
python -m physicsguard.cli database scan ROOT --catalog CATALOG.yaml --pretty
python -m physicsguard.cli database refresh CATALOG.yaml --pretty
python -m physicsguard.cli database gap-check CATALOG.yaml --pretty
python -m physicsguard.cli database map CATALOG.yaml --pretty
python -m physicsguard.cli database query CATALOG.yaml --quantity pump.flow_readback --pretty
```

By default, query excludes `archived`, `deprecated`, `superseded`, and
`rejected` projects. Use `--include-inactive` when historical records are
needed.

## Archive Or Replace A Project

Do not silently delete project records. Use an explicit lifecycle state:

```powershell
python -m physicsguard.cli database archive CATALOG.yaml PROJECT_ID --reason "superseded by cleaned project record" --archive-state superseded --superseded-by-project-id NEW_PROJECT_ID --apply --pretty
```

Archive operations update the catalog and append history. They preserve why the
record changed.

## AI Handoff

Render the handoff files after meaningful changes:

```powershell
python -m physicsguard.cli database render-handoff DATABASE_ROOT --apply --pretty
```

Other AI agents should read `DATABASE_README.md` and `DATABASE_STATUS.md`
before answering database questions. Those files tell them which projects are
present, which project evidence registries exist, what is active, what is
historical, and what gaps remain.

## Claim Boundary

Database maps and queries are navigation outputs. They can identify related
candidate projects, historical tests, reusable model candidates, and missing
maintenance work. They cannot prove physical consistency, validation pass,
model reuse, or direct cross-project comparability.

Broad claims still require project evidence maps, test-file contracts,
model-dataset validation reports, model-library checks, project closure, and an
explicit comparison scope.
