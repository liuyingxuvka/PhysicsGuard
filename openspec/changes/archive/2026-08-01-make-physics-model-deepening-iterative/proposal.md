## Why

PhysicsGuard already freezes competing hypotheses, ranks observations, compares signal/residual/timing predictions, and validates candidate revisions. The first implementation left strict fields optional, accepted caller-declared gaps and check statuses, and could close after one matching observation even when native execution-depth evidence still showed missing physical boundaries, mappings, residual proof, uncertainty, diagnosability, or predictive rollout coverage.

## What Changes

- **BREAKING** Replace the optional/legacy task-local shape with one strict current shape; no compatibility reader or default-success path remains.
- Require every non-trivial plan to bind an exact task purpose, independently owned coverage universe and fingerprint, explicit assumptions and unknowns, iteration identity, predecessor receipt, and a current target-native depth receipt.
- Derive execution-depth, mapping, residual, uncertainty, diagnosability, and predictive gaps from the native receipt instead of accepting caller-declared gap lists.
- Require typed regression, holdout, and predictive receipts to bind the same task, coverage universe, revision, and candidate model identity.
- Treat an observation that matches no hypothesis as a task-model miss, not a physical-cause conclusion or successful closure.
- Compute resolved, persisted, and introduced gaps from base/candidate native receipts; expose exact continuation, stall, iteration-limit, and external-input terminals.
- Update the purpose-contract generator and all ten PhysicsGuard prompts with their native route/check owner and the strict no-self-report loop.
- Add a dedicated FlowGuard task-local-deepening model and complete known-good/known-bad coverage.

## Capabilities

### New Capabilities
- None. The existing task-local hypothesis revision capability is extended.

### Modified Capabilities
- `simulation-validation-depth`: require current task-local model deepening and closure evidence.

## Impact

- `src/physicsguard/schema/task_local_revision.py`, core evaluator, CLI, package exports, purpose-contract generator, ten generated skill prompts/contracts, focused tests, FlowGuard task-local model/manifest, README, changelog, and version sources.
- No new physical component model, external simulator dependency, or generic understanding service.
