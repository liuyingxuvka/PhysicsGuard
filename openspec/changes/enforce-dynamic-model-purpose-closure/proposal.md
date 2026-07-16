## Why

PhysicsGuard currently bundles one fixed prevented-failure contract per skill and then validates that bundled artifact for every invocation. That proves a family capability baseline, but it does not force AI to state what the concrete model being built now is intended to prevent, so a shallow or irrelevant candidate can still appear procedurally complete.

## What Changes

- **BREAKING**: separate immutable family baseline regression from current modeling-instance authority; bundled `guard-model/` fixtures can no longer close a real target modeling task.
- Require AI to freeze a target-local model-purpose contract before constructing a candidate. The contract must state a concrete purpose, at least one prevented physical/evidence failure, the bounded operating/evidence scope, and one PhysicsGuard-native oracle per failure.
- Bind the candidate to the exact contract fingerprint, declared failure universe, actual candidate artifact fingerprint, and an ordered purpose-freeze-before-candidate event chain.
- Require one known-good proof and at least one known-bad proof for every declared failure, all bound to the same contract and candidate identities and evaluated by the declared native oracle.
- Require explicit target-root and artifact paths for current-instance validation; missing, external, stale, mismatched, self-reported, or baseline-only evidence blocks closure.
- Update all PhysicsGuard family skills and their generated SkillGuard check inventories so PhysicsGuard owns dynamic purpose semantics while SkillGuard remains a generic executor and receipt supervisor.

## Capabilities

### New Capabilities

- `dynamic-model-purpose-closure`: Target-local purpose declaration, candidate binding, native good/bad proof coverage, and closure rules for every concrete PhysicsGuard modeling instance.

### Modified Capabilities

- `physicsguard-skill-suite-runtime-authority`: Reclassify bundled guard-model contracts as family baseline regression and require generated skill/runtime authority to point real tasks at target-local dynamic artifacts.

## Impact

- Affects `src/physicsguard/guard_model_contract.py`, the purpose-contract generator, ten PhysicsGuard `SKILL.md` files, generated guard-model baselines, generated SkillGuard V2 authorities, FlowGuard model exports/preflight, and focused regression tests.
- Existing fixed family failure catalogs remain useful as regression fixtures and examples, but cease to be current-task success authority.
- No installation or release projection is part of this change.
