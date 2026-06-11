## Why

PhysicsGuard now has a database catalog that can scan, map, gap-check, and
query many projects. That catalog is still a directory layer, not a complete
explicit local database workflow.

Users need a governed way to create a local PhysicsGuard database, admit
projects only when project-level PhysicsGuard evidence is present or clearly
missing, maintain history, archive records without silent deletion, and give
other AI agents a readable entry point even when they do not run PhysicsGuard.

## What Changes

- Add explicit database lifecycle governance: initialization policy, database
  README/status files, maintenance reports, history events, archive records,
  and model-template indexes.
- Add project intake states so scanned projects can be candidates,
  placeholders, active registered projects, validated/reusable projects,
  archived projects, deprecated projects, superseded projects, rejected
  projects, or blocked projects without pretending they are all complete.
- Add intake checks that compare database project cards against project-level
  PhysicsGuard requirements, especially project adoption records, project
  evidence registries, project profile basics, evidence gaps, bindings,
  validation, and model-library reuse evidence.
- Add write-capable lifecycle commands that remain explicit and safe:
  initialization, intake planning, admission, maintenance audit, archive, and
  README/status rendering. Mutating operations require explicit apply intent.
- Add a database history layer so additions, updates, admissions, archives,
  supersessions, rejections, and policy changes leave an append-only trail.
- Add a model-template index so a local database can point AI agents to
  reusable model templates, compatible evidence, source projects, and limits
  without copying full project contents.
- Strengthen Codex skills so database construction and maintenance are
  explicit user-authorized routes, while non-PhysicsGuard AI agents can still
  read the generated Markdown/YAML map and rules.

## Capabilities

### New Capabilities

- `database-lifecycle-policy`: explicit rules for a local PhysicsGuard database,
  including ownership, scope, admission levels, raw-data policy, write policy,
  and PhysicsGuard repository references.
- `database-adoption`: initialize a database root with catalog, policy,
  README/status, maintenance, history, and model-template artifacts.
- `database-project-intake`: scan, plan, and admit projects with project-level
  PhysicsGuard requirement checks and explicit candidate/placeholder/active
  states.
- `database-maintenance-audit`: run database health checks for missing project
  requirements, broken paths, stale summaries, stale validations, duplicate
  project records, and pending AI maintenance tasks.
- `database-history-and-archive`: append database lifecycle events and archive,
  deprecate, supersede, reject, or restore project records without silent
  deletion.
- `database-ai-handoff`: generate human/AI-readable database README, map, status,
  rules, and maintenance documents that do not require running PhysicsGuard.
- `database-model-template-index`: register model templates and reusable model
  assets at database level while keeping evidence and validity boundaries
  explicit.
- `database-explicit-write-safety`: require explicit apply semantics for
  database mutations and keep dry-run reports as the default.

### Modified Capabilities

- `database-catalog-registry`: project cards gain lifecycle/admission state,
  admission evidence, archive/supersession fields, and links to database policy
  and history.
- `database-gap-check`: lifecycle gaps include project-level PhysicsGuard
  requirement gaps, missing database policy/history/readme artifacts, and stale
  maintenance reports.
- `database-map-report`: database maps include lifecycle state, readiness level,
  model-template references, and next maintenance actions.
- `database-query`: query results expose project lifecycle state and exclude or
  flag archived/rejected/superseded records unless explicitly requested.
- `model-library-index`: database-level model template indexes may reference
  model-library entries but do not replace validation evidence.
- `physicsguard-skills`: database creation, project intake, and database
  maintenance get explicit skill routes and handoff rules.

## Impact

- Affected code: database catalog schema/core module, loader, CLI, workflow
  project policy, package exports, and version metadata.
- Affected artifacts: new OpenSpec specs/tasks, FlowGuard lifecycle model and
  model-code ledger rows, templates, examples, docs, README/CHANGELOG, Codex
  skills, installed skill copies, tests, and local editable package install.
- No external database server or external dependency is added.
- No raw test datasets are copied or embedded in database artifacts.
