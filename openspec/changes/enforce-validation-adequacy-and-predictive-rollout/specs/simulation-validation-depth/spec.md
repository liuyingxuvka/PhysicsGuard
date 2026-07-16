## MODIFIED Requirements

### Requirement: Time and scenario scope
PhysicsGuard SHALL report whether evidence is a scalar snapshot, a time window, a declared scenario set, or a bounded dataset; every non-snapshot pass MUST include a target-owned adequacy receipt derived from current manifest, hierarchy, role, and observed-series evidence and MUST NOT silently extrapolate between scopes.

#### Scenario: Snapshot only
- **WHEN** only one distinct timestamp is evaluated
- **THEN** the receipt SHALL identify snapshot scope and SHALL NOT claim time-series, bounded-dataset, validation-ready, or predictive behavior

#### Scenario: Degenerate multi-point window
- **WHEN** several point ids reuse one timestamp or the selected timestamps have no positive span
- **THEN** broad temporal adequacy SHALL be blocked

#### Scenario: Declared scope exceeds observed scope
- **WHEN** a bounded-dataset or scenario claim is not supported by the observed rows, scenarios, and required coverage classes
- **THEN** the receipt SHALL block the broader claim and expose the actual covered scope

### Requirement: Native validation-depth receipt
PhysicsGuard SHALL emit a target-owned receipt bound to dataset, mapping, model universe, sampling plan, point/time/signal/family adequacy, scenario, split, residual, envelope, predictive semantics, assumptions, report hash, report type, and pass/partial/block status.

#### Scenario: SkillGuard supervision
- **WHEN** SkillGuard evaluates PhysicsGuard execution depth
- **THEN** it SHALL execute the validation plan from the exact target-input set, consume the current native adequacy/depth receipt, reconcile the complete target-owned object scope, preserve class-aware raw-denominator coverage and the precommitted native dynamic floors, and SHALL NOT recompute physical, sampling, or predictive metrics
- **AND** formal target execution SHALL emit `scheduled_production` evidence bound to the current verified installation identity carried by exactly one target-owned identity sidecar in the declared input set; an identity present only in the generic supervisor request SHALL be ignored and SHALL block; static/dynamic positive and intentionally shallow calibration SHALL remain `fixture_calibration` and SHALL NOT authorize a real model/dataset validation

### Requirement: Frozen purpose candidate admission
Every maintained PhysicsGuard guard model SHALL emit a target-owned candidate artifact that binds the exact current prevented-failure contract fingerprint, the complete declared failure and obligation universes, the native owner/route, and an ordered hash-linked authoring chain in which purpose freeze precedes candidate construction. Contract validation and candidate admission SHALL be separate mandatory checks.

#### Scenario: Candidate artifact is missing
- **WHEN** the prevented-failure contract exists but no candidate artifact is present
- **THEN** candidate admission SHALL block without treating the contract declaration as an implemented model

#### Scenario: Candidate binds another purpose contract
- **WHEN** the candidate carries a missing, stale, or mismatched purpose-contract fingerprint
- **THEN** candidate admission SHALL block and identify the fingerprint mismatch

#### Scenario: Candidate predates purpose freeze
- **WHEN** the authoring event chain places candidate construction before purpose freeze or breaks the hash-linked predecessor
- **THEN** candidate admission SHALL block even if the final files contain matching prose

### Requirement: Truthful proof-strength classification
Every prevented failure SHALL declare whether its proof is `native_semantic_detection` or `native_obligation_admission_gate`. A semantic-detection claim MUST bind a target-native fixture and oracle assertion for the declared failure. An obligation-admission proof MUST expose the actual generic obligation-gate finding and MUST narrow its title, block condition, known limit, and claim boundary to rejection of a candidate that lacks current target-native obligation proof.

#### Scenario: Generic missing obligation is relabeled as semantic detection
- **WHEN** a known-bad proof removes an obligation and observes only `missing_target_obligation`
- **THEN** the proof SHALL be classified as an obligation-admission gate and SHALL NOT claim that PhysicsGuard detected the underlying physical or evidence defect

#### Scenario: Semantic fixture is declared
- **WHEN** a failure is classified as native semantic detection
- **THEN** its known-bad case SHALL name the exact target-native test/fixture and the native assertion that proves the bounded failure

