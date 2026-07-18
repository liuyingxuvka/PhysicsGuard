## Context

PhysicsGuard currently has two relevant native paths. The hierarchy evaluator consumes observed values, computes physical residuals, ranks suspicious blocks, and emits rule-based refinement recommendations. Separately, predictive-rollout validation compares an externally generated stateful trajectory with a disjoint future holdout and intentionally does not mutate model state.

The missing layer is a small task-local contract around those owners: hypotheses and their predictions must be frozen before a new observation, the next observation must be selected for both residual relevance and hypothesis discrimination, and a failed prediction may produce a separate candidate task model without overwriting the base. PhysicsGuard's package, skills, bundled runtime, and tests must remain synchronized, but no task episode may alter Guard code, thresholds, or reusable defaults.

## Goals / Non-Goals

**Goals:**

- Represent at least two competing hypotheses for every explicitly non-trivial diagnostic plan.
- Freeze signal, residual, and timing expectations before the corresponding observation sequence.
- Rank candidate observations with a deterministic combination of task-declared residual relevance and hypothesis-discrimination evidence.
- Evaluate observations against frozen expectations and preserve matched, contradicted, and missing results per hypothesis.
- Evaluate a separate task-local candidate artifact as accepted, rejected, or rolled back while proving that the base artifact remains current.
- Consume the existing predictive-rollout receipt when a stateful future trajectory is a required candidate check.

**Non-Goals:**

- Generate domain hypotheses without caller/AI-authored engineering content.
- Infer one universal measurement-value metric or modify physical audit thresholds.
- Automatically edit an external simulator, PhysicsGuard source, reusable model library, or installed user skill.
- Implement meta-learning or promote one task episode into a future default.

## Decisions

### 1. Add one focused task-local schema and evaluator

`physicsguard.schema.task_local_revision` owns strict Pydantic input objects. `physicsguard.core.task_local_revision` owns ordering, expectation comparison, observation ranking, artifact identity checks, and revision disposition. The existing hierarchy and predictive-rollout evaluators remain unchanged.

Alternative: add fields directly to `HierarchySpec`. Rejected because the hierarchy is a reusable physical audit model, while hypotheses and revisions belong to one diagnostic episode.

### 2. Use bounded native expectation kinds

Each hypothesis must declare at least one signal expectation, residual expectation, and timing expectation. Expectations use supported operators such as range, sign, trend, before, after, or simultaneous. The observation contains measured signal values/trends, residual values, and event times. Unsupported semantics block instead of being guessed.

Alternative: accept free-form prediction prose. Rejected because it cannot be compared deterministically and invites hindsight rewriting.

### 3. Freeze with identities and monotonic sequence order

A plan records a model identity and `prediction_sequence`. Every hypothesis binds that sequence. An observation must name the plan and use a strictly larger `observation_sequence`. Content fingerprints are emitted in the receipt. This is a task-local ordering proof, not a wall-clock or external-producer guarantee.

### 4. Combine residual relevance with discrimination without a new global threshold

Every observation candidate declares a residual-relevance score and per-hypothesis predicted outcome labels. Discrimination is derived from the number of distinct live-hypothesis outcomes. A task-local weight pair, summing to one, combines the two. Ties are stable by candidate id. No PhysicsGuard core threshold changes.

Alternative: choose the highest residual only. Rejected because a high-residual signal can leave competing explanations indistinguishable.

### 5. Keep candidate models separate and reversible

Base and candidate artifacts have separate paths, hashes, model ids, and versions. The evaluator verifies both current identities and never writes either artifact. A candidate with all required checks passing is `accepted`; a failed unapplied candidate is `rejected`; a failed candidate marked applied is `rolled_back` only when the declared rollback identity equals the still-current base identity. All failure outcomes report `base_model_preserved: true`.

### 6. Reuse predictive rollout through its existing receipt

A candidate check of kind `predictive_rollout` must consume a current receipt issued by `evaluate_predictive_rollout`; the task-local evaluator checks its status and identity rather than reimplementing trajectory metrics.

## Risks / Trade-offs

- [AI can author weak hypotheses] → Require typed, falsifiable expectations and expose missing/contradicted expectations; do not claim hypothesis quality beyond the declared task model.
- [Sequence numbers can be falsely asserted] → Bind content fingerprints and state the boundary: the receipt proves declared ordering, not external clock provenance.
- [Candidates may pass shallow checks] → Require exact declared inventory equality and at least one regression plus one holdout check; stateful prediction additionally consumes the native rollout receipt.
- [New schema may drift from the bundled runtime] → Copy the current package projection into the repository-owned bundled runtime and compare hashes during validation.

## Migration Plan

1. Add schema, evaluator, CLI commands, exports, and focused fixtures.
2. Update AI-debugging and candidate-model skill guidance.
3. Refresh the PhysicsGuard-owned bundled runtime projection.
4. Run focused tests, the full package suite, OpenSpec verification, FlowGuard project audit, and SkillGuard project/native checks.

Rollback is removal of this unarchived change's files and exports. Existing hierarchy and predictive-rollout behavior remains unchanged throughout.

## Open Questions

None for this bounded implementation. Project-specific hypothesis content and observation costs remain task inputs.
