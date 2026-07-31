## ADDED Requirements

### Requirement: Observations preserve interval uncertainty

PhysicsGuard SHALL retain lower and upper bounds, inclusivity, unit, provenance, and execution state for every diagnosability observation.

#### Scenario: Observation is missing

- **WHEN** a required signal was not supplied
- **THEN** PhysicsGuard SHALL record `missing` and SHALL NOT substitute zero or a point estimate

#### Scenario: Units are incompatible

- **WHEN** observed and predicted intervals use non-convertible units
- **THEN** the comparison SHALL be blocked with a unit diagnostic

### Requirement: Robust terminals reflect the full interval

PhysicsGuard SHALL determine pass or fail only when the declared relation holds uniformly across the full compatible interval.

#### Scenario: Every value passes

- **WHEN** the entire observed interval satisfies the declared acceptance relation
- **THEN** the result SHALL be `robust_pass`

#### Scenario: Every value fails

- **WHEN** the entire observed interval violates the declared acceptance relation
- **THEN** the result SHALL be `robust_fail`

#### Scenario: Pass and fail overlap

- **WHEN** the interval crosses the acceptance boundary
- **THEN** the result SHALL be `indeterminate`

### Requirement: Indistinguishable hypotheses remain visible

PhysicsGuard SHALL group hypotheses that share the same current discriminator signature and SHALL preserve the group until new evidence separates it.

#### Scenario: Candidates share a current fault signature

- **WHEN** two or more hypotheses cannot be separated by current discriminators
- **THEN** PhysicsGuard SHALL report one diagnosability class and SHALL NOT choose a unique fault

### Requirement: The next signal maximizes declared discrimination safely

PhysicsGuard SHALL rank only caller-declared feasible signals using explicit discrimination, risk, and acquisition-cost inputs.

#### Scenario: A feasible signal splits the largest class

- **WHEN** candidate signals have declared partitions, costs, and risks
- **THEN** PhysicsGuard SHALL rank by partition gain, then risk and cost, and SHALL preserve ties
