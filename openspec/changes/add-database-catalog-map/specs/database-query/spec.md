## ADDED Requirements

### Requirement: Database query filters projects safely
PhysicsGuard SHALL provide query output for project tags, tested quantities,
component tags, model targets, validation presence, test-data presence, and
project status.

#### Scenario: Query by measurement tag
- **WHEN** an AI queries a measurement tag
- **THEN** PhysicsGuard returns matching projects and each project's registry
  path, validation state, and gap summary.

### Requirement: Query results retain claim boundaries
PhysicsGuard SHALL include query semantics explaining that matches are search
candidates and require project-level evidence review before broad technical
claims or comparisons.

#### Scenario: Query finds historical projects
- **WHEN** multiple projects match a query
- **THEN** the query report lists them as related candidates and keeps blocking
  or review gaps visible.
