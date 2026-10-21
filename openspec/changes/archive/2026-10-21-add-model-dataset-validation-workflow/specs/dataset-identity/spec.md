## ADDED Requirements

### Requirement: Logical dataset records preserve raw-data references
PhysicsGuard SHALL provide logical dataset records that reference file
representation manifests without moving raw data files.

#### Scenario: Logical dataset references a manifest
- **WHEN** a logical dataset record is checked
- **THEN** PhysicsGuard verifies the referenced manifest exists and records the
  dataset id, representation manifest references, raw-data policy, and optional
  signatures.

### Requirement: Non-identical test files keep symmetric contracts
PhysicsGuard SHALL avoid parent/child base-delta contract relationships between
non-identical test data files.

#### Scenario: Related files are not identical
- **WHEN** two files have different value fingerprints or logical dataset ids
- **THEN** each file keeps its own contract while shared artifacts may be
  referenced independently.

### Requirement: Project relation indexes express file relationships
PhysicsGuard SHALL provide relation indexes that record same-test, same
testbench, redundant-sensor, fallback-sensor, equivalent-format, and
review-required relationships outside individual contracts.

#### Scenario: Redundant sensors map to one target
- **WHEN** two source fields measure the same physical target
- **THEN** the relation index may record their relationship without merging
  their source identities.
