# Task-Local Competing Hypotheses

PhysicsGuard does not ask an AI whether it "understands" a model. It asks for
concrete predictions from more than one explanation, picks the observation that
best separates them, and compares that observation with the frozen predictions.

## Commands

1. `physicsguard task-model plan PLAN.yaml` checks a hypothesis plan: purpose,
   the hierarchy YAML the hypotheses are about (`model.path`, which must exist),
   assumptions, unknowns, at least two hypotheses for a non-trivial task, and at
   least one signal, residual, or timing expectation per hypothesis. It ranks the
   declared observation candidates by residual relevance and by how well they
   separate the hypotheses.
2. `physicsguard task-model observe PLAN.yaml OBSERVATION.yaml` compares a later
   observation (`observation_sequence` larger than the plan's
   `prediction_sequence`) with every expectation. Each hypothesis is reported as
   `supported`, `weakened`, or `undetermined`; missing targets stay open. When
   every hypothesis is contradicted the result is `model_miss`: revise the
   hypothesis list instead of inventing a cause.
3. `task-model interval-residual` and `task-model diagnose` keep interval
   uncertainty explicit and recommend the next signal from fault signatures.

Templates for the first two inputs ship with the ai-debugging skill
(`references/templates/hypothesis_plan.yaml` and
`references/templates/diagnostic_observation.yaml`).

The results are task-local. They never identify the true physical cause and do
not change PhysicsGuard itself.
