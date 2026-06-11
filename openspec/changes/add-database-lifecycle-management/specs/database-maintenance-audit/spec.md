## ADDED Requirements

### Requirement: Database Maintenance Audit

The system SHALL provide a database maintenance audit that checks lifecycle
artifacts, catalog health, project-level requirement gaps, path existence,
duplicate project records, stale summaries, stale validation/reuse state, and
pending maintenance actions.

#### Scenario: Broken project path

- **WHEN** a catalog project references a missing project evidence registry
- **THEN** the maintenance audit SHALL report a blocking or review gap depending
  on lifecycle state
- **AND** it SHALL propose a concrete maintenance action.

#### Scenario: Active model without validation

- **WHEN** an active project claims a model exists but validation is missing
- **THEN** the maintenance audit SHALL report the missing validation as a review
  or blocking gap according to the requested project state.

### Requirement: Maintenance Report Is AI-Readable

Maintenance reports SHALL be JSON/YAML serializable and include status, gaps,
actions, project summaries, stale reasons, and claim boundaries.

#### Scenario: Other AI agent reads report

- **WHEN** an AI agent reads the maintenance report without running commands
- **THEN** it SHALL be able to identify which projects need admission,
  remediation, archive, validation, or manual review.
