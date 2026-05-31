## Why

PhysicsGuard already has model-code traceability, but AI-guided debugging still relies on ad hoc metadata for external signal mappings. To avoid blaming a physical model before checking mapping quality, PhysicsGuard needs first-class signal mapping provenance, review-required flags, and same-family follow-up records for unit/sign/mapping bugs.

## What Changes

- Add a signal mapping ledger schema for external signal, PhysicsGuard variable, units, conversion, confidence, review status, source locator, and stale conditions.
- Extend observed-value and hierarchy reporting so low-confidence or review-required mappings are visible.
- Add bug-family follow-up records for unit, sign, mapping, missing-term, map-axis, and boundary-condition issue classes.
- Update AI debugging prompts/docs so suspicious residuals are interpreted through mapping confidence before accusing a model block.
- Keep PhysicsGuard's boundary: no high-fidelity solver, no commercial-tool adapter, no natural-language report generator.

## Capabilities

### New Capabilities
- `signal-mapping-ledger`: PhysicsGuard can preserve external-signal mapping provenance and same-family debugging follow-ups.

### Modified Capabilities
- `model-code-traceability`: The existing ledger should point to the new mapping schema, tests, and stale-evidence rules where model-backed debugging depends on observed signal mapping.

## Impact

- Affected code: observed-value schemas, hierarchy reports, signal modules, CLI JSON output, docs, tests, examples, model-code ledger, README/changelog, and installed PhysicsGuard skill.
- API impact: additive schema fields and report keys; existing observed YAML remains valid.
- Governance impact: requires OpenSpec validation, FlowGuard checks, model-code ledger check, pytest, example hierarchy regressions, package version bump, editable install sync, and installed skill sync.
