## ADDED Requirements

### Requirement: Database catalog records project references
PhysicsGuard SHALL provide a database catalog registry that records project
references, project evidence registry paths, model-library indexes, generic
tags, confidence summaries, catalog roots, and metadata.

#### Scenario: Project is registered with project evidence path
- **WHEN** a catalog project record is checked
- **THEN** PhysicsGuard verifies it has a project id and either a project
  evidence registry path or an explicit missing-registry reason.

### Requirement: Catalog does not embed raw datasets
PhysicsGuard SHALL reject or block catalog records that embed raw test-data
payloads, sample rows, or bulk data arrays in catalog metadata.

#### Scenario: Raw rows appear in metadata
- **WHEN** a catalog contains metadata that looks like raw data rows
- **THEN** database gap checking reports a blocking raw-data payload gap.

### Requirement: Tags remain generic
PhysicsGuard SHALL support generic domain, system, subsystem, component,
test-object, testbench, and measurement tags without hardcoded industry
categories.

#### Scenario: AI classifies a project
- **WHEN** a project is summarized for the catalog
- **THEN** the project uses generic tag lists and does not require a
  domain-specific schema change.

### Requirement: Confidence summaries separate concerns
PhysicsGuard SHALL store source, mapping, data-quality, validation, reuse, and
catalog-freshness confidence states separately.

#### Scenario: Validation is unknown but source is high confidence
- **WHEN** a project has good source references but no model validation
- **THEN** the catalog can show source confidence separately from validation
  state.
