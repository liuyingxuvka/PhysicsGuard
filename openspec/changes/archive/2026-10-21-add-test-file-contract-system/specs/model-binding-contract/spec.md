## ADDED Requirements

### Requirement: Contract binds to PhysicsGuard model artifacts
PhysicsGuard SHALL provide a model-binding format that records hierarchy or audit file paths, hashes, PhysicsGuard version, compatible profiles, expected variables/parameters, and stale conditions.

#### Scenario: Binding validates hierarchy path
- **WHEN** a model binding references a hierarchy file
- **THEN** contract check verifies the file exists and, when a hash is provided, matches the expected hash.

#### Scenario: Binding lists expected model variables
- **WHEN** parameter coverage maps to model variables or parameters
- **THEN** the check validates those targets against the bound hierarchy/model where possible.

### Requirement: Model changes stale file contracts
PhysicsGuard SHALL mark a contract stale when the bound model artifact or relevant model version changes without a refreshed binding.

#### Scenario: Hierarchy hash changed
- **WHEN** the bound hierarchy file hash differs from the model binding
- **THEN** the contract check reports stale model binding and blocks broad analysis claims.

### Requirement: Model-needed data is checked against file coverage
PhysicsGuard SHALL compare bound model required variables and parameters with test-file coverage where possible.

#### Scenario: Required variable has no source
- **WHEN** the bound hierarchy requires a variable that has no mapped test source, boundary, assumption, or explicit planned/excluded disposition
- **THEN** the contract check reports missing model input coverage.
