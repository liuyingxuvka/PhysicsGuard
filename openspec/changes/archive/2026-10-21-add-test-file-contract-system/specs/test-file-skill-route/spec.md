## ADDED Requirements

### Requirement: Test-file contract review is a direct Codex child skill
PhysicsGuard SHALL include a repository and installed Codex skill named `physicsguard-test-file-contract-review` for test-bench and test-file workflows.

#### Scenario: Skill exists in repository and installed copy
- **WHEN** skill synchronization is checked
- **THEN** the repository skill file and installed `%USERPROFILE%/.codex/skills` copy both exist and match expected content.

### Requirement: Main skill routes test-data inputs conditionally
PhysicsGuard SHALL update the main AI debugging skill so test files, test-bench exports, CSV/TSV files, database/historian exports, run files, or field-level test data trigger test-file contract review before broad claims.

#### Scenario: Test file is present
- **WHEN** a PhysicsGuard AI workflow consumes a concrete test data file
- **THEN** the main skill routes through `physicsguard-test-file-contract-review` before residual localization claims.

#### Scenario: No test file is present
- **WHEN** a PhysicsGuard workflow is model-only or blueprint-only
- **THEN** the main skill does not require test-file contract review.

### Requirement: Closure incorporates test-file contract evidence when applicable
PhysicsGuard closure SHALL include test-file contract status when a workflow includes test data files.

#### Scenario: Contract failed
- **WHEN** a test-file contract status is failed, stale, blocked, or partial
- **THEN** closure output downgrades or blocks broad analysis claims and names next actions.

#### Scenario: Contract not applicable
- **WHEN** no test data file is in scope
- **THEN** closure may proceed using existing PhysicsGuard audit, mapping, refinement, and assumption evidence.