#### Scenario: Ordinary rows are mistaken for cannot-omit sentinels
- **WHEN** a representative plan exposes a large raw universe
- **THEN** SkillGuard SHALL keep every raw row visible in the denominator, SHALL hard-gate the native event/boundary/contribution sentinels, and SHALL NOT turn every ordinary row into a critical item that forces full sampling

#### Scenario: SkillGuard two-key depth calibration
- **WHEN** a broad PhysicsGuard claim requests supervised closure
- **THEN** SkillGuard SHALL require content-addressed current static-positive, time-varying-positive, and intentionally-shallow native calibration receipts, and a bundled calibration fixture SHALL NOT substitute for execution of the target plan

#### Scenario: Structural contract without execution adequacy
- **WHEN** the schema and contract exist but current coverage or native checks did not pass
- **THEN** execution depth SHALL remain partial, blocked, stale, or not run rather than pass

## ADDED Requirements

### Requirement: Target-owned validation universe
PhysicsGuard MUST derive available raw points and fields from the current hashed manifest, required variables and parameters from the current hierarchy/model, eligible dispositions from the current hashed role matrix, and selected/evaluated/validated coverage from the current hashed observed series and native audit results.

#### Scenario: Caller understates the raw universe
- **WHEN** a plan selects two points from a manifest containing one thousand available rows
- **THEN** the receipt SHALL preserve available=1000 and selected=2 and SHALL NOT accept caller-authored counts as authority

#### Scenario: Empty broad variable roles
- **WHEN** a non-snapshot plan has no declared validation roles or omits hierarchy-required critical variables
- **THEN** broad adequacy SHALL be blocked

### Requirement: Quantitative temporal adequacy
Every non-snapshot validation MUST have at least three distinct timestamps, positive span, unique in-range source row identities, start/middle/end strata, a declared maximum gap, and current count/ratio thresholds with a non-empty threshold source.

The sample MUST name a predeclared `selection_policy_id` and rationale whose
fingerprint is preserved in the receipt. Start/middle/end SHALL be derived from
the target-owned raw row universe rather than renormalized to the selected
subset. For an available universe of size `N`, representative modes MUST apply
the predeclared `sqrt_n_stage_v1` anti-degeneracy count
`min(N, max(12, ceil(sqrt(N))))`; the effective floor MUST be the strictest of
that count, the plan count/ratio, the project count/ratio, and any current
convergence count/ratio. `full` mode MUST additionally require `N`. The receipt
MUST preserve every floor input, the effective result, and the maximum observed
raw-row gap.

#### Scenario: Endpoint-only sample
- **WHEN** a long series selects only its first and last rows
- **THEN** the sample SHALL fail minimum-count and middle-stratum coverage

#### Scenario: Same-phase sample relabels itself
- **WHEN** several selected points all come from one raw-row phase
- **THEN** they SHALL NOT be renormalized into start/middle/end and broad temporal adequacy SHALL be blocked

#### Scenario: Three rows from a thousand-row universe
- **WHEN** a representative plan selects only three distributed rows from `N=1000` and declares no stricter valid floor
- **THEN** the effective native floor SHALL remain 32 and broad temporal adequacy SHALL be blocked

#### Scenario: Sufficient distributed representative sample
- **WHEN** a representative plan for `N=1000` validates at least 32 rows across the universal and project strata without exceeding the native row-gap limit
- **THEN** the anti-degeneracy floor SHALL be allowed to pass without requiring all 1000 rows, subject to every other native gate

#### Scenario: Duplicate timestamps
- **WHEN** unique point ids contain duplicate timestamps
- **THEN** the sample SHALL fail distinct-time coverage

#### Scenario: Skipped transient
- **WHEN** a required transient, peak, boundary, mode, or event tag has no selected valid point
- **THEN** event-aware adequacy SHALL be blocked and list the missing tag

### Requirement: Explicit sampling modes
PhysicsGuard SHALL support `full`, `stratified`, `event_aware`, `adaptive`, and `project_declared` modes, record threshold provenance, and emit pass/partial/block adequacy status without treating a declared mode name as proof.

#### Scenario: Sampling mode is omitted
- **WHEN** a complete aligned sequence plan does not explicitly choose a representative mode
- **THEN** the sampling mode SHALL default to `full` and every eligible row SHALL be required

#### Scenario: Full mode omits a row
- **WHEN** `full` mode selects fewer unique eligible source rows than the manifest provides
- **THEN** adequacy SHALL be blocked

