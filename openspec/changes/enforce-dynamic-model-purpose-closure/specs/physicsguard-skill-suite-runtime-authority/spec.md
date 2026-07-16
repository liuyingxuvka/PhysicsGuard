## MODIFIED Requirements

### Requirement: PhysicsGuard-owned purpose declaration precedes candidate construction
Every concrete governed PhysicsGuard model or route MUST freeze a target-local, current-model-purpose contract before candidate construction. The AI MUST select and declare what one or more physical/evidence failure classes this modeling instance is intended to prevent, the bounded physical/evidence universe, the PhysicsGuard-native oracle and predicate for each failure, expected finding code, proof strength and known limit, and the bounded claim. A maintained skill's bundled fixed contract SHALL be a family baseline regression only and MUST NOT supply the current task's purpose or failure set. This chain has no selectable mode.

#### Scenario: Candidate exists before its purpose contract
- **WHEN** a candidate model is authored before the exact target-local purpose, universe, oracle, and prevented-failure identities are frozen
- **THEN** the candidate SHALL be invalid for closure and MUST be rebuilt or rebound after a valid declaration

#### Scenario: Fixed family contract is reused as current purpose
- **WHEN** AI validates the bundled family contract but does not declare what the concrete model now being built is meant to prevent
- **THEN** the real modeling task SHALL remain blocked even though family baseline regression passes

### Requirement: Every declared prevented failure is proven natively
Every concrete governed target MUST provide one target-local known-good proof covering all declared failures and at least one target-local known-bad proof for every dynamically declared prevented failure class. Every known-bad MUST execute the declared PhysicsGuard-native evaluator against the exact bound candidate, block, identify the exact failure class, and emit its declared finding code. All proofs MUST bind the exact current contract, candidate artifact, oracle, and fixture fingerprints.

#### Scenario: Generic fixture relabeled as target evidence
- **WHEN** a proof contains generic obligations or only changes an expected-status label without executing the target's native evaluator against the bound current candidate
- **THEN** proof authorization SHALL fail

#### Scenario: One declared failure has no bad proof
- **WHEN** a current model-purpose contract declares a prevented failure class but no exact native known-bad case proves it is blocked
- **THEN** the model SHALL remain non-pass even if all other cases and family baselines pass

#### Scenario: SkillGuard decides the physical meaning
- **WHEN** a SkillGuard field, target classification, integration mode, or generic calibration policy supplies the failure class or oracle instead of the current PhysicsGuard task contract
- **THEN** the contract SHALL be rejected as non-current

### Requirement: Generic SkillGuard supervision and single current authority
Each migrated target SHALL use only `contract-source.json`, `compiled-contract.json`, and `check-manifest.json` as SkillGuard runtime authority plus explicitly referenced PhysicsGuard-native assets. The source contract SHALL declare only checks, owners, dependencies, inputs, obligations, and closure; it SHALL NOT contain `depth_profile`, `calibration`, `integration_mode`, target classification, Guard-family semantics, a fixed current-task failure set, or an alternate success route. Bundled guard-model assets referenced by SkillGuard SHALL be labeled family baseline regression and SHALL NOT close current model-purpose work.

#### Scenario: Former V1 control surface remains executable
- **WHEN** a former manifest, work contract, generic V1 checker, mutable report/ledger, fallback instruction, or alternate success route remains in source or installed skill roots
- **THEN** migration and installation parity SHALL fail

#### Scenario: Narrow retirement receipt omits live V1 residue
- **WHEN** a completion receipt scans only the former work contract and manifest while generic V1 checkers, policies, mutable evidence/reports/ledgers, run outputs, or caches remain
- **THEN** that receipt SHALL be invalid and retirement SHALL remain incomplete

#### Scenario: Retirement history is placed inside current SkillGuard authority
- **WHEN** a V1 retirement receipt or other historical control artifact is stored inside a maintained skill's `.skillguard` directory
- **THEN** current SkillGuard authority and installation SHALL be blocked; retirement history MUST remain in the PhysicsGuard project-level evidence root

#### Scenario: SkillGuard baseline receipt is used as current model proof
- **WHEN** a generic SkillGuard receipt proves only the maintained family baseline checks
- **THEN** it SHALL NOT be accepted as a current model-purpose native proof receipt
