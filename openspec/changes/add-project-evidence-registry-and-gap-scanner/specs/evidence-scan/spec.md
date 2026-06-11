## ADDED Requirements

### Requirement: Evidence scan reports candidate registrations
PhysicsGuard SHALL provide a read-only scanner that reports candidate files and
artifacts that may need project evidence registry entries.

#### Scenario: Unregistered source document found
- **WHEN** the scanner finds a PPT/PDF/DOCX/XLSX file not referenced by the
  registry
- **THEN** it reports a candidate source-document registration.

### Requirement: Scan does not mutate registry files
PhysicsGuard SHALL NOT automatically write registry records during scan.

#### Scenario: Candidate test data found
- **WHEN** scan finds a CSV file
- **THEN** it reports the candidate without modifying the registry.

### Requirement: Scanner distinguishes known artifact categories
PhysicsGuard SHALL classify likely test data, source documents, model files,
contracts, validation plans, model libraries, and evidence registry files by
extension and known YAML keys where possible.

#### Scenario: Validation plan YAML found
- **WHEN** a YAML file has validation plan keys
- **THEN** scan reports it as a candidate validation plan artifact.
