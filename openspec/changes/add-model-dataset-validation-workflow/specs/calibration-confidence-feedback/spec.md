## ADDED Requirements

### Requirement: Calibration is conservative and bounded
PhysicsGuard SHALL support first-version calibration only for explicit bounded
calibration parameters and SHALL NOT calibrate observed values.

#### Scenario: Calibration parameter missing bounds
- **WHEN** calibration is enabled and a parameter lacks finite lower bound,
  upper bound, initial value, or positive scale
- **THEN** validation fails before optimization.

### Requirement: Optimizer convergence is not validation pass
PhysicsGuard SHALL report `optimization_success` separately from
`validation_status` and `audit_pass`.

#### Scenario: Parameter hits bound
- **WHEN** a calibrated parameter ends at or near a finite bound
- **THEN** the report emits a warning and does not use that fact alone to
  support broad validation claims.

### Requirement: Validation emits confidence feedback
PhysicsGuard SHALL emit confidence update records from validation evidence
without mutating source contracts.

#### Scenario: Sensor violates envelope
- **WHEN** a source repeatedly violates a physical or measurement envelope
- **THEN** validation output may lower validation confidence and require review.
