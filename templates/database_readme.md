# PhysicsGuard Database Map

- Database id: `example_database`
- Database name: `Example PhysicsGuard database`
- Database root: `path/to/database`

## Required First Reads

- `database_policy.yaml`
- `database_catalog.yaml`
- `database_maintenance_report.yaml`
- `DATABASE_STATUS.md`
- `database_history.jsonl`
- `model_template_index.yaml`

## Operating Rules

- This is an explicit local database root, not a hidden global database.
- Do not store raw test datasets in database artifacts.
- Active projects should satisfy project-level PhysicsGuard requirements.
- Historical projects stay visible but are excluded from default queries.
- Model templates are reuse starting points, not validation proof.
