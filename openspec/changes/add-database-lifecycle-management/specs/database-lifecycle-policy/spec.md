## ADDED Requirements

### Requirement: Explicit Database Policy

A PhysicsGuard database SHALL have an explicit policy artifact that defines the
database name, scope, owner/maintainer notes, raw-data policy, admission policy,
write policy, archive policy, required lifecycle artifacts, and PhysicsGuard
repository reference.

#### Scenario: Missing policy blocks lifecycle pass

- **WHEN** a database lifecycle audit runs without a policy artifact
- **THEN** the audit SHALL report a blocking gap
- **AND** the database SHALL NOT be described as fully governed.

#### Scenario: Policy references PhysicsGuard

- **WHEN** a policy is present
- **THEN** it SHALL include a PhysicsGuard repository URL or explicit unknown
  reason
- **AND** it SHALL distinguish users/AI agents with PhysicsGuard installed from
  agents that can only read Markdown/YAML.

### Requirement: Required Lifecycle Artifacts

A database lifecycle check SHALL account for README, status, catalog, policy,
history, maintenance report, and model-template index artifacts.

#### Scenario: Optional artifact is missing

- **WHEN** a non-critical lifecycle artifact is missing
- **THEN** the audit SHALL report a review or optional gap
- **AND** it SHALL name the missing artifact and suggested creation action.
