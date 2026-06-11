## ADDED Requirements

### Requirement: Project closure plan declares claim scope and required checks
PhysicsGuard SHALL provide a project closure plan schema that declares the intended claim scope, referenced evidence artifacts, and required checks.

#### Scenario: Validation readiness closure is planned
- **WHEN** a closure plan declares `claim_scope: validation_ready`
- **THEN** the plan identifies project evidence, consumed evidence bundles, test contracts, validation plans, and required check flags.

### Requirement: Project closure report aggregates route evidence
PhysicsGuard SHALL provide a project closure report that aggregates project audit, evidence registry checks, evidence gap checks, evidence map generation, test-file contracts, model-dataset validation, model-library checks, and optional hierarchy closure inputs.

#### Scenario: Clean project evidence and validation pass
- **WHEN** all required route checks pass for the declared claim scope
- **THEN** the closure report status is `passed`, `ok` is true, and the safe claim is scoped to the checked boundary.

### Requirement: Blocking evidence prevents broad claims
PhysicsGuard SHALL block broad project completion, validation pass, validated reuse, or fault-localization claims when blocking evidence gaps or error findings remain.

#### Scenario: Evidence bundle has a blocking gap
- **WHEN** a required evidence bundle gap-check reports a blocking gap
- **THEN** the project closure report status is `blocked` and includes a blocking finding with a next action.

### Requirement: Review gaps downgrade claims but remain visible
PhysicsGuard SHALL keep review gaps visible and downgrade broad claims unless the claim scope explicitly allows scoped progress.

#### Scenario: Project profile is incomplete but no blocking gap exists
- **WHEN** gap-check reports only review gaps
- **THEN** the project closure report status is `partial` or `downgraded`, and the review findings remain in the report.

### Requirement: Evidence maps are navigation, not validation proof
PhysicsGuard SHALL treat project evidence maps as AI onboarding/navigation evidence only, not as validation proof.

#### Scenario: Evidence map succeeds while gap-check fails
- **WHEN** evidence map generation succeeds but the corresponding gap-check has blocking gaps
- **THEN** the closure report is not `passed`.

### Requirement: Skipped required checks are explicit
PhysicsGuard SHALL report skipped required checks and block closure by default when the plan does not allow skipped required checks.

#### Scenario: Required validation check is missing
- **WHEN** the closure plan requires validation but provides no validation plan
- **THEN** the closure report includes a skipped required check finding and status is `blocked`.

### Requirement: CLI emits schema-valid JSON
PhysicsGuard SHALL expose a `project closure` CLI command that emits a schema-valid project closure report.

#### Scenario: Closure command runs with pretty output
- **WHEN** the user runs `physicsguard project closure PLAN.yaml --pretty`
- **THEN** stdout contains JSON matching the project closure report schema and the process exits nonzero unless the closure status is `passed`.
