## ADDED Requirements

### Requirement: Traceability ledger records model-to-code ownership
The repository SHALL maintain a structured traceability ledger that maps FlowGuard model responsibilities to source symbols, tests, examples, assumptions or boundaries, and validation evidence.

#### Scenario: Core model block can be traced to implementation
- **WHEN** an AI agent or maintainer inspects a ledger entry for a core FlowGuard model block
- **THEN** the entry identifies the owning model file, model block, source symbol, test evidence, example evidence, validation commands, and stale-evidence conditions

### Requirement: Traceability ledger remains machine-checkable
The repository SHALL provide a local validation command that checks whether ledger references still point to existing files and source symbols.

#### Scenario: Ledger references are valid
- **WHEN** the traceability validation command is run against the committed ledger
- **THEN** it exits successfully after verifying ledger structure, referenced files, and declared source symbols

#### Scenario: Ledger reference is stale
- **WHEN** the traceability validation command is run against a ledger entry that references a missing file or missing source symbol
- **THEN** it exits unsuccessfully and reports the stale reference

### Requirement: Traceability guidance is explicit for future agents
The repository SHALL document how AI agents and maintainers use the ledger before model-backed edits, validation, and release claims.

#### Scenario: Agent prepares a model-backed edit
- **WHEN** an AI agent plans a change to a model-backed PhysicsGuard behavior
- **THEN** the documentation tells the agent to consult the ledger, update it when ownership changes, and rerun the ledger check alongside FlowGuard and pytest validation

### Requirement: Traceability evidence does not replace validation
The repository SHALL state that the ledger is navigation and evidence indexing, not proof of runtime behavior or physical correctness.

#### Scenario: Ledger check passes
- **WHEN** the traceability validation command passes
- **THEN** release or done claims still require the relevant FlowGuard checks, tests, and example regressions
