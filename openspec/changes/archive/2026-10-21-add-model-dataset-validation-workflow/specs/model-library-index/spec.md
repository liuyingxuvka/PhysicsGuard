## ADDED Requirements

### Requirement: Model library records reusable model evidence
PhysicsGuard SHALL provide a model library index for reusable model assets,
hashes, compatible profiles, validation report references, known limits, and
reuse status.

#### Scenario: Validated model entry
- **WHEN** a model library entry claims validated or partial reuse status
- **THEN** it references at least one validation report.

### Requirement: Model library does not store raw datasets
PhysicsGuard SHALL store only metadata, paths, hashes, fingerprints, and report
references in the model library.

#### Scenario: Raw data path recorded
- **WHEN** a model library entry references data
- **THEN** it records a reference or fingerprint, not copied raw data content.
