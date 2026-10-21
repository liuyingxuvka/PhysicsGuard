## Why

PhysicsGuard can localize residuals and validate an externally produced predictive rollout, but an ordinary non-trivial diagnosis does not yet freeze competing explanations before new observations or turn a failed prediction into a reversible task-local model revision. This change closes that task-local loop without changing PhysicsGuard's core thresholds or teaching the Guard to rewrite itself.

## What Changes

- Require non-trivial diagnostic plans to contain at least two competing hypotheses, each with frozen signal, residual, and timing predictions plus explicit weakening conditions.
- Rank the next observation by both residual relevance and its declared ability to distinguish the live hypotheses.
- Reuse the existing predictive-rollout evaluator for stateful future trajectories; do not add a second rollout engine.
- Add a task-local candidate-model revision contract with a restricted revision taxonomy, base/candidate identities, triggering mismatch, required replay and holdout checks, and explicit accept, reject, or rollback disposition.
- Preserve the base model unchanged until the candidate passes every declared check; a rejected candidate must leave v1 reusable.
- Expose the workflow through native CLI commands, PhysicsGuard skill guidance, bundled runtime projection, and focused regression tests.
- Keep all learning inside the current task. Do not modify Guard code, default policy, core thresholds, or reusable model-library defaults from an episode.

## Capabilities

### New Capabilities

- `task-local-hypothesis-revision`: Competing-hypothesis prediction freezing, discriminating observation selection, mismatch recording, and reversible task-model candidate revision.

### Modified Capabilities

None.

## Impact

- New task-local schemas and evaluator logic under `src/physicsguard/schema/` and `src/physicsguard/core/`.
- Native CLI JSON commands and package exports.
- PhysicsGuard AI-debugging and candidate-model skill guidance plus the bundled runtime used by the installed projection.
- Focused hypothesis, observation-selection, candidate acceptance, rejection, rollback, and predictive-rollout integration tests.
- No package release, installed-skill write, global-router refresh, reusable model promotion, or core-threshold change.
