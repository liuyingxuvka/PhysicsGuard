## Context

The current PhysicsGuard owner already requires signal/residual/timing expectations, at least two hypotheses for non-trivial work, regression and holdout checks, and rollback identity. The missing piece is an outer continuation decision that consumes the existing execution-depth gaps.

## Goals / Non-Goals

**Goals:**

- Bind each hypothesis plan to task purpose, coverage universe, assumptions, unknowns, and prior iteration.
- Carry open/resolved/introduced gap ids through observation and candidate revision.
- Prevent a pointwise match or optimizer success from licensing a deeper physical claim.
- Keep all evidence JSON-serializable, SI-aware, low-fidelity, and explicit about limits.

**Non-Goals:**

- No commercial simulator integration or real physical component model.
- No probability invention, self-reported understanding, or online change to PhysicsGuard algorithms.
- No second plan-observation-revision owner.

## Decisions

1. Extend the existing Pydantic models; do not create a parallel deepening framework.
2. Add `task_id`, purpose/coverage fingerprints, `assumption_ids`, `declared_unknown_ids`, `iteration_index`, and `prior_plan_fingerprint` to `HypothesisPlanSpec`.
3. Add evidence and requested-observation identity to `DiagnosticObservationSpec`.
4. Add input/resolved/introduced gaps, next actions, and terminal reason to `CandidateModelRevisionSpec`.
5. The evaluator returns continuation whenever native execution depth or predictive rollout still has addressable gaps.

## Risks / Trade-offs

- [Existing fixtures omit new fields] -> current-schema replacement updates fixtures and generated examples together; no compatibility reader.
- [A candidate changes the model but not the proof] -> require exact candidate identity and current regression/holdout/predictive receipts.
- [Missing external signals look like model failure] -> classify them as `external_input_required` with the exact signal and owner boundary.

## Migration Plan

Finish the remaining validation-adequacy maintenance tasks first, implement the schema/evaluator changes, regenerate prompts, run focused tests, then regenerate local consumer projections. Roll back by retaining the previous task-local model revision, not by changing core rules.
