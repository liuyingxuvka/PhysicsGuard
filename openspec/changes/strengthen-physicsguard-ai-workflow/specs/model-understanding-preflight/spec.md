## ADDED Requirements

### Requirement: Model Understanding Preflight
PhysicsGuard SHALL provide a workflow artifact for non-trivial external-model debugging that records visible symptom, external model identity, physical boundary, subsystem blocks, conserved quantities, interfaces, unit expectations, assumptions, uncertain mappings, first audit level, and stop conditions before residual conclusions are interpreted.

#### Scenario: Review complete preflight
- **WHEN** a complete model-understanding preflight file is reviewed
- **THEN** the review reports pass and summarizes the physical boundary, required evidence, and claim boundary.

#### Scenario: Review incomplete preflight
- **WHEN** a preflight file omits required symptom, boundary, subsystem, unit, or assumption sections
- **THEN** the review reports non-passing status with missing inputs and next actions.

### Requirement: Preflight Does Not Replace Runtime Audit
PhysicsGuard SHALL treat preflight review as planning evidence only and MUST NOT count it as residual validation or localization proof.

#### Scenario: Preflight passes without audit
- **WHEN** a model-understanding preflight passes but no audit report exists
- **THEN** PhysicsGuard documentation and closure guidance still require runtime audit evidence before localization claims.
