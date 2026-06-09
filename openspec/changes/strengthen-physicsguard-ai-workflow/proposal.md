## Why

PhysicsGuard already checks low-fidelity residuals, hierarchy reports, signal mapping evidence, and assumptions, but AI agents still need stronger project-level guidance before they touch an external model and stronger evidence gates before they claim a fault is localized. This change makes the FlowGuard-inspired workflow explicit: project adoption, model-understanding preflight, signal intake, module/equation traceability, and closure evidence become first-class surfaces instead of scattered documentation.

## What Changes

- Add a PhysicsGuard project adoption surface so repositories can record PhysicsGuard version, repository URL, rule files, logs, skill paths, and workflow policy.
- Add a model-understanding preflight template and validator so AI agents capture symptom, physical boundary, subsystem blocks, conserved quantities, interfaces, units, assumptions, uncertainty, and stop conditions before residual interpretation.
- Add an external-model intake template and validator for external tool metadata, scenario, exported signals, unit evidence, mapping confidence, review state, and stale conditions.
- Add a physical module/equation ledger that maps audit modules to equations, assumptions, validity boundaries, diagnostic keys, tests, and examples.
- Strengthen PhysicsGuard closure guidance so localization claims are gated by audit status, mapping review, missing inputs, stale evidence, skipped checks, and next actions.
- Split PhysicsGuard Codex skill guidance into route-oriented subskills and keep installed local skill copies synchronized with repository source.
- Bump and verify PhysicsGuard version surfaces as a workflow capability upgrade.

## Capabilities

### New Capabilities
- `physicsguard-project-adoption`: Project-level PhysicsGuard adoption, audit, version, policy, and log records.
- `model-understanding-preflight`: AI-facing preflight files that capture low-fidelity physical understanding before audit execution.
- `external-model-intake`: External model snapshot and signal-mapping intake records with review and staleness semantics.
- `physical-module-ledger`: Machine-checkable ledger from module types to equations, units, assumptions, diagnostics, tests, and examples.
- `physicsguard-closure-workflow`: Completion and localization claim boundaries for PhysicsGuard audit work.
- `physicsguard-skill-routes`: Route-oriented Codex skill prompts for project adoption, preflight, signal mapping, closure, and candidate blueprint work.

### Modified Capabilities
- None. Existing runtime solve/evaluate/compare and hierarchy semantics are preserved.

## Impact

- Affected code: `src/physicsguard/cli.py`, new workflow helper modules under `src/physicsguard/`, new validation scripts, tests, templates, and skill folders.
- Affected docs: README, AI debugging protocol, model-code traceability docs, and new workflow references.
- Affected local state: repository FlowGuard adoption record, PhysicsGuard version files, editable install, and installed Codex skill copies under `%USERPROFILE%\.codex\skills`.
- No new external dependencies, no commercial-tool adapter, no high-fidelity physical model, and no automatic repair behavior.
