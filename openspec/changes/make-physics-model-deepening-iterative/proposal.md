## Why

PhysicsGuard already freezes competing hypotheses, ranks observations, compares signal/residual/timing predictions, and validates candidate revisions. It can still stop after one matching observation even when native execution-depth evidence shows missing physical boundaries, mappings, alternatives, uncertainty, or predictive rollout coverage.

## What Changes

- **BREAKING** Make addressable PhysicsGuard depth gaps require another task-local hypothesis/model iteration.
- Extend the existing plan, observation, and candidate-revision records with task purpose, coverage identity, gap transitions, iteration identity, and terminal reason.
- Make native depth and predictive-rollout gaps visible in candidate evaluation.
- Update the purpose-contract generator and all affected PhysicsGuard prompts.
- Add known-good/known-bad tests for shallow, stalled, stale, and externally blocked diagnosis.

## Capabilities

### New Capabilities
- None. The existing task-local hypothesis revision capability is extended.

### Modified Capabilities
- `simulation-validation-depth`: require current task-local model deepening and closure evidence.

## Impact

- `src/physicsguard/schema/task_local_revision.py`, core evaluator, CLI, execution-depth output, purpose-contract generator, ten generated skill prompts, tests, and local SkillGuard target contracts.
- No new physical component model, external simulator dependency, or generic understanding service.
