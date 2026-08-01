## Context

The current PhysicsGuard owner already requires signal/residual/timing expectations, at least two hypotheses for non-trivial work, regression and holdout checks, and rollback identity. The missing piece is an outer continuation decision that consumes the existing execution-depth gaps.

## Goals / Non-Goals

**Goals:**

- Bind each hypothesis plan to task purpose, independently owned coverage universe, assumptions, unknowns, and an exact predecessor receipt.
- Derive open/resolved/persisted/introduced gap ids from immutable target-native receipts instead of caller declarations.
- Prevent a pointwise match or optimizer success from licensing a deeper physical claim.
- Keep all evidence JSON-serializable, SI-aware, low-fidelity, and explicit about limits.

**Non-Goals:**

- No commercial simulator integration or real physical component model.
- No probability invention, self-reported understanding, or online change to PhysicsGuard algorithms.
- No second plan-observation-revision owner.

## Decisions

1. Extend the existing Pydantic models; do not create a parallel deepening framework.
2. `HypothesisPlanSpec` has one current shape. Non-trivial plans require `task_id`, `purpose`, a `CoverageUniverseSpec` with an independent owner/fingerprint, explicit `assumptions` and `unknowns`, iteration, predecessor receipt, and a current `NativeDepthReceiptSpec` bound to the base model.
3. `DiagnosticObservationSpec` binds the exact frozen-plan fingerprint, selected observation candidate, task identity, and immutable observation evidence. It cannot supply its own gap transitions.
4. `NativeDepthReceiptSpec` has exactly six source families: execution depth, mapping, residual, uncertainty, diagnosability, and predictive rollout. The evaluator consumes only the gaps in this current receipt.
5. `CandidateModelRevisionSpec` binds base and candidate native depth receipts plus typed regression, holdout, and predictive receipts. Every check receipt binds the same task, plan, revision, coverage fingerprint, and candidate SHA-256.
6. The evaluator computes gap transitions by set difference. A renamed/deleted caller list is impossible because there is no caller transition field.
7. Closure requires current identities, an empty candidate-native gap set, and all three current check receipts. Otherwise the exact terminal is derived: external input, model miss, progress stalled, iteration limit, or continue iteration.
8. A zero-surviving-hypothesis observation emits `model_miss:observation_outside_hypothesis_space` and requests hypothesis/model revision.
9. Every maintained skill's `depth_profile.model_deepening_check_id` points to its own strict task-local runtime/negative-test check, which is also present in `native_check_ids`; the suite mesh rejects a missing or foreign binding.

## Risks / Trade-offs

- [Existing fixtures omit new fields] -> current-schema replacement updates fixtures and generated examples together; no compatibility reader, alias, or default.
- [A candidate changes the model but not the proof] -> require exact candidate identity and current regression/holdout/predictive receipts.
- [Missing external signals look like model failure] -> classify them as `external_input_required` with the exact signal and owner boundary.
- [A caller fabricates progress] -> compute gap transitions from two fingerprinted native receipts and require at least one resolved gap for progress.
- [A few prompts remain shallow] -> generate the strict loop into all ten maintained skills and assert every native owner/route/check binding in tests.
- [A profile names only an abstract model check] -> require the exact runtime/negative-test owner through `model_deepening_check_id` and check that binding in the source mesh.

## Migration Plan

Implement the strict schema/evaluator as a direct current replacement, regenerate prompts/contracts, run focused tests and affected FlowGuard model checks, then let the parent integration owner run the frozen SkillGuard/full-suite/install/release sequence. Roll back a failed task candidate by retaining the exact previous task-local model artifact; do not restore the retired optional schema.
