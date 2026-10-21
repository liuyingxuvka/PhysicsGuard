## ADDED Requirements

### Requirement: One resolved contract per test data file
PhysicsGuard SHALL provide a Test File Contract format that binds a specific test data file to a manifest, test-bench profile, extractor profile, model binding, parameter coverage artifacts, and coverage policy.

#### Scenario: Contract binds file evidence
- **WHEN** a contract is checked
- **THEN** the check verifies the referenced manifest exists, matches the contract binding, and describes the expected source file identity.

#### Scenario: Contract is file-specific
- **WHEN** two test data files have different field signatures or time/file identity
- **THEN** each file requires its own resolved contract, even if both reuse a shared test-bench profile or model binding.

### Requirement: Test-bench and script drift are explicit
PhysicsGuard SHALL report test-bench profile, extraction script, field signature, and model binding drift as contract findings.

#### Scenario: Field signature changed
- **WHEN** a new file adds, removes, or renames fields relative to its contract without an accepted alias or migration
- **THEN** contract check fails and names the added, removed, or unknown fields.

#### Scenario: Model binding changed
- **WHEN** the bound PhysicsGuard hierarchy or model hash differs from the contract
- **THEN** contract check fails or returns partial according to policy and blocks broad analysis claims.

### Requirement: Dataset segments are explicit
PhysicsGuard SHALL allow a test file contract to define dataset segments and SHALL fail or downgrade contracts that mix incompatible segments without declaring them.

#### Scenario: Multi-segment file is declared
- **WHEN** a test file has declared row or time segments
- **THEN** contract output reports each segment's scope, policy, and audit participation.

#### Scenario: Mixed file is not declared
- **WHEN** a file appears to mix incompatible field or time bases and no segment declaration exists
- **THEN** the contract check reports a blocking finding.

### Requirement: Test-file contracts are optional outside test-data workflows
PhysicsGuard SHALL NOT require Test File Contracts for ordinary model-only audits, candidate blueprints, or residual checks that do not consume concrete test data files.

#### Scenario: Model-only workflow
- **WHEN** a user asks for PhysicsGuard model construction or residual audit without test files or test-bench exports
- **THEN** existing PhysicsGuard routes remain valid and no test-file contract is required.

#### Scenario: Test data workflow
- **WHEN** a user provides a test file, test-bench export, CSV/TSV, database/historian export, run file, or field-level test data
- **THEN** the test-file contract route is required before broad AI analysis claims.
