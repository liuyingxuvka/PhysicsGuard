## ADDED Requirements

### Requirement: Project Intake States

Database project records SHALL support explicit lifecycle/admission states,
including candidate, placeholder, active registered, active validated, active
reusable, blocked, archived, deprecated, superseded, and rejected.

#### Scenario: Candidate is not active evidence

- **WHEN** a project is registered as candidate or placeholder
- **THEN** database maps and queries SHALL show it as incomplete
- **AND** it SHALL NOT count as validated or reusable evidence.

### Requirement: Project-Level PhysicsGuard Admission Gate

Active project admission SHALL check project-level PhysicsGuard requirements:
project adoption record, project evidence registry, project profile basics,
important artifact registration, binding expectations or exemptions, gap-check
status, validation evidence for validated claims, and model-library evidence for
reusable claims.

#### Scenario: Project has no evidence registry

- **WHEN** an intake plan targets active registration but no project evidence
  registry exists and no missing reason is recorded
- **THEN** the intake report SHALL block active admission.

#### Scenario: Project has blocking evidence gaps

- **WHEN** the project evidence registry has blocking gaps
- **THEN** the intake report SHALL allow only candidate, placeholder, or blocked
  state unless the user records a reason and does not claim active readiness.

### Requirement: Explicit Admission Writes

Writing a project into the database catalog SHALL require explicit apply intent
and SHALL append a history event.

#### Scenario: Dry-run admission

- **WHEN** admission is requested without apply intent
- **THEN** the system SHALL return an intake/admission report
- **AND** the catalog SHALL remain unchanged.
