# physics-model-deepening Specification

## Purpose
Keep a non-trivial PhysicsGuard diagnosis honest: competing hypotheses with expectations, the most discriminating next observation, and a visible model miss when the observation contradicts every hypothesis.

## Requirements
### Requirement: Competing hypotheses carry expectations
`task-model plan` SHALL accept a plan only when each hypothesis declares at least one signal, residual or timing expectation, and SHALL report `blocked` while the model file named in the plan does not exist.

#### Scenario: The model file is missing
- **WHEN** `model.path` names a file that does not exist
- **THEN** the plan status SHALL be `blocked` and the command SHALL exit 1

#### Scenario: A plan uses the retired receipt fields
- **WHEN** a plan still carries `blueprint`, `coverage`, `native_depth_receipt` or `predecessor`
- **THEN** validation SHALL reject it

### Requirement: The next observation is the most discriminating one
`task-model plan` SHALL rank observation candidates by residual relevance and by how differently the live hypotheses predict them.

#### Scenario: Two candidates are equally relevant
- **WHEN** two candidates have the same residual relevance
- **THEN** the one whose predicted outcomes separate the live hypotheses SHALL rank first

### Requirement: Observations are compared with frozen predictions
`task-model observe` SHALL compare an observation with the predictions frozen in the plan, keep supported, weakened and undetermined hypotheses, and SHALL NOT rewrite an old prediction.

#### Scenario: The observation contradicts every hypothesis
- **WHEN** every live hypothesis is contradicted
- **THEN** the terminal reason SHALL be `model_miss` and the command SHALL exit 1

#### Scenario: An expected target is not observed
- **WHEN** an expected target is missing from the observation
- **THEN** it SHALL stay undetermined and open and SHALL NOT count as support
