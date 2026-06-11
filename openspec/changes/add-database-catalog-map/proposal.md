## Why

PhysicsGuard now has file-level test contracts, project-level evidence
registries, model-dataset validation reports, and model-library indexes. Those
layers still do not provide a database-level map for many projects.

Without a database catalog, AI agents must rediscover which projects exist,
which projects have test data, which models were validated, which quantities or
model targets appear across projects, and which projects still have evidence
gaps. That makes cross-project search, reuse, and comparison fragile.

## What Changes

- Add a Database Catalog that lists projects, project evidence registries,
  model-library indexes, tags, summary confidence states, and scan freshness.
- Add database-level gap checks that surface missing project registries, stale
  registry references, project evidence gaps, missing model validation, and
  unsafe raw-data-in-catalog payloads.
- Add a Database Map report that gives AI agents a cross-project onboarding
  view without copying large test datasets.
- Add query support for tags, quantities, components, model targets, validation
  state, test-data presence, and project status.
- Add CLI commands, docs, templates, examples, a Codex skill route, FlowGuard
  model coverage, tests, install sync, and package version sync.

## Non-Goals

- No database server or external database adapter.
- No copying or embedding large raw test data.
- No claim that projects are comparable without explicit scope and gap checks.
- No replacement for project evidence registries, test-file contracts,
  validation reports, or model-library checks.
- No domain-specific hardcoded taxonomy such as a specific vehicle, energy, or
  component class.

## Capabilities

### New Capabilities

- `database-catalog-registry`: database-level records for project references,
  project tags, model-library indexes, confidence summaries, and catalog
  policies.
- `database-project-index`: cross-project indexes derived from project evidence
  maps, including tested quantities, model targets, tags, models, and gaps.
- `database-gap-check`: database-level missing/stale/gap classification before
  cross-project claims.
- `database-map-report`: AI-readable database map for onboarding and navigation.
- `database-query`: safe query output with claim boundaries and gap visibility.

### Modified Capabilities

- `project-evidence-registry`: may be referenced by database catalogs and should
  be refreshed before catalog-level claims.
- `model-library-index`: remains the model-reuse index; database catalogs only
  summarize and reference it.
- `physicsguard-skills`: multi-project, historical-test, database, or
  cross-project comparison requests should start with the database catalog route.

## Impact

- Affected code: new schema/core modules, loader, CLI commands, package exports.
- Affected artifacts: OpenSpec files, FlowGuard models, model-code ledger,
  templates, docs, examples, Codex skills, project policy, tests, installed
  skill copies, and local package metadata.
