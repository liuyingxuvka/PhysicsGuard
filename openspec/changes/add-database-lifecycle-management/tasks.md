## 1. OpenSpec And FlowGuard Governance

- [x] 1.1 Create proposal, design, specs, and task records for database lifecycle management.
- [x] 1.2 Validate the OpenSpec change with strict validation.
- [x] 1.3 Add or extend FlowGuard models for explicit database lifecycle, intake, maintenance, history, archive, and AI handoff.
- [x] 1.4 Update model-code traceability and local FlowGuard adoption logs.

## 2. Lifecycle Schemas

- [x] 2.1 Add database policy, lifecycle artifact, history event, archive record, maintenance report, intake plan/report, and model-template index schemas.
- [x] 2.2 Extend catalog project records with lifecycle/admission state, admission evidence, archive/supersession/rejection fields, and maintenance metadata.
- [x] 2.3 Add loader support and package exports for the new lifecycle artifacts.

## 3. Core Behavior

- [x] 3.1 Implement database root initialization with dry-run default and explicit apply writes.
- [x] 3.2 Implement policy and model-template index checks.
- [x] 3.3 Implement project intake planning against project-level PhysicsGuard requirements.
- [x] 3.4 Implement explicit project admission with catalog update and history append.
- [x] 3.5 Implement maintenance audit for lifecycle artifacts, project state, stale paths, validation/reuse gaps, duplicates, and next actions.
- [x] 3.6 Implement archive/deprecate/supersede/reject project lifecycle transitions with no silent deletion.
- [x] 3.7 Implement Markdown handoff rendering for non-PhysicsGuard AI agents.

## 4. CLI And Integration

- [x] 4.1 Add `database init`, `policy-check`, `intake-plan`, `admit`, `audit`, `archive`, `render-handoff`, and `template-index-check` commands.
- [x] 4.2 Keep write-capable commands dry-run by default and require explicit apply intent.
- [x] 4.3 Update project workflow policy and database catalog map/query behavior for lifecycle states.

## 5. Skills, Docs, Templates, Examples

- [x] 5.1 Add database adoption, project intake, and maintenance skill routes.
- [x] 5.2 Update existing database catalog, project adoption, project evidence, model library, validation, closure, and AI debugging skills.
- [x] 5.3 Add templates for policy, README/status, intake plan/report, maintenance report, history event, archive record, and model-template index.
- [x] 5.4 Add docs and examples for an explicit local database root.
- [x] 5.5 Sync installed Codex skills.

## 6. Tests, Version, And Release Hygiene

- [x] 6.1 Add schema/core/CLI tests for initialization, dry-run/apply writes, intake, admission, maintenance, history, archive, handoff, and template index checks.
- [x] 6.2 Run OpenSpec, FlowGuard, ledger, CLI smoke, focused tests, and full pytest.
- [x] 6.3 Reinstall/sync the local editable package and verify imports resolve to the workspace.
- [x] 6.4 Update VERSION, package metadata, README, CHANGELOG, examples, installed skills, and project records.
- [x] 6.5 Perform final completion audit, KB postflight, and local git commit.
