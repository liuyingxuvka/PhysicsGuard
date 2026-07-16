## ADDED Requirements

### Requirement: Explicit model semantics
Every validation-depth receipt SHALL identify the model semantics as `pointwise` or `stateful_dynamic`; pointwise evidence MUST NOT authorize trajectory prediction.

#### Scenario: Pointwise prediction request
- **WHEN** a pointwise plan or receipt requests a predictive claim
- **THEN** PhysicsGuard SHALL block the claim with `pointwise_prediction_forbidden`

### Requirement: Future-holdout rollout identity
A predictive claim MUST bind exact training identities, an identity-disjoint future holdout, an exact predicted-series artifact, model identity, initial state, step size/unit, horizon, signal scales, and threshold source.

#### Scenario: Training and future holdout overlap
- **WHEN** training and future-holdout evidence overlap by resolved path, content hash, or case id
- **THEN** predictive rollout SHALL be blocked

#### Scenario: Prediction and holdout are not aligned
- **WHEN** timestamps, horizon, required targets, units, or step size cannot be aligned
- **THEN** predictive rollout SHALL be blocked with the alignment gaps

### Requirement: Predictive rollout metrics
PhysicsGuard SHALL compare the predicted trajectory with the future holdout and preserve worst-step normalized error, accumulated normalized error, lag steps, phase error, drift, and error-growth stability against declared thresholds.

#### Scenario: Good future rollout
- **WHEN** a stateful dynamic rollout is identity-current, disjoint, aligned, and all predictive metrics meet their thresholds
- **THEN** PhysicsGuard SHALL emit a passing target-owned predictive rollout receipt bounded to that exact horizon

#### Scenario: Drift hidden by average
- **WHEN** average point error is small but end-of-horizon drift or error growth exceeds its threshold
- **THEN** predictive rollout SHALL fail or remain partial and SHALL NOT authorize prediction

### Requirement: Prediction-ready closure
A `prediction_ready` project closure request MUST require both a passing stateful-dynamic predictive rollout receipt and passing validation adequacy; no other evidence combination SHALL satisfy it.

#### Scenario: Pointwise receipt enters prediction closure
- **WHEN** project closure requests `prediction_ready` with only pointwise or non-predictive evidence
- **THEN** closure SHALL block without recomputing the rollout

#### Scenario: Predictive receipt is stale or partial
- **WHEN** the prediction, holdout, model, threshold, or receipt identity changed or the predictive status is not pass
- **THEN** closure SHALL block the predictive claim
