## ADDED Requirements

### Requirement: Catalog builds cross-project indexes
PhysicsGuard SHALL derive cross-project indexes from project evidence maps for
tags, tested quantities, model targets, model contexts, validation state, and
project gaps.

#### Scenario: Quantity appears in one project
- **WHEN** a project evidence map lists a tested quantity
- **THEN** the database map indexes that quantity to the project id.

### Requirement: Project registry remains the source of details
PhysicsGuard SHALL treat catalog summaries as navigation data and the referenced
project evidence registry as the detailed source for project facts, files,
bindings, and gaps.

#### Scenario: AI needs file-level evidence
- **WHEN** query results identify a project
- **THEN** the result includes the project registry path so AI can inspect the
  detailed project evidence chain.
