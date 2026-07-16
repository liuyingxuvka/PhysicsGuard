## ADDED Requirements

### Requirement: Exact dataset identity
PhysicsGuard SHALL bind every validation claim to the exact dataset files, content hashes, testbench version, field schema, and parameter roles used.

#### Scenario: Dataset changes after validation
- **WHEN** a bound file or schema changes after a receipt
- **THEN** that receipt SHALL be stale

### Requirement: Current mapping gate
Validation MUST consume a current signal-mapping review with units, confidence, unresolved mappings, and reviewer status.

#### Scenario: Required signal is uncertain
- **WHEN** a required signal mapping is unresolved or unit evidence is missing
- **THEN** broad validation SHALL be blocked or bounded to unaffected relations

### Requirement: Time and scenario scope
PhysicsGuard SHALL report whether evidence is a scalar snapshot, a time window, or a declared scenario set and MUST NOT silently extrapolate between scopes.

#### Scenario: Snapshot only
- **WHEN** only one timestamp is evaluated
- **THEN** the receipt SHALL identify snapshot scope and SHALL NOT claim time-series behavior

### Requirement: Disjoint calibration and holdout identity
When calibration is enabled, training and holdout evidence MUST be identity-disjoint.

#### Scenario: Same data under different labels
- **WHEN** train and holdout labels refer to identical content or case ids
- **THEN** holdout validation SHALL fail with an overlap finding

### Requirement: Residual-series and envelope evidence
Time-series validation SHALL preserve pointwise residual results, missing/invalid intervals, physical envelope violations, and aggregate statistics.

#### Scenario: Short violation hidden by average
- **WHEN** average residual passes but a bounded interval violates a hard physical envelope
- **THEN** audit pass SHALL be false or explicitly partial according to the relation contract

### Requirement: Native validation-depth receipt
PhysicsGuard SHALL emit a receipt bound to dataset, mapping, time, scenario, split, residual, envelope, assumptions, report hash, report type, and pass/partial/block status.

#### Scenario: SkillGuard supervision
- **WHEN** SkillGuard evaluates PhysicsGuard execution depth
- **THEN** it SHALL consume the native receipt and SHALL NOT recompute physical residuals
