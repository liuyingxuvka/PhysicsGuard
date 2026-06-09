## ADDED Requirements

### Requirement: Project Adoption Record
PhysicsGuard SHALL provide a project adoption record that identifies the PhysicsGuard repository, installed package version, schema version, rule path, adoption log path, module ledger path, and workflow policy for a target project.

#### Scenario: Adopt current project
- **WHEN** a user runs the PhysicsGuard project adoption command in a repository
- **THEN** the repository contains a machine-readable PhysicsGuard project record and a human-readable adoption log path.

### Requirement: Project Audit
PhysicsGuard SHALL provide a read-only project audit that reports whether the project record is present, version fields are current, expected files exist, and required policy fields are readable.

#### Scenario: Audit adopted project
- **WHEN** a user runs the PhysicsGuard project audit command in an adopted project
- **THEN** the command reports pass when the record, version, rules, log, and configured ledger paths are present.

#### Scenario: Audit missing project record
- **WHEN** a user runs the PhysicsGuard project audit command in a project without a PhysicsGuard record
- **THEN** the command reports a non-passing status and names the missing record.
