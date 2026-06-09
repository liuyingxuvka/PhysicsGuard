## ADDED Requirements

### Requirement: External Model Intake
PhysicsGuard SHALL provide a workflow artifact for external model snapshots that records tool identity, model version, scenario, export time, observed snapshot path, exported signals, source units, expected SI units, mapping confidence, review state, conversion notes, and stale conditions.

#### Scenario: Review complete intake
- **WHEN** a complete external-model intake file is reviewed
- **THEN** the review reports pass and summarizes mapping records, review-required count, and stale triggers.

#### Scenario: Review uncertain mappings
- **WHEN** any exported signal has low confidence, missing conversion evidence, or review-required state
- **THEN** the review reports a non-passing or partial status and recommends mapping review before model fault claims.

### Requirement: Intake Does Not Convert Observed Values
PhysicsGuard SHALL treat intake mapping fields as evidence and review metadata only and MUST NOT convert or mutate observed values from this artifact.

#### Scenario: Intake declares conversion note
- **WHEN** an intake signal includes conversion notes or factors
- **THEN** the review reports the note but does not alter any observed-value file.
