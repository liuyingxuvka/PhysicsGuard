## ADDED Requirements

### Requirement: Append-Only Database History

Database mutations SHALL append history events describing event type, timestamp,
actor, target project or artifact, reason, affected paths, before/after state,
and whether the event came from dry-run or apply execution.

#### Scenario: Project admitted

- **WHEN** a project is admitted into the catalog with apply intent
- **THEN** a project-admitted history event SHALL be appended.

### Requirement: No Silent Deletion

Project removal SHALL default to archive, deprecate, supersede, or reject
records rather than silently deleting project history.

#### Scenario: Project archived

- **WHEN** a project is archived
- **THEN** the catalog SHALL retain a project card with archived state or an
  archive record
- **AND** history SHALL record the archive reason and previous state.

#### Scenario: Superseded project

- **WHEN** one project replaces another
- **THEN** the old project SHALL record its superseding project ID or explicit
  unknown reason.
