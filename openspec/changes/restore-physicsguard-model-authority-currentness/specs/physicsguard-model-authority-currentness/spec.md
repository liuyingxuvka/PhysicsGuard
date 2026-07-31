## ADDED Requirements

### Requirement: Feature work starts from current observed model authority

PhysicsGuard SHALL bind one observed model-system snapshot to exact current owners, source revision, toolchain, and fresh passing evidence before feature behavior changes.

#### Scenario: Observed authority is absent

- **WHEN** model-system audit finds no current observed snapshot
- **THEN** feature-ready and release-ready claims SHALL remain blocked

### Requirement: Historical maintenance gaps remain honest

Unfinished historical tasks SHALL be completed with exact current receipts or explicitly superseded with a reason and successor change.

#### Scenario: An old check was never run

- **WHEN** no terminal current receipt exists
- **THEN** the task SHALL NOT be marked complete merely because a newer change exists
