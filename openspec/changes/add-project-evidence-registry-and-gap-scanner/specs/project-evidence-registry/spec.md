## ADDED Requirements

### Requirement: Project evidence registry records common evidence
PhysicsGuard SHALL provide a project evidence registry for artifacts,
engineering facts, context cards, evidence bundles, conflicts, and missing
evidence records.

#### Scenario: Minimal artifact is registered
- **WHEN** an artifact record is checked
- **THEN** PhysicsGuard verifies it has an id, kind, path or external reference,
  registered time, status, and review state.

### Requirement: Project profile records basic project facts
PhysicsGuard SHALL provide a project-level profile for basic facts such as
project name, run period, run locations, owner/customer/testbench context when
known, source references, and explicit unknown reasons when not known.

#### Scenario: Project location is unknown
- **WHEN** AI cannot find the project run location in registered sources
- **THEN** it records an unknown reason and gap-check keeps the missing location
  visible for later maintenance.

### Requirement: Source or missing reason is explicit
PhysicsGuard SHALL require evidence records to provide source references or an
explicit source-missing reason when a source is expected.

#### Scenario: Cleaned file lacks raw source
- **WHEN** a cleaned test file has no raw source lineage
- **THEN** the registry can pass only if the missing raw-source reason is
  recorded as a gap or missing-source explanation.

### Requirement: Facts cover parameters and non-parameter engineering evidence
PhysicsGuard SHALL allow engineering facts to represent physical parameters,
equipment identity, vendor/model/version information, configuration facts,
time-series references, calibrated values, derived values, and human overrides.

#### Scenario: Equipment model number is registered
- **WHEN** an air-valve model number is extracted from a source document
- **THEN** it can be registered as an engineering fact without being treated as
  a model parameter.

### Requirement: Context cards declare applicability
PhysicsGuard SHALL provide model, testbench, test-object, and generic context
cards that record applicability, known invalid scope, and evidence
requirements.

#### Scenario: Model requires a fact
- **WHEN** a model context declares a required fact
- **THEN** gap checking reports whether that fact is available, missing, or
  unresolved.

### Requirement: Binding records summarize cross-artifact relationships
PhysicsGuard SHALL provide binding records for source-field-to-model,
engineering-fact-to-model, artifact-to-contract, and report-to-library
relationships without duplicating the full authoritative contract.

#### Scenario: Test field is bound to model variable
- **WHEN** a test-file contract maps a source field to a model target
- **THEN** the registry can store a binding summary that names the source
  contract as authority.

### Requirement: Binding expectations require coverage or explicit exemption
PhysicsGuard SHALL let AI record binding expectations for test fields,
engineering facts, and model targets, and SHALL require each expectation to be
either satisfied by a binding record or explicitly exempted with a reason.

#### Scenario: Manufacturer serial number is intentionally not model-bound
- **WHEN** a fact or field is useful project evidence but should not bind into
  the model
- **THEN** the registry records an exemption reason instead of leaving the
  missing binding ambiguous.

### Requirement: Local copies are explicit for small source documents
PhysicsGuard SHALL allow small source documents to record both an external
reference and a local copy path while preserving large test-data reference-only
behavior.

#### Scenario: Report copied into project
- **WHEN** a PDF report is copied into the project evidence folder
- **THEN** the artifact record can store local copy path, copy time, and copy
  hash.
