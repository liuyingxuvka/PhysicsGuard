## ADDED Requirements

### Requirement: DataBank Owns Guard-Neutral Database Ledgers

DataBank SHALL own database root, catalog, lifecycle, history, query, freshness,
closure, AI navigation, and cross-Guard evidence ledger responsibilities.

#### Scenario: User asks for a general database

- **WHEN** a user asks to build, audit, query, maintain, or hand off a database
  that is not limited to PhysicsGuard physical/test/model evidence
- **THEN** the canonical route SHALL be `databank-workflow`.

### Requirement: DataBank Root Is Explicit

DataBank SHALL require an explicit root layout with README, status, policy,
catalog, history, contracts, project records, provider results, navigation,
closure reports, and query records.

#### Scenario: Root folder is missing required files

- **WHEN** DataBank audits a root that lacks required files or directories
- **THEN** the root check SHALL return `blocked`
- **AND** no database-level pass claim SHALL be allowed.

### Requirement: DataBank Validates Contract Values

DataBank SHALL validate not only required field presence but also status values,
hash format, pass-closure evidence, empty query reasons, raw-data-copy flags,
and optionally local path resolution.

#### Scenario: Contract field exists but is invalid

- **WHEN** a source contract has a malformed sha256 value or missing local path
- **THEN** contract validation SHALL return `blocked` with invalid-field details.

### Requirement: DataBank Adapts Provider Results Without Hiding Gaps

DataBank SHALL convert provider reports into the closure envelope while
preserving missing, stale, skipped, partial, and blocked provider evidence.

#### Scenario: Provider report has blocking gaps

- **WHEN** a provider report has blocking gaps even if its top-level status says
  pass
- **THEN** the DataBank provider adapter SHALL return `blocked`.

### Requirement: DataBank Gates Lifecycle Promotion

DataBank SHALL require passing closure evidence before promoting a project to
`active_validated` or `active_reusable`, and SHALL write lifecycle events to
append-only history when applied.

#### Scenario: Validated state requested without closure

- **WHEN** a lifecycle transition targets `active_validated` without a passing
  closure report
- **THEN** DataBank SHALL return `blocked`
- **AND** SHALL NOT update the catalog or history.

### Requirement: DataBank Provides One-Command Audit

DataBank SHALL provide a single audit command that aggregates root, contract,
provider closure, freshness, navigation, and query checks.

#### Scenario: Fixture database is structurally valid

- **WHEN** the fixture database root is audited
- **THEN** audit SHALL return `pass`
- **AND** the report SHALL show the checked sections.
