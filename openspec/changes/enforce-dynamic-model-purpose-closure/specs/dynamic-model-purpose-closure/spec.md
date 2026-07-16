## ADDED Requirements

### Requirement: Every concrete model declares a dynamic prevented-failure purpose
Before constructing a concrete candidate, AI SHALL freeze a target-local PhysicsGuard purpose contract that states the specific modeling purpose, at least one prevented physical/evidence failure selected for that modeling instance, the bounded physical/evidence scope, the native owner and route, and the bounded claim. The family skill SHALL NOT prescribe the concrete failure set.

#### Scenario: AI starts candidate construction without a dynamic failure
- **WHEN** no current target-local contract declares at least one concrete prevented failure before candidate construction
- **THEN** PhysicsGuard SHALL block the model with no baseline, default failure, or inferred-success fallback

#### Scenario: Different tasks use the same family skill
- **WHEN** two modeling tasks use the same PhysicsGuard skill but have different physical risks
- **THEN** each task SHALL freeze its own purpose and failure set without modifying the family baseline

### Requirement: Current-instance authority uses explicit target-local paths
Every current-instance verifier action SHALL require an explicit target root and explicit contract, candidate, oracle, case, and proof artifact paths. Every path SHALL resolve inside the target root and SHALL NOT resolve to the maintained skill's bundled family baseline.

#### Scenario: Bundled baseline is passed as a real-task contract
- **WHEN** a current-instance action receives a bundled `guard-model/contract.json` or another path outside the explicit target root
- **THEN** it SHALL fail before evaluating candidate or proof content

### Requirement: Candidate binds the frozen contract and actual model artifact
The candidate SHALL bind the exact dynamic contract fingerprint, exact declared failure-id universe, actual candidate model artifact path and content fingerprint, and a hash-linked authoring event chain proving the purpose contract was frozen before candidate construction.

#### Scenario: Candidate predates contract freeze
- **WHEN** the candidate event is missing, unordered, not linked to the purpose-freeze event, or bound to a different contract fingerprint
- **THEN** candidate admission SHALL fail and the candidate SHALL remain non-pass

#### Scenario: Model artifact changes after binding
- **WHEN** the bound candidate model artifact content changes
- **THEN** the candidate binding and every dependent proof SHALL become stale

### Requirement: Every dynamic failure owns a PhysicsGuard-native oracle and cases
Every declared failure SHALL map to exactly one declared PhysicsGuard-native oracle, at least one target-local known-bad case, and coverage by the target-local known-good case. Oracle and case artifacts SHALL bind the same dynamic contract identity and SHALL identify exact fixtures and expected findings.

#### Scenario: One failure has no bad case
- **WHEN** any declared failure lacks a matching native oracle or known-bad case
- **THEN** contract closure SHALL fail even if all other failures are proven

### Requirement: Proof closure exhausts the exact dynamic failure universe
The proof set SHALL bind the exact contract and candidate fingerprints, include one current passing good result, include one current blocking result for every and only every declared failure, and bind each result to its exact oracle, case, fixture fingerprint, native owner, and finding code. Self-reported outcomes SHALL NOT satisfy proof.

#### Scenario: Proof set covers only a family baseline
- **WHEN** bundled family good/bad fixtures pass but current-instance proofs are missing
- **THEN** the real model SHALL remain non-pass

#### Scenario: One dynamic bad case does not block
- **WHEN** the target-native evaluator passes, skips, or emits a different finding for any declared failure's bad case
- **THEN** the whole model-purpose closure SHALL fail

### Requirement: Baseline regression and current model authority remain disjoint
Bundled family contracts, candidates, oracles, and fixtures SHALL declare the artifact role `family_baseline_regression`; current target artifacts SHALL declare `current_model_purpose`. Baseline results SHALL license only maintained-skill capability regression and SHALL NOT be projected as evidence that a concrete model prevents its declared failures.

#### Scenario: Baseline and current contract have identical text
- **WHEN** a current task happens to choose the same purpose or failure wording as the family baseline
- **THEN** the task SHALL still produce and prove its own target-local identity chain
