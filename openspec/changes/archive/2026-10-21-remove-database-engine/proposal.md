## Why

PhysicsGuard still owns a package-level database engine and `physicsguard
database` CLI even after its Codex database skill routes were removed. That
keeps two database control paths alive and conflicts with the clean boundary:
PhysicsGuard should produce physical provider evidence, while DataBank should
own database ledger, lifecycle, freshness, query, navigation, and closure.

## What Changes

- **BREAKING**: Remove the `python -m physicsguard.cli database ...` command
  group with no bridge command, alias, compatibility route, or fallback.
- Remove PhysicsGuard database catalog/lifecycle core modules, schemas,
  templates, tests, examples, and docs that implement database-ledger ownership.
- Remove database catalog/lifecycle exports from the public `physicsguard`
  package.
- Keep PhysicsGuard provider responsibilities: test-file facts, units,
  parameter roles, signal mapping, model binding, residual validation, model
  dataset validation, model library evidence, project evidence registry, and
  project closure reports.
- Update PhysicsGuard README, skills, portable-header hints, and active machine
  records so database-level work points to DataBank conceptually without keeping
  old database control commands.
- Preserve historical changelog and FlowGuard logs as audit history only; they
  must not act as live routes.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `database-catalog-map`: retire PhysicsGuard ownership; database map/query
  behavior moves to DataBank.
- `database-lifecycle-management`: retire PhysicsGuard ownership; database root,
  project intake/admission, lifecycle history, maintenance, and handoff move to
  DataBank.
- `project-evidence-registry`: clarify that PhysicsGuard project evidence is a
  provider input to an external DataBank ledger.
- `model-library-index`: clarify that cross-project discovery and model-template
  indexing are DataBank ledger concerns, while PhysicsGuard model-library
  records remain provider evidence.

## Impact

- Removes public CLI/API surfaces and related tests/docs/templates/examples from
  PhysicsGuard.
- Updates active OpenSpec, FlowGuard model-code ledgers, package exports,
  installed skill sync checks, and README content.
- Requires full PhysicsGuard regression, FlowGuard checks, OpenSpec validation,
  installed skill validation, and a negative CLI check proving
  `python -m physicsguard.cli database --help` fails.
