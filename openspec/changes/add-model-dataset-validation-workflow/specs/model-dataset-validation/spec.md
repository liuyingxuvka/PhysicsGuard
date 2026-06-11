## ADDED Requirements

### Requirement: Model-dataset validation follows passing contracts
PhysicsGuard SHALL require passing test-file contracts before broad
model-dataset validation claims.

#### Scenario: Contract failed
- **WHEN** a validation plan references a failing contract
- **THEN** validation output is blocked or partial and broad validation claims
  are not allowed.

### Requirement: Direct no-fit validation runs before calibration
PhysicsGuard SHALL run direct observed residual, physical envelope, and
redundant-sensor checks before optional calibration.

#### Scenario: Direct validation fails
- **WHEN** direct validation finds residual, envelope, or sensor consistency
  failures
- **THEN** the report records those failures before any calibration result.

### Requirement: Validation reports separate evidence states
PhysicsGuard SHALL report direct audit status, calibration optimizer status,
holdout audit status, final validation status, safe claim, unsafe claim
boundary, and next actions separately.

#### Scenario: Optimizer succeeds but holdout fails
- **WHEN** calibration converges but holdout validation fails
- **THEN** final validation status is not `pass`.
