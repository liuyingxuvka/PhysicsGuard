# physics-model-deepening Specification

## ADDED Requirements

### Requirement: A non-trivial plan carries purpose and coverage identity

Every non-trivial `HypothesisPlanSpec` SHALL bind a task purpose, independent coverage-universe fingerprint, assumptions/unknowns, and iteration identity.

#### Scenario: Missing purpose blocks depth
- **GIVEN** a plan has competing hypotheses but no current purpose or coverage binding
- **WHEN** task-local depth is evaluated
- **THEN** the result is blocked and cannot license localization or prediction

### Requirement: Native depth gaps force continuation

`evaluate_hypothesis_observation()` and `evaluate_candidate_model_revision()` SHALL expose addressable execution-depth, mapping, residual, uncertainty, diagnosability, and predictive-rollout gaps as required next actions.

#### Scenario: Pointwise match with shallow depth
- **GIVEN** observed signals match the frozen expectations
- **AND** native depth still reports a missing time-varying or holdout obligation
- **WHEN** the candidate is evaluated
- **THEN** it remains non-terminal with `next_iteration_required=true`

### Requirement: Candidate revisions preserve exact evidence identity

Every candidate revision SHALL bind base/candidate model identities, gap transitions, regression and holdout checks, and any required predictive receipt to the same candidate fingerprint.

#### Scenario: Stale candidate evidence
- **GIVEN** a candidate file changed after its receipt was produced
- **WHEN** revision closure is evaluated
- **THEN** the revision is blocked and cannot be applied

### Requirement: Physical model limits remain visible

Missing external signals, unsupported validity ranges, and indistinguishable hypotheses SHALL remain explicit terminal blockers; the evaluator SHALL not invent values or select a hypothesis by prose.

#### Scenario: All predictions disagree with an observation
- **GIVEN** a real observation matches none of the declared hypotheses
- **WHEN** the iteration is evaluated
- **THEN** it creates a model-gap revision action and does not declare a physical cause
