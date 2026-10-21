## ADDED Requirements

### Requirement: Parameter catalog accounts every manifest field
PhysicsGuard SHALL compare Data File Manifest fields with a parameter catalog and fail when required source fields are missing from the catalog.

#### Scenario: Manifest field missing from catalog
- **WHEN** a manifest field is not represented in the parameter catalog and is not ignored by explicit policy
- **THEN** coverage check fails with an unregistered field finding.

### Requirement: Role matrix separates identity from contextual roles
PhysicsGuard SHALL support multi-view role assignments for each parameter rather than a single mutually exclusive label.

#### Scenario: Command and readback fields
- **WHEN** a test file has both command and measured readback fields
- **THEN** role matrix can classify command, measurement, physical role, model role, owner block, and verification role separately.

### Requirement: Mapping edges connect test fields to model surfaces
PhysicsGuard SHALL represent relationships from test parameters to PhysicsGuard variables, parameters, hierarchy blocks, residuals, post-checks, derived quantities, aggregates, mode gates, and explicit exclusions.

#### Scenario: Mapping target is unknown
- **WHEN** a mapping edge points to a nonexistent PhysicsGuard variable, parameter, block, residual, or post-check
- **THEN** coverage check fails with an unknown target finding.

### Requirement: Every parameter has explicit disposition
PhysicsGuard SHALL fail-closed when a cataloged parameter lacks role assignment, mapping, planned child-model status, review status, or excluded-with-reason disposition.

#### Scenario: Parameter has no disposition
- **WHEN** a parameter is cataloged but has no role or mapping disposition
- **THEN** coverage check fails and blocks broad analysis claims.

#### Scenario: Parameter is excluded
- **WHEN** a parameter is excluded from model coverage
- **THEN** it must include an explicit reason and the report must count it separately from covered parameters.

### Requirement: Coverage reports summarize completeness
PhysicsGuard SHALL emit machine-readable coverage summaries with counts for manifest fields, catalog entries, classified entries, mapped entries, checked entries, excluded entries, review-required entries, stale entries, and uncovered entries.

#### Scenario: Coverage report generated
- **WHEN** a coverage check runs
- **THEN** output includes summary counts and findings suitable for AI consumption.
