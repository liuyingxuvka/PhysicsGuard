## ADDED Requirements

### Requirement: Database map summarizes catalog state
PhysicsGuard SHALL provide an AI-readable database map report that summarizes
projects, tags, tested quantities, model targets, model-library indexes,
validation state, and open gaps.

#### Scenario: AI enters a database
- **WHEN** an AI agent runs the database map command
- **THEN** the report shows the available projects, what each covers, which
  registries and model libraries to inspect, and what gaps remain.

### Requirement: Database map is navigation, not validation proof
PhysicsGuard SHALL mark database maps as navigation/onboarding artifacts and
not as validation proof or cross-project comparability proof.

#### Scenario: Map lists a validated project
- **WHEN** a project summary says validation exists
- **THEN** the map still points to the validation/project evidence records
  rather than making an independent pass claim.
