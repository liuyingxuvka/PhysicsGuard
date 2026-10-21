## ADDED Requirements

### Requirement: Non-trivial diagnosis has competing hypotheses
The system SHALL reject a non-trivial diagnostic plan unless it contains at least two uniquely identified hypotheses, and every hypothesis MUST contain at least one signal, residual, and timing expectation.

#### Scenario: One hypothesis cannot start a non-trivial diagnosis
- **WHEN** a non-trivial diagnostic plan contains only one hypothesis
- **THEN** validation fails before an observation is selected

#### Scenario: Competing hypotheses are accepted
- **WHEN** a non-trivial plan contains two uniquely identified hypotheses with all required expectation kinds
- **THEN** the system creates a fingerprinted frozen prediction-plan receipt

### Requirement: Predictions precede observations
The system SHALL bind every hypothesis prediction to the plan's model identity and prediction sequence, and MUST reject an observation whose sequence is not strictly later than the frozen prediction sequence.

#### Scenario: Observation arrives after prediction
- **WHEN** an observation names the frozen plan and has a greater observation sequence
- **THEN** the system compares it with the frozen expectations

#### Scenario: Hindsight observation is blocked
- **WHEN** an observation sequence is equal to or earlier than the prediction sequence
- **THEN** the system rejects the comparison without rewriting the predictions

### Requirement: Observation selection combines residual relevance and discrimination
The system SHALL rank each observation candidate from its task-declared residual relevance and a discrimination score derived from distinct predicted outcomes across live hypotheses. The weights MUST be finite, non-negative, and sum to one.

#### Scenario: Discriminating signal outranks a residual-only tie
- **WHEN** two candidates have equal residual relevance but one separates more live-hypothesis outcomes
- **THEN** the more discriminating candidate ranks first

#### Scenario: Invalid weights are rejected
- **WHEN** task-local selection weights do not sum to one
- **THEN** the plan is rejected without changing PhysicsGuard thresholds

### Requirement: Frozen expectations produce hypothesis outcomes
The system SHALL compare measured signal values or trends, residual values, and timing observations with the supported frozen expectation operators and SHALL report matched, contradicted, and missing expectation ids for every hypothesis.

#### Scenario: Observation weakens one hypothesis
- **WHEN** a measured signal or residual contradicts one hypothesis while matching another
- **THEN** the receipt marks the first hypothesis weakened and preserves the second as live

#### Scenario: Missing measurement remains visible
- **WHEN** an expected target is absent from the observation
- **THEN** the expectation is reported missing rather than treated as matched or contradicted

### Requirement: Candidate revision is separate from the base model
The system SHALL require distinct current base and candidate artifact identities and MUST NOT overwrite the base artifact while evaluating a task-local revision.

#### Scenario: Candidate passes every declared check
- **WHEN** the candidate artifact is current and every required regression, holdout, and applicable predictive-rollout check passes
- **THEN** the revision disposition is accepted and the base identity remains recorded

#### Scenario: Unapplied candidate fails
- **WHEN** any required check fails before the candidate is applied
- **THEN** the candidate is rejected and `base_model_preserved` is true

#### Scenario: Applied candidate fails and rolls back
- **WHEN** any required check fails after candidate application and the rollback identity equals the still-current base
- **THEN** the disposition is rolled back and v1 remains the authoritative task model

### Requirement: Predictive rollout remains natively owned
The system SHALL consume an existing PhysicsGuard predictive-rollout receipt for a stateful trajectory check and MUST NOT recompute or weaken its trajectory thresholds.

#### Scenario: Passing predictive receipt supports candidate acceptance
- **WHEN** a declared predictive-rollout check references a current native receipt with status `pass`
- **THEN** that exact check may satisfy the candidate inventory

#### Scenario: Failed predictive receipt blocks candidate acceptance
- **WHEN** the native predictive-rollout receipt is failed, blocked, stale, or missing
- **THEN** the candidate cannot be accepted

### Requirement: Learning remains task-local
The system SHALL limit automatic changes to the current task model and MUST NOT alter PhysicsGuard source, default thresholds, reusable model-library entries, or installed user skills.

#### Scenario: Episode ends
- **WHEN** a candidate is accepted, rejected, or rolled back
- **THEN** only the task-local receipt and task-model identities change
