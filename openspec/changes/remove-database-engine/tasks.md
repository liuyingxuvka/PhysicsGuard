## 1. Inventory And Boundary

- [x] 1.1 Inventory PhysicsGuard database CLI, core, schema, templates, examples, docs, tests, package exports, and active model records.
- [x] 1.2 Confirm DataBank package CLI is locally installable before removing PhysicsGuard database engine.
- [x] 1.3 Keep historical logs as audit evidence while excluding them from active route checks.

## 2. Remove Engine Surfaces

- [x] 2.1 Remove the `database` CLI command group and handlers.
- [x] 2.2 Remove database catalog/lifecycle core modules and schema exports from active package code.
- [x] 2.3 Remove database templates, examples, docs, and tests from active PhysicsGuard ownership.
- [x] 2.4 Update package root exports and loader helpers so no active database engine API remains.

## 3. Update Docs, Skills, And Version

- [x] 3.1 Update README and current PhysicsGuard skills so database-ledger questions point outside PhysicsGuard without old commands.
- [x] 3.2 Update portable-header hints, model-code ledger, FlowGuard active validation set, and adoption records.
- [x] 3.3 Bump PhysicsGuard to `0.9.0` for the breaking CLI/API removal.
- [x] 3.4 Sync installed PhysicsGuard skills from repository source.

## 4. Validation

- [x] 4.1 Verify `python -m physicsguard.cli database --help` fails and old database command docs are absent from current docs/skills.
- [x] 4.2 Run OpenSpec validation, FlowGuard project audit, remaining FlowGuard checks, installed skill sync, import/version checks, and full pytest.
- [x] 4.3 Record FlowGuard/OpenSpec validation evidence and update local git state.
