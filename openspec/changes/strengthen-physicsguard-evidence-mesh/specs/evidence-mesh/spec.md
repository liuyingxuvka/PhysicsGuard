## ADDED Requirements

### Requirement: Evidence mesh records parent-child model closure
PhysicsGuard SHALL provide an evidence mesh artifact that records parent model ids, child model evidence ids, partition ownership, child reattachment status, and parent-consumed child evidence ids.

#### Scenario: Parent consumes current child evidence
- **WHEN** every required child model evidence row is current, attached, and consumed by its parent mesh row
- **THEN** the evidence mesh review can count the parent-child model mesh section as passing.

#### Scenario: Child evidence is local-only
- **WHEN** child model evidence is marked current but no parent row consumes that evidence id
- **THEN** the evidence mesh review reports a blocking parent reattachment finding.

### Requirement: Evidence mesh records model-code-test alignment
PhysicsGuard SHALL provide alignment rows that bind each required model obligation to an owner code contract and current external or mixed-scope test evidence.

#### Scenario: Required obligation has a code contract and test
- **WHEN** a required model obligation row has a matching code contract row and current passing test evidence that references both ids
- **THEN** the evidence mesh review can count the obligation as covered.

#### Scenario: Required obligation lacks test evidence
- **WHEN** a required model obligation has no current passing test evidence bound to the same owner code contract
- **THEN** the evidence mesh review reports a blocking alignment finding.

### Requirement: Evidence mesh records generated bad-case coverage
PhysicsGuard SHALL track contract-exhaustion case ids, expected oracles, test owners, and downstream consumption before generated bad-case coverage can support broad claims.

#### Scenario: Generated case has oracle and downstream evidence
- **WHEN** every required generated case has an oracle, a current passing test owner, and a downstream route that consumes the case id
- **THEN** the evidence mesh review can count contract-exhaustion coverage as passing.

#### Scenario: Generated case is hand-written only
- **WHEN** a bad-case row lacks a generated case id or oracle
- **THEN** the evidence mesh review reports the case as insufficient for broad coverage.

### Requirement: Evidence mesh records test mesh freshness
PhysicsGuard SHALL track parent test suites, child test suites, required cell or shard ids, result status, result evidence reference, and freshness.

#### Scenario: Parent suite consumes current child suites
- **WHEN** all required child suite rows are current, passing, non-progress-only, and consumed by the parent test mesh row
- **THEN** the evidence mesh review can count test mesh evidence as passing.

#### Scenario: Background progress is used as pass evidence
- **WHEN** a test evidence row is running, progress-only, stale, skipped, failed, or missing a result reference
- **THEN** the evidence mesh review reports a blocking test freshness finding.

### Requirement: Evidence mesh records behavior-bearing field lifecycle
PhysicsGuard SHALL record field lifecycle rows for behavior-bearing schema keys, payload fields, report fields, and old-field dispositions that affect evidence claims.

#### Scenario: Behavior field is projected and tested
- **WHEN** a behavior-bearing field has an owner, lifecycle disposition, projection target, and downstream alignment evidence
- **THEN** the evidence mesh review can count field lifecycle evidence as passing.

#### Scenario: Old field disposition is missing
- **WHEN** an old, renamed, deprecated, or replaced behavior-bearing field lacks a disposition
- **THEN** the evidence mesh review reports a blocking field lifecycle finding.

### Requirement: Evidence mesh records risk-ledger claim decisions
PhysicsGuard SHALL require final risk-ledger rows to consume ModelMesh, Model-Test Alignment, ContractExhaustion, TestMesh, and FieldLifecycle evidence before a broad claim can pass.

#### Scenario: Risk row consumes all required routes
- **WHEN** a risk-ledger row for the claim consumes current passing evidence from every required route
- **THEN** the evidence mesh review status can be `pass`.

#### Scenario: Risk row omits a required route
- **WHEN** a broad claim risk row omits a required route receipt
- **THEN** the evidence mesh review blocks the claim.

### Requirement: Evidence mesh CLI emits schema-valid JSON
PhysicsGuard SHALL expose a CLI command that checks an evidence mesh YAML file and emits schema-valid JSON.

#### Scenario: Evidence mesh check passes
- **WHEN** the user runs `physicsguard evidence mesh-check MESH.yaml --pretty` on a valid mesh
- **THEN** stdout contains a JSON report with status `pass`, `ok: true`, and a safe claim boundary.

#### Scenario: Evidence mesh check fails
- **WHEN** the user runs the mesh checker on an incomplete mesh
- **THEN** the process exits nonzero and the JSON report lists blocking findings and next actions.
