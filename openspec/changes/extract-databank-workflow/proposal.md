## Why

PhysicsGuard now has strong database lifecycle and catalog features, but those
features are broader than physical/test/model evidence. Database roots,
cross-project catalogs, query gates, lifecycle ledgers, freshness, closure,
provider handoff, and AI navigation should become a Guard-neutral DataBank
workflow that can ingest PhysicsGuard, LogicGuard, TraceGuard, SourceGuard, and
FlowGuard evidence without turning PhysicsGuard into a universal database layer.

## What Changes

- Add a `databank-workflow` Codex skill to the repository and installed skill
  set.
- Define an explicit DataBank root layout with policy, catalog, history,
  contracts, provider results, navigation, closure reports, and query records.
- Add deterministic scripts for root initialization/checking, strict contract
  validation, provider adaptation, freshness, closure, lifecycle transitions,
  navigation, query, intake, and one-command audit.
- Keep legacy PhysicsGuard database skills for PhysicsGuard-specific physical,
  test, and model evidence maps only.
- Update PhysicsGuard caller skills so database total-ledger work routes to
  `databank-workflow`.
- Add executable tests, fixture data, FlowGuard model checks, and install sync
  evidence.

## Capabilities

### New Capabilities

- `databank-workflow`: Guard-neutral database root, catalog, lifecycle, query,
  freshness, closure, provider adapter, and AI navigation workflow.

### Modified Capabilities

- PhysicsGuard database skills become compatibility/provider routes rather than
  canonical total-ledger routes.
- PhysicsGuard non-database skills route cross-project and database-level work
  to DataBank instead of old PhysicsGuard database cards.

## Impact

- Affected paths: `skill/databank-workflow`, selected `skill/physicsguard-*`
  SKILL.md files, OpenSpec records, FlowGuard records, README/install guidance,
  and installed skill copies under `C:\Users\liu_y\.codex\skills`.
- No raw project data is copied into DataBank by default.
- No external database server or new runtime dependency is added.
