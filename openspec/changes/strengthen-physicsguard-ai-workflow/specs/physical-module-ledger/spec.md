## ADDED Requirements

### Requirement: Module Equation Ledger
PhysicsGuard SHALL provide a machine-checkable module/equation ledger that maps audit module types or module families to equation summaries, SI units, assumptions, validity boundaries, diagnostic keys, representative tests, examples, and stale conditions.

#### Scenario: Check valid module ledger
- **WHEN** the module ledger check is run against the repository
- **THEN** it passes when required ledger fields are present and referenced files exist.

#### Scenario: Check incomplete module ledger
- **WHEN** a ledger entry omits equation, unit, assumption, diagnostic, test, example, or stale condition evidence
- **THEN** the checker reports a non-passing result naming the incomplete entry.

### Requirement: Ledger Is Navigation Evidence
PhysicsGuard SHALL describe the module ledger as navigation and review evidence, not as proof of physical correctness.

#### Scenario: Ledger check passes
- **WHEN** the module ledger check passes
- **THEN** final confidence still requires relevant runtime audit examples, pytest, FlowGuard checks, and closure evidence.
