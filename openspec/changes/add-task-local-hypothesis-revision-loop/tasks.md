## 1. Native Task-Local Contracts

- [x] 1.1 Add strict schemas for model identity, competing hypotheses, frozen signal/residual/timing expectations, observation candidates, and observations
- [x] 1.2 Add schemas for separate candidate-model revisions, declared check inventory, existing predictive-rollout receipt consumption, and accept/reject/rollback output

## 2. Evaluation And CLI

- [x] 2.1 Implement deterministic plan validation, observation ranking, and frozen expectation comparison without changing PhysicsGuard thresholds
- [x] 2.2 Implement current base/candidate identity checks and reversible revision disposition with v1 preservation
- [x] 2.3 Add native CLI commands and public package exports for plan, observation, and candidate-revision evaluation

## 3. Skill And Runtime Projection

- [x] 3.1 Update PhysicsGuard AI-debugging and candidate-model guidance for the independent task-local loop
- [x] 3.2 Synchronize the repository-owned bundled PhysicsGuard runtime and its content manifest or contract projection

## 4. Verification

- [x] 4.1 Add focused positive and negative tests for competing hypotheses, prediction ordering, discriminating selection, mismatch results, and revision acceptance/rejection/rollback
- [x] 4.2 Add a test proving the candidate evaluator consumes the existing predictive-rollout receipt without replacing its metrics
- [x] 4.3 Run focused tests, full tests, OpenSpec verification, FlowGuard project audit, and SkillGuard project/native checks; fix every in-scope failure and retain the pre-existing project-id plus intentionally unsynchronized installed-skill boundaries as explicit blockers