#### Scenario: Adaptive mode lacks convergence
- **WHEN** `adaptive` mode has no current convergence evidence or has not converged
- **THEN** adequacy SHALL be blocked

#### Scenario: Project-declared thresholds lack provenance
- **WHEN** `project_declared` thresholds do not name their source
- **THEN** the plan or adequacy receipt SHALL fail closed

### Requirement: Signal-time and family coverage
PhysicsGuard MUST report per-signal valid and missing point counts, signal-by-time coverage, critical signal and parameter coverage, family/subsystem quota status, raw exclusion ratio, and repeated exclusion reasons; broad pass requires all declared critical targets and quotas plus bounded exclusions.

#### Scenario: Large signal universe sampled shallowly
- **WHEN** one or two signals are selected from a ten-thousand-signal universe without an allowed bounded scope
- **THEN** broad signal adequacy SHALL be blocked

#### Scenario: Boilerplate exclusions
- **WHEN** multiple excluded fields reuse the same generic reason under a policy that rejects templated exclusions
- **THEN** adequacy SHALL be blocked and identify the repeated reason

#### Scenario: Family quota missing
- **WHEN** a subsystem or signal family does not meet its declared covered-count or covered-ratio floor
- **THEN** broad adequacy SHALL be blocked for that family

### Requirement: Parameter temporal classification and depth
PhysicsGuard MUST derive the available parameter universe from the hierarchy,
critical declarations, calibration roles, and active fact-to-parameter bindings.
Every available parameter MUST have a project-sourced `static` or
`time_varying` classification. Static parameters require current binding
evidence; every time-varying parameter MUST independently satisfy declared
point count/ratio, distinct-time, span, and maximum-gap floors.

Every time-varying parameter MUST name a target-owned available-point
denominator (`manifest:rows` or a currently bound manifest field with a
non-null count), universal early/middle/late coverage, and at least three
project-declared row-position strata. Static parameters MUST use a binding/value
gate and MUST NOT be required to fabricate temporal points or strata.

When a manifest declares both `row_count` and `sample_count`, they MUST
identify the same point universe. A mismatch SHALL block broad adequacy and all
point, lineage, and per-parameter floors SHALL use the larger count while the
manifest is being repaired; PhysicsGuard MUST NOT silently select the smaller
denominator.

Each time-varying parameter MUST also declare whether it is expected to be
model-sensitive or verified non-sensitive for the bounded claim. PhysicsGuard
MUST apply each observed parameter value to the executable component model at
its own row and MUST run a baseline counterfactual. A sensitive disposition
requires at least two distinct observed values, a declared positive normalized
effect floor, and an actual change in one or more native residuals. A verified
non-sensitive disposition requires at least two distinct observed values, a
declared maximum effect, an exact reason, and an explicit claim boundary.

When sampling is representative rather than full, every time-varying parameter
MUST also retain current native residual evidence, a declared perturbation with
observed value direction, and a physical envelope. The aggregate parameter
identity universe MUST preserve available and selected counts so high overall
coverage cannot hide one shallow critical parameter.

#### Scenario: One point from a long time-varying parameter series
- **WHEN** the overall sample has adequate temporal coverage but a declared time-varying parameter appears at only one selected timestamp
- **THEN** broad adequacy SHALL be blocked with that parameter's point/time coverage details

#### Scenario: Two endpoints from a thousand-point parameter history
- **WHEN** a critical time-varying parameter is present only at the first and last raw rows
- **THEN** its count, ratio, middle-stage, and project-stage coverage SHALL remain insufficient

#### Scenario: Manifest point counts disagree
- **WHEN** the current manifest declares `row_count=10` and `sample_count=1000`
- **THEN** broad adequacy SHALL block with an identity mismatch and SHALL calculate its current point denominator as 1000, never 10

#### Scenario: Three distributed points from a thousand-point parameter history
- **WHEN** a time-varying parameter has only three validated rows from `N=1000`, even if early/middle/late are all present
- **THEN** its native 32-row anti-degeneracy floor SHALL remain unmet

#### Scenario: One shallow parameter among deep siblings
- **WHEN** aggregate parameter identity coverage is high but any critical time-varying parameter misses its own floor or stage
- **THEN** broad adequacy SHALL block on that parameter rather than average it away

