## Why

Nine maintained PhysicsGuard satellite skills and the primary dataset-validation skill were partially migrated against a retired SkillGuard depth/calibration shape. The physical purpose declarations are useful, but they are currently stored as if SkillGuard owned PhysicsGuard semantics. That makes the contracts non-current and can also let an AI connect a shallow model without first proving what the model can actually block.

## What Changes

- Migrate all ten maintained PhysicsGuard skills to the current generic SkillGuard declared-check contract, compiled contract, and exact check manifest while preserving each existing PhysicsGuard workflow as the native owner.
- Require target-native, current-run receipts appropriate to each route: model understanding, signal/evidence mapping, test-file validation, project adoption, model-library readiness, candidate blueprint validation, or audit closure.
- Require a PhysicsGuard-owned guard-model contract to be frozen before a candidate model is built. It declares the prevented failure classes, physical/evidence boundary, native oracle, expected finding code, proof strength, and bounded claim.
- Require one known-good proof plus a known-bad proof for every declared prevented failure class. A missing, untested, mismatched, or non-blocking failure class blocks the model. These are mandatory proof steps, not selectable modes.
- Keep SkillGuard generic: it supervises only the exact checks, owners, dependencies, immutable receipts, installation projection, and closure declared by PhysicsGuard. It does not classify the target or decide what PhysicsGuard should prevent.
- Add a parent suite mesh that inventories all ten maintained skills (the primary dataset-validation skill plus nine satellites), assigns one native owner and route per skill, consumes current child receipts, and blocks incomplete or stale reattachment.
- **BREAKING**: retire and remove the former V1 manifests, work contracts, checker scripts, reports, ledgers, and fallback authority after V2 closure and installation parity are proven. No V1 success route remains.
- Preserve bounded snapshot/data compatibility inside PhysicsGuard where the product contract still requires it; this does not preserve the retired SkillGuard runtime.

## Capabilities

### New Capabilities

- `physicsguard-skill-suite-runtime-authority`: Governs the PhysicsGuard family under one current generic SkillGuard authority while PhysicsGuard owns per-model prevented-failure declarations, native good/bad proof, mesh closure, and formal retirement of obsolete authority.

### Modified Capabilities

None.

## Impact

This affects each maintained PhysicsGuard skill's native guard-model contract, `.skillguard` supervision surface, prompt instructions, proof fixtures, suite inventory/mesh evidence, migration tests, installation parity checks, and global routing metadata. PhysicsGuard domain algorithms and public CLI semantics remain owned by the existing native workflows; no optional operating mode is added.
