## Context

The current database catalog is a YAML/JSON map above project evidence
registries. It can scan, refresh, gap-check, map, and query. It intentionally
does not store raw datasets and does not prove cross-project comparability.

The requested upgrade keeps that explicit-file design, but adds lifecycle
governance so a local database can be created, maintained, audited, and handed
off to other AI agents without becoming an implicit hidden memory.

## Design Decisions

### Decision: Database is explicit and file-backed

A PhysicsGuard database is a user-authorized database root containing explicit
files. The database does not appear automatically because an AI has used
PhysicsGuard before.

Minimum database files:

- `DATABASE_README.md`
- `DATABASE_STATUS.md`
- `database_policy.yaml`
- `database_catalog.yaml`
- `database_history.jsonl`
- `database_maintenance_report.yaml`
- `model_template_index.yaml`

The code may create templates and dry-run reports. Mutating commands require
explicit apply intent.

### Decision: Project admission mirrors project-level PhysicsGuard requirements

Projects may be registered as placeholders or candidates before they are fully
ready, but active database membership requires project-level PhysicsGuard
evidence:

- project adoption record or explicit missing reason;
- project evidence registry or explicit missing reason;
- project profile basics or explicit unknown reasons;
- registered important artifacts;
- binding expectations or exemptions for important fields/facts/model targets;
- gap-check status;
- validation evidence when a model is claimed as validated or reusable;
- model-library evidence when reusable model status is claimed.

The database catalog records the lifecycle state rather than pretending every
record is complete.

### Decision: Lifecycle state is first-class

Project records support states such as:

- `candidate`
- `placeholder`
- `active_registered`
- `active_validated`
- `active_reusable`
- `blocked`
- `archived`
- `deprecated`
- `superseded`
- `rejected`

Queries and maps expose these states. Archived, superseded, deprecated, and
rejected projects stay visible when requested but do not silently count as
current active evidence.

### Decision: History is append-only

Database lifecycle events are written as JSONL records. Events include database
creation, policy changes, project candidates, admission, updates, maintenance
audits, archive, deprecation, supersession, rejection, restoration, and rendered
handoff documents.

History is evidence of what the database maintainer did; it is not physics
validation proof.

### Decision: Model templates are database-level references

`model_template_index.yaml` lists reusable model templates or reusable model
assets, source projects, model-library evidence, validation boundaries,
compatible tags, and known limits. It does not copy full projects or raw data.

This lets AI agents find likely starting points without overclaiming that a
template is valid for a new project.

### Decision: Plain Markdown handoff is mandatory

Other AI agents may not have PhysicsGuard installed. Generated Markdown files
therefore summarize:

- what the database is;
- where the catalog, policy, history, maintenance report, and model-template
  index live;
- how projects are admitted;
- which projects are active, placeholder, blocked, archived, or rejected;
- which evidence is missing;
- how to install or use PhysicsGuard if available;
- which claims are unsafe without running checks.

### Decision: No hidden writes

Scanning, intake planning, maintenance auditing, map building, and query remain
read-only by default. Commands that write database files must require an
explicit apply flag or explicit output path. Reports must say whether they were
dry-run or applied.

## Implementation Shape

Add lifecycle schemas in `src/physicsguard/schema/database_catalog.py` rather
than creating a separate database server abstraction:

- `DatabasePolicySpec`
- `DatabaseLifecycleArtifactsSpec`
- `DatabaseProjectAdmissionSpec`
- `DatabaseProjectIntakePlanSpec`
- `DatabaseProjectIntakeReportSpec`
- `DatabaseMaintenanceReportSpec`
- `DatabaseHistoryEventSpec`
- `DatabaseArchiveRecordSpec`
- `DatabaseModelTemplateIndexSpec`

Extend `CatalogProjectRecordSpec` with lifecycle/admission fields while keeping
existing fields compatible.

Add core functions in `src/physicsguard/core/database_catalog.py`:

- `initialize_database_root`
- `plan_database_project_intake`
- `admit_database_project`
- `audit_database_maintenance`
- `archive_database_project`
- `render_database_handoff`
- `check_database_policy`
- `check_database_model_template_index`

Add CLI routes under `physicsguard database`:

- `init`
- `policy-check`
- `intake-plan`
- `admit`
- `audit`
- `archive`
- `render-handoff`
- `template-index-check`

Existing commands remain.

## FlowGuard Plan

Add a database lifecycle model that covers:

- explicit user intent to create/maintain a database;
- initialize root artifacts;
- scan and plan project intake;
- gate admission on project-level PhysicsGuard requirements;
- append history events for mutations;
- audit maintenance state;
- archive/deprecate/supersede/reject without silent deletion;
- render AI handoff documents;
- block broad claims when lifecycle, evidence, validation, or history gaps
  remain.

Key invariants:

- no database exists implicitly without explicit root artifacts;
- no active project admission without project-level evidence or explicit
  placeholder/blocking state;
- no validated/reusable state without validation/model-library evidence;
- no mutation claim without explicit apply and history event;
- no raw data payload in lifecycle artifacts;
- archived/rejected/superseded projects are not treated as current active
  evidence by default;
- generated Markdown handoff is navigation only.

## Risks

- Lifecycle schemas can become too large. Mitigation: keep required fields small
  and use optional metadata for project-specific variation.
- AI may over-automate admission. Mitigation: default to dry-run reports and
  require apply for writes.
- Model template indexes may be mistaken for validation. Mitigation: require
  source evidence, known limits, and explicit safe-claim boundaries.
- Long-term history can grow. Mitigation: JSONL append-only history is compact
  and auditable; summaries stay in maintenance reports.