#### Scenario: Ten-thousand parameter universe sampled twice
- **WHEN** only two parameters are bound from a ten-thousand-parameter hierarchy universe
- **THEN** the native receipt SHALL preserve available=10000 and selected=2 and SHALL block aggregate parameter coverage

#### Scenario: Static parameter has current binding
- **WHEN** a parameter is source-classified static and its current binding/value evidence passes
- **THEN** it SHALL pass without time-point, time-span, maximum-gap, or temporal-strata requirements

#### Scenario: Parameter values do not reach the model
- **WHEN** a declared sensitive time-varying parameter has multiple observed values but resetting it to the model baseline changes no native residual
- **THEN** broad adequacy SHALL block with missing model-contribution evidence rather than treating row presence as model use

#### Scenario: Verified non-sensitive parameter
- **WHEN** a time-varying parameter is executable, has multiple observed values, remains below its declared counterfactual effect ceiling, and carries an exact bounded non-sensitive disposition
- **THEN** its contribution gate SHALL be allowed to pass without inventing a sensitive effect

#### Scenario: Parameter temporal behavior is unclassified
- **WHEN** an available hierarchy, calibration, critical, or bound parameter is not classified as static or time-varying from a named source
- **THEN** broad adequacy SHALL fail closed rather than treating one binding as temporal coverage

### Requirement: Claim-compatible project closure
Validation-ready and validated-reuse-ready closure MUST consume a passing non-snapshot adequacy receipt whose covered scope supports the requested closure claim.

#### Scenario: Snapshot enters validation-ready closure
- **WHEN** a snapshot receipt is supplied for `validation_ready`
- **THEN** project closure SHALL block with a scope incompatibility finding

#### Scenario: Adequacy is partial
- **WHEN** pointwise residuals pass but sampling or signal adequacy is partial or blocked
- **THEN** project closure SHALL NOT issue a broad validation-ready pass

### Requirement: Single current SkillGuard V2 authority and expanded V1 retirement
The maintained PhysicsGuard skill SHALL retain only the V2 contract trio and explicitly referenced target-native assets. Generic V1 checkers, policies, mutable evidence/reports/ledgers, target-local run outputs, caches, fallback text, and alternate success paths MUST be absent from source and installed roots.

#### Scenario: Narrow completion receipt misses old runtime files
- **WHEN** a retirement receipt scans only `work-contract.json` and `check_manifest.json` while any other former V1 runtime surface remains
- **THEN** the receipt SHALL be invalid and PhysicsGuard family closure SHALL remain blocked

### Requirement: Receipt-only OpenSpec verification
OpenSpec SHALL consume the exact current PhysicsGuard family parent receipt and MUST NOT rerun, resume, or reconstruct any native, calibration, mesh, installation, or full-suite owner.

#### Scenario: Parent receipt is missing or stale
- **WHEN** the portable parent receipt is missing, partial, stale, tampered, or identity-mismatched
- **THEN** verification SHALL fail closed without executing a missing owner

#### Scenario: One parent execution is projected to this work package
- **WHEN** the same current PhysicsGuard family parent execution also supports a sibling OpenSpec change
- **THEN** this change SHALL consume a portable ref/envelope whose `work_package_id` is this current change while preserving the same underlying execution receipt identity and SHALL NOT rerun the owner

### Requirement: Installed portable native evaluator authority
Formal PhysicsGuard depth and calibration checks SHALL load the complete target-native Python runtime bundled under the installed skill's `.skillguard/runtime` tree. Every bundled source SHALL be part of the V2 implementation authority and every depth/calibration input fingerprint. A global package or editable source checkout SHALL NOT satisfy formal closure.

#### Scenario: Installed runtime file is absent from the contract
- **WHEN** a bundled native runtime source exists but is absent from implementation authority or any depth/calibration input set
- **THEN** compilation, source audit, installed parity, or formal closure SHALL fail closed

#### Scenario: External checkout can replace the installed evaluator
- **WHEN** the bundled runtime is missing or bypassed and an editable PhysicsGuard checkout remains importable
- **THEN** formal scheduled-production closure SHALL remain blocked rather than accepting the external import

#### Scenario: Bundled runtime manifest is incomplete
- **WHEN** any Python source owned by the current PhysicsGuard runtime is absent from or mismatched against the installed dataset-validation native-runtime manifest
- **THEN** the guard-model contract and formal installed-runtime gate SHALL block even if a global or editable `physicsguard` package can still be imported
