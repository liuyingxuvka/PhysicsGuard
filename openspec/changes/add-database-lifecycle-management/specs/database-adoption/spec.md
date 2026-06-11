## ADDED Requirements

### Requirement: Explicit Database Initialization

The system SHALL support initializing an explicit local PhysicsGuard database
root with database policy, catalog, history, maintenance, model-template, README,
and status artifacts.

#### Scenario: Dry-run initialization

- **WHEN** a user requests database initialization without apply intent
- **THEN** the system SHALL report which files would be created
- **AND** it SHALL NOT write database artifacts.

#### Scenario: Applied initialization

- **WHEN** a user requests database initialization with explicit apply intent
- **THEN** the system SHALL create missing lifecycle artifacts
- **AND** it SHALL append a database-created history event
- **AND** it SHALL avoid overwriting existing files unless explicitly requested.

### Requirement: Database Initialization Does Not Scan Whole Computer

Database initialization SHALL operate on the user-provided database root and
SHALL NOT silently scan or index unrelated local machine paths.

#### Scenario: No root provided

- **WHEN** initialization is requested without a database root
- **THEN** the command SHALL fail or ask for a root rather than using a hidden
  global database.
