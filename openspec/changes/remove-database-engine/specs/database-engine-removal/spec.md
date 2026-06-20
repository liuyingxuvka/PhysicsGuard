## ADDED Requirements

### Requirement: PhysicsGuard database CLI is removed
PhysicsGuard SHALL NOT expose a `database` command group from
`python -m physicsguard.cli`.

#### Scenario: Database CLI help is unavailable
- **WHEN** a user runs `python -m physicsguard.cli database --help`
- **THEN** the command fails because `database` is not a recognized command

### Requirement: PhysicsGuard database engine code is removed
PhysicsGuard SHALL NOT contain active database catalog/lifecycle engine modules,
schemas, templates, examples, tests, or public package exports.

#### Scenario: Package imports without database engine exports
- **WHEN** Python imports `physicsguard`
- **THEN** no database catalog/lifecycle functions or schemas are exported from
  the package root

### Requirement: No fallback or bridge command remains
PhysicsGuard SHALL NOT preserve aliases, bridge commands, compatibility
wrappers, or fallback text for removed database control paths.

#### Scenario: Old command is not redirected
- **WHEN** the removed database command is requested
- **THEN** PhysicsGuard does not invoke DataBank, does not translate arguments,
  and does not continue through an alternate database path
