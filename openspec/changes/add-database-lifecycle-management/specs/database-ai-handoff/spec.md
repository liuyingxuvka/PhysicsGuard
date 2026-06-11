## ADDED Requirements

### Requirement: Plain AI Handoff Documents

The system SHALL generate or maintain plain Markdown database README, map, rules,
and status documents that can be read by AI agents without PhysicsGuard tools.

#### Scenario: AI lacks PhysicsGuard

- **WHEN** an AI agent cannot run PhysicsGuard
- **THEN** the handoff documents SHALL still show database purpose, file layout,
  project lifecycle states, active projects, incomplete projects, archived
  projects, key gaps, model-template pointers, safe claims, unsafe claims, and
  how to install/use PhysicsGuard if available.

### Requirement: Handoff Is Navigation Only

Generated handoff documents SHALL say that they are onboarding/navigation
artifacts and do not prove project validation, model reuse, or cross-project
comparability.

#### Scenario: Handoff contains active project list

- **WHEN** a handoff document lists active projects
- **THEN** it SHALL also reference the catalog/gap/maintenance artifacts that
  support or limit those entries.
