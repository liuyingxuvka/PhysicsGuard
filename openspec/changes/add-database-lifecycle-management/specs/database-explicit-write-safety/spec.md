## ADDED Requirements

### Requirement: Lifecycle Writes Require Apply Intent

Lifecycle commands SHALL require explicit write intent when they initialize,
admit, archive, deprecate, supersede, reject, restore, or render persistent
database artifacts.

#### Scenario: No apply flag

- **WHEN** a lifecycle command is run without apply intent
- **THEN** it SHALL produce a dry-run report
- **AND** it SHALL not mutate catalog, policy, history, README, status, or
  maintenance files.

### Requirement: Mutations Report Written Files

Applied lifecycle commands SHALL return machine-readable reports that list
written files and appended history events.

#### Scenario: Applied archive

- **WHEN** a project archive command succeeds
- **THEN** the report SHALL list the updated catalog and history file
- **AND** it SHALL include the previous and new lifecycle state.
