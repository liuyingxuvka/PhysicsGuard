# physics-model-deepening Specification

## Purpose
Define how a PhysicsGuard task deepens competing hypotheses through independently
bound coverage, target-native evidence, explicit gap transitions, and finite
evidence-backed terminal decisions.
## Requirements
### Requirement: A non-trivial plan carries purpose and coverage identity

Every non-trivial `HypothesisPlanSpec` SHALL bind a non-empty task purpose, an independently owned coverage-universe id and fingerprint, an explicit assumptions list, an explicit unknowns list, an iteration identity, an exact predecessor receipt for iteration greater than zero, and a current native-depth receipt for the base model.

#### Scenario: Missing purpose blocks depth
- **GIVEN** a plan has competing hypotheses but no current purpose or coverage binding
- **WHEN** task-local depth is evaluated
- **THEN** the result is blocked and cannot license localization or prediction

#### Scenario: Old optional plan shape is rejected
- **GIVEN** a plan omits the current coverage binding, assumptions/unknowns declaration, predecessor field, or native receipt
- **WHEN** the plan is parsed
- **THEN** validation fails rather than selecting a compatibility path

### Requirement: Native depth gaps force continuation

`evaluate_hypothesis_observation()` and `evaluate_candidate_model_revision()` SHALL derive addressable execution-depth, mapping, residual, uncertainty, diagnosability, and predictive-rollout gaps exclusively from current target-native receipts and expose them as required next actions.

#### Scenario: Pointwise match with shallow depth
- **GIVEN** observed signals match the frozen expectations
- **AND** native depth still reports a missing time-varying or holdout obligation
- **WHEN** the candidate is evaluated
- **THEN** it remains non-terminal with `next_iteration_required=true`

#### Scenario: Caller-reported progress has no authority
- **GIVEN** the base and candidate native receipts expose the same open gaps
- **WHEN** the candidate is evaluated
- **THEN** it returns `progress_stalled` even if the caller changed prose, ids outside the receipt, or the candidate file

### Requirement: Candidate revisions preserve exact evidence identity

Every candidate revision SHALL bind base/candidate model identities, base/candidate native depth receipts, and typed regression, holdout, and predictive check receipts to the same task, plan, revision, coverage-universe fingerprint, and candidate fingerprint. Regression, holdout, and predictive evidence identities SHALL be distinct; holdout evidence SHALL be independent from candidate construction.

#### Scenario: Stale candidate evidence
- **GIVEN** a candidate file changed after its receipt was produced
- **WHEN** revision closure is evaluated
- **THEN** the revision is blocked and cannot be applied

#### Scenario: Check receipt belongs to another candidate
- **GIVEN** one required check receipt names another task, revision, coverage universe, or candidate fingerprint
- **WHEN** revision closure is evaluated
- **THEN** the revision is blocked and cannot be closed

### Requirement: Physical model limits remain visible

Missing external signals, unsupported validity ranges, and indistinguishable hypotheses SHALL remain explicit terminal blockers; the evaluator SHALL not invent values or select a hypothesis by prose.

#### Scenario: All predictions disagree with an observation
- **GIVEN** a real observation matches none of the declared hypotheses
- **WHEN** the iteration is evaluated
- **THEN** it creates a model-gap revision action and does not declare a physical cause

### Requirement: Terminal reasons are derived and exact

The evaluator SHALL derive `next_iteration_required` and one exact terminal reason from current evidence. `model_closed_for_task` SHALL require zero open native gaps and passing current regression, independent holdout, and predictive receipts. Missing external evidence, no progress, and exhausted iteration budgets SHALL remain distinct non-success terminals.

#### Scenario: Iteration budget is exhausted
- **GIVEN** a candidate still has addressable gaps at its declared maximum iteration
- **WHEN** revision closure is evaluated
- **THEN** it returns `iteration_limit` and does not accept the candidate

#### Scenario: External signal is required
- **GIVEN** the current native receipt names an addressable gap whose resolution class is external input and identifies the exact signal
- **WHEN** the iteration is evaluated
- **THEN** it returns `external_input_required` with that exact input id and no closed-model claim

### Requirement: Every maintained skill names the real model-deepening check
Each of the ten maintained PhysicsGuard author contracts SHALL name its exact target-owned strict task-local model-deepening check, and that check SHALL also appear in the current native check inventory. The compact skill entry SHALL conditionally point to one target-local `native-depth-and-purpose.md` that preserves the six-family native receipt, purpose-before-candidate order, prediction-before-observation, `model_miss`, base/candidate identities, typed regression, independent holdout, predictive rollout, gap comparison, and exact non-success terminal rules. The named check SHALL execute the runtime schema/core/CLI known-good and known-bad cases plus the current skill's prompt, capsule, and reference projection; an abstract model Boolean or self-report is insufficient.

#### Scenario: Model-deepening check is missing or merely abstract
- **GIVEN** a maintained skill omits the current target-owned check, names another check, or names a check that does not execute the strict runtime and negative cases
- **WHEN** the author contract is compiled or its skill-suite mesh is checked
- **THEN** the maintained skill remains blocked and cannot support model-deepening closure

#### Scenario: Entry is compact but deep semantics are unreachable
- **GIVEN** a maintained skill has a small `SKILL.md` but its capsule lacks the exact conditional reference or the reference omits one required deepening family, evidence identity, or terminal boundary
- **WHEN** prompt and contract projection are checked
- **THEN** the maintained skill remains blocked and cannot claim that prompt contraction preserved deep understanding

#### Scenario: Ordinary task does not need deep protocol
- **GIVEN** a selected route performs a bounded ordinary action without creating, revising, or closing a task-local model
- **WHEN** initial prompt loading is evaluated
- **THEN** the deepening reference remains available but not eagerly loaded
