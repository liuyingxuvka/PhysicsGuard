## ADDED Requirements

### Requirement: Signal mapping ledger records external-signal provenance
PhysicsGuard SHALL provide a structured signal mapping ledger that maps external signals to PhysicsGuard variables with units, conversion metadata, confidence, review-required status, source locator, snapshot id, and stale conditions.

#### Scenario: Mapping record is loaded
- **WHEN** an observed-values file includes mapping records
- **THEN** PhysicsGuard preserves external signal, target variable, source unit, target unit, conversion factor or offset, mapping confidence, review-required status, source locator, snapshot id, and stale conditions.

### Requirement: Observed values remain backward compatible
PhysicsGuard SHALL keep existing observed-value YAML files valid when they only provide value, unit, source, and description.

#### Scenario: Legacy observed file is evaluated
- **WHEN** a legacy observed-values file is used for hierarchy evaluation
- **THEN** the evaluation still runs and mapping ledger output is empty or marked unavailable rather than failing schema validation.

### Requirement: Hierarchy reports expose mapping warnings
PhysicsGuard hierarchy reports SHALL expose low-confidence, review-required, missing-conversion, and stale mapping warnings when observed data includes mapping provenance.

#### Scenario: Review-required mapping affects diagnosis
- **WHEN** a residual is high and an involved observed variable has a review-required or low-confidence mapping
- **THEN** the report recommends mapping review before treating the residual as model blame.

### Requirement: Bug-family follow-ups connect similar debugging risks
PhysicsGuard SHALL emit bug-family follow-up records for unit, sign, mapping, missing-term, map-axis, and boundary-condition risk classes when available evidence suggests sibling checks.

#### Scenario: Sign-risk follow-up is produced
- **WHEN** a suspicious block or residual involves a feedback, command, actual, gain, sign, or direction mapping cue
- **THEN** PhysicsGuard records a sign or mapping follow-up naming affected variables, block ids, and suggested sibling checks.

## MODIFIED Requirements

### Requirement: Model-code traceability includes signal mapping ownership
PhysicsGuard model-code traceability SHALL include source symbols, tests, examples, and stale conditions for signal mapping ledger and bug-family follow-up behavior.

#### Scenario: Ledger validates mapping ownership
- **WHEN** the model-code ledger check runs after this change
- **THEN** it verifies entries for signal mapping schema/reporting and bug-family follow-up code.
