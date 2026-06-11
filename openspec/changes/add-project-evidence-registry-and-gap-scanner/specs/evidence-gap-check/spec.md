## ADDED Requirements

### Requirement: Gap check classifies evidence gaps
PhysicsGuard SHALL classify missing or inconsistent evidence as blocking,
review, or optional.

#### Scenario: Required model fact missing
- **WHEN** an evidence bundle references a model context with a blocking
  required fact that is not registered
- **THEN** the gap report includes a blocking gap.

### Requirement: Blocking gaps prevent broad pass claims
PhysicsGuard SHALL prevent validation pass or validated reuse claims when
blocking evidence gaps remain unresolved.

#### Scenario: Bundle has unresolved blocking gap
- **WHEN** model-dataset validation consumes a bundle with unresolved blocking
  gaps
- **THEN** final validation status is not `pass`.

### Requirement: Missing required evidence is preserved
PhysicsGuard SHALL provide missing evidence records for required facts or
artifacts that were searched for but not found.

#### Scenario: Required fact cannot be found
- **WHEN** AI cannot find a required fact after checking registered sources
- **THEN** it records a missing evidence item instead of inventing a value.

### Requirement: Gap check audits binding completeness
PhysicsGuard SHALL report gaps when test fields, physical parameters, or model
targets that should be bound to the model have no binding record and no explicit
exemption reason.

#### Scenario: Covered test field lacks project-level binding summary
- **WHEN** a registered test-file contract marks a source field as covered
  but the project registry has no binding record or exemption for that field
- **THEN** the gap report includes a review gap for the missing binding
  summary.

#### Scenario: Physical parameter has no model binding review
- **WHEN** a registered physical parameter has no model target binding and no
  binding expectation or exemption
- **THEN** the gap report includes a review gap so AI knows the parameter still
  needs maintenance.

### Requirement: Gap check audits basic project profile completeness
PhysicsGuard SHALL report review gaps when basic project profile fields are
missing, unknown, or lack source evidence.

#### Scenario: Project name missing
- **WHEN** a project evidence registry lacks project name and has no explicit
  unknown reason
- **THEN** the gap report includes a review gap asking AI to find or record the
  project name evidence.

#### Scenario: Project run time unknown
- **WHEN** project run period is unknown
- **THEN** the gap report keeps that unknown visible instead of treating the
  project profile as complete.
