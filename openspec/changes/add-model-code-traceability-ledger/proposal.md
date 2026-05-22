## Why

PhysicsGuard already has FlowGuard models and adoption logs, but future AI agents still have to rediscover which model blocks map to which source files, tests, examples, and validation commands. A lightweight model-code traceability ledger makes the model useful as durable navigation and release evidence instead of only historical design notes.

## What Changes

- Add a machine-checkable model-code traceability ledger for core FlowGuard-backed PhysicsGuard responsibilities.
- Add documentation explaining how maintainers and AI agents should use and update the ledger.
- Add a validation script and tests that ensure ledger references stay real and reviewable.
- Add release evidence so model regressions, ledger checks, tests, installed package metadata, and GitHub release version remain aligned.
- No breaking changes to PhysicsGuard CLI behavior, YAML schemas, residual semantics, or physical audit modules.

## Capabilities

### New Capabilities
- `model-code-traceability`: Records and validates the relationship between FlowGuard model blocks, source symbols, tests, examples, assumptions, and release evidence.

### Modified Capabilities
- None.

## Impact

- Affected artifacts: `.flowguard/`, `docs/`, `scripts/`, `tests/`, OpenSpec change files, version/changelog release metadata.
- No new runtime dependency is required.
- Public behavior stays unchanged; this is a repository governance, validation, and release hygiene upgrade.
