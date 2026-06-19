## ADDED Requirements

### Requirement: PhysicsGuard Database Skills Are Compatibility Routes

PhysicsGuard database skills SHALL remain available only for legacy or
PhysicsGuard-specific physical/test/model evidence maps.

#### Scenario: Task is Guard-neutral database work

- **WHEN** a task involves Guard-neutral catalog, lifecycle, query, AI
  navigation, freshness, closure, or cross-Guard ledger work
- **THEN** PhysicsGuard database skills SHALL route to `databank-workflow`.

### Requirement: PhysicsGuard Caller Skills Do Not Route Total-Ledger Work To Legacy Database Cards

PhysicsGuard non-database skills SHALL not direct database total-ledger work to
`physicsguard-database-*` routes.

#### Scenario: A caller skill sees database-level work

- **WHEN** a PhysicsGuard caller skill mentions database-level or cross-project
  work
- **THEN** it SHALL direct broad database work to `databank-workflow`.

### Requirement: Legacy PhysicsGuard Database Success Is Not DataBank Closure

PhysicsGuard database command results SHALL be treated only as provider or
compatibility evidence, and SHALL NOT be treated as sufficient for DataBank
freshness, cross-Guard closure, or reusable database claims.

#### Scenario: Legacy command succeeds

- **WHEN** a legacy PhysicsGuard database command succeeds
- **THEN** broad DataBank claims SHALL still require DataBank audit and closure.
