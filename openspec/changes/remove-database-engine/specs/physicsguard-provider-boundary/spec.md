## ADDED Requirements

### Requirement: PhysicsGuard remains a provider of physical evidence
PhysicsGuard SHALL retain ownership of test-file facts, units, parameter roles,
signal mapping, model binding, physical models, residual validation, model
dataset validation, model-library evidence, project evidence registries, and
project closure reports.

#### Scenario: Project evidence remains available
- **WHEN** a project evidence registry is checked after database engine removal
- **THEN** PhysicsGuard still validates the provider evidence without requiring
  a database ledger

### Requirement: Database-ledger work is outside PhysicsGuard
Current PhysicsGuard docs and skills SHALL describe database-ledger ownership as
external to PhysicsGuard without preserving old PhysicsGuard database commands.

#### Scenario: Current docs do not teach old commands
- **WHEN** current README and skill files are searched for
  `python -m physicsguard.cli database`
- **THEN** no current user-facing command instructions remain
