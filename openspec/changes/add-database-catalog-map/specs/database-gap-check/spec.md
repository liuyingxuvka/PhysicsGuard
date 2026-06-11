## ADDED Requirements

### Requirement: Database gap check classifies catalog gaps
PhysicsGuard SHALL provide database-level gap checks that classify gaps as
blocking, review, or optional.

#### Scenario: Referenced project registry is missing
- **WHEN** a catalog project points to a missing project evidence registry file
- **THEN** gap checking reports a blocking gap for that project.

### Requirement: Project evidence gaps propagate to catalog
PhysicsGuard SHALL propagate blocking and review project evidence gaps into the
database gap report.

#### Scenario: Project registry has blocking gaps
- **WHEN** a referenced project evidence registry reports blocking gaps
- **THEN** database gap checking reports the project as blocked for broad
  database-level validation or reuse claims.

### Requirement: Cross-project comparison requires scope
PhysicsGuard SHALL keep comparison-scope uncertainty visible and MUST NOT claim
two projects are directly comparable unless scope and evidence gaps support that
claim.

#### Scenario: Query finds two related projects
- **WHEN** projects share a tag or quantity but have unresolved gaps
- **THEN** query output treats them as related candidates, not directly
  comparable proof.
