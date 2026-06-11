## ADDED Requirements

### Requirement: Database Model Template Index

A database SHALL be able to reference reusable model templates and model assets
with source projects, model-library entries, validation evidence, compatible
tags, known limits, and safe-claim boundaries.

#### Scenario: Template lacks evidence

- **WHEN** a model template record lacks source evidence or known limits
- **THEN** the template-index check SHALL report a review or blocking gap.

#### Scenario: Template suggests reuse

- **WHEN** a template is presented as reusable
- **THEN** the report SHALL include validation boundaries and SHALL NOT claim
  validity for a new project without project-specific evidence.

### Requirement: Template Index Does Not Replace Model Library

The model-template index MAY reference model-library entries but SHALL NOT
replace model-library validation evidence.

#### Scenario: Referenced library is missing

- **WHEN** a template references a missing model-library index or entry
- **THEN** the template-index check SHALL report the missing evidence.
