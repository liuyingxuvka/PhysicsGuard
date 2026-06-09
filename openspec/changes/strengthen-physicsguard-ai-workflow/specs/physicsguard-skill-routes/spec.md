## ADDED Requirements

### Requirement: Route-Oriented Skills
PhysicsGuard SHALL provide route-oriented Codex skill guidance for project adoption, model-understanding preflight, signal mapping review, audit closure, and candidate model blueprints while keeping the main AI debugging skill as the default entry.

#### Scenario: Main skill routes non-trivial audit
- **WHEN** a non-trivial PhysicsGuard debugging task starts
- **THEN** the main skill directs the agent through project adoption, preflight, signal mapping review, audit execution, and closure boundaries as applicable.

#### Scenario: Installed skills are synced
- **WHEN** repository skill files change
- **THEN** local installed skill copies can be synchronized and compared with repository source.
