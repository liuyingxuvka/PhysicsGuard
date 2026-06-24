## Why

PhysicsGuard already has FlowGuard models, project evidence registries, test-file contracts, validation gates, and project closure, but the evidence chain is still looser than FlowGuard's current parent/child ModelMesh and model-code-test alignment standard. Broad claims such as `validation_ready`, `fault_localization_ready`, and release readiness need a single strong, machine-checkable chain that proves parent models consume current child evidence, model obligations bind to code contracts and tests, generated bad cases are covered, field lifecycle gaps are closed, and final claims consume the resulting risk evidence.

## What Changes

- Add a first-class PhysicsGuard evidence mesh artifact and checker that combines FlowGuard-style ModelMesh, Model-Test Alignment, ContractExhaustion, TestMesh, FieldLifecycle, and RiskLedger receipt concepts.
- Add a CLI command for checking an evidence mesh YAML file and emitting schema-valid JSON.
- Extend project closure plans so strong claim scopes can consume evidence mesh reports as required inputs.
- Add pump-loop example evidence mesh artifacts that bind existing project evidence, test-file contract, validation, model-library, and closure evidence into one parent claim chain.
- Add FlowGuard model/check coverage for the evidence mesh route itself.
- Update docs, OpenSpec artifacts, model-code traceability, examples, version anchors, and release notes.
- Publish a new source-only GitHub release after validation and local install sync.

## Capabilities

### New Capabilities
- `evidence-mesh`: FlowGuard-grade evidence chain artifacts and checks for parent/child model reattachment, model-code-test rows, generated bad-case receipts, test mesh freshness, field lifecycle closure, risk evidence, and project-closure handoff.

### Modified Capabilities
- `project-closure-gate`: Project closure SHALL optionally require and consume evidence mesh reports before broad claim scopes pass.

## Impact

- Affected runtime API: new schema/core/CLI surfaces for evidence mesh review.
- Affected closure API: project closure plan/report schema gains evidence mesh inputs and required-check flag.
- Affected project artifacts: `.flowguard` models/checks, model-code ledger, docs, examples, OpenSpec change files, version files, CHANGELOG, README version anchors, and installed local package metadata.
- No new physical component models, no commercial-tool dependencies, no high-fidelity solver claims, and no hidden unit conversion behavior.
