## ADDED Requirements

### Requirement: PhysicsGuard closure reports route audit followups
PhysicsGuard SHALL expose audit pass state, missing variables or parameters, signal mapping review rows, recommended refinements, bug-family followups, stale evidence, skipped checks, and next actions before audit completion claims.

#### Scenario: Required variables are missing
- **WHEN** hierarchy evaluation reports missing required variables
- **THEN** the closure report is blocked and recommends requesting the next required signals

### Requirement: Audit closure does not imply high-fidelity equivalence
PhysicsGuard SHALL preserve unsafe claim boundaries that prevent low-fidelity audit results from being presented as commercial-model equivalence or high-fidelity proof.

#### Scenario: Audit returns a suspicious block
- **WHEN** a suspicious block has recommended refinements
- **THEN** the closure report remains partial until the block is refined, scoped, or the claim is downgraded
