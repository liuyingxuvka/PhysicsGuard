# Strict Task-Local Model Deepening

PhysicsGuard does not ask an AI whether it “understands” a model. It treats
understanding as an ability to make a concrete prediction, compare that
prediction with independently identified evidence, expose where the model was
wrong, and improve the model without losing known behavior.

## Existing route, strengthened

The existing `physicsguard task-model` route remains the single current route:

1. `plan` freezes the task purpose, model identity, independently owned
   coverage universe, explicit assumptions and unknowns, competing hypotheses,
   predicted observations, predecessor, and target-owned native depth receipt.
2. `observe` compares later evidence with the frozen predictions. If every
   declared hypothesis is contradicted, the result is `model_miss`; it does not
   invent a cause outside the declared hypothesis space.
3. `revision` compares distinct base and candidate models. It derives gap
   changes from their native receipts and consumes exactly one regression, one
   independent holdout, and one predictive-rollout receipt for the same
   candidate.

This is a strict current contract. Retired optional shapes, compatibility
readers, caller-written gap transitions, and self-reported progress are not
accepted.

## Six native gap families

Every native depth receipt names all six source receipts and may report open
gaps in these families:

- `execution_depth`: the route did not exercise enough of the real model;
- `mapping`: a signal, parameter, unit, or identity binding is incomplete;
- `residual`: a required physical or behavioral comparison is absent;
- `uncertainty`: a range, assumption, or sensitivity boundary is unresolved;
- `diagnosability`: competing explanations cannot yet be separated;
- `predictive_rollout`: future-state behavior or stability evidence is absent.

PhysicsGuard compares the base and candidate native receipts to derive
`resolved`, `persisted`, and `introduced` gaps. Deleting or renaming a gap in
AI-authored text is therefore not progress.

## Closure rule

`model_closed_for_task` is available only when all of these are true:

- the exact candidate identity is current and distinct from the base;
- the candidate native depth receipt contains no open gap;
- regression passes for that candidate;
- an evidence group independent from candidate construction passes holdout;
- the native predictive rollout passes for that same candidate.

Otherwise the receipt preserves one visible boundary such as
`continue_iteration`, `model_miss`, `external_input_required`,
`scope_excluded`, `progress_stalled`, or `iteration_limit`. A non-success
result explains the next action; it is not silently converted into closure.

This workflow proves only the declared task-local model and evidence boundary.
It does not prove that an external source is true or that the low-fidelity
candidate is the full physical system.
