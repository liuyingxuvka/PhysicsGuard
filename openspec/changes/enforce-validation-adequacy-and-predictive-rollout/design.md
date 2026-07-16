## Context

The existing model-dataset validator owns exact dataset identity, signal mapping, pointwise residual evaluation, physical envelopes, split identity, and the native depth receipt. Its current time gate distinguishes one-point snapshots from multi-point evidence, but the selected sample is self-declared and is not reconciled with raw manifest row counts, hierarchy-required targets, timestamp distribution, or a predictive trajectory contract. Project closure consumes a passing receipt without comparing the requested closure claim to the receipt's scope or model semantics.

PhysicsGuard must remain a low-fidelity audit framework. It must not reverse engineer a commercial solver or pretend that a target-neutral supervisor can choose domain sample sizes. SkillGuard remains a target-neutral contract supervisor and consumes PhysicsGuard's native receipt without recomputing physical or trajectory metrics.

## Goals / Non-Goals

**Goals:**

- Derive a machine-readable validation universe from current raw manifest, role matrix, hierarchy, model parameters, plan roles, and selected observed series.
- Fail closed for broad claims when the sample is too small, duplicated, temporally degenerate, badly distributed, missing required event classes, or too sparse for declared thresholds.
- Preserve project-specific freedom through explicit threshold provenance while enforcing universal invariants such as distinct timestamps, positive span, start/middle/end coverage, non-empty broad roles, and honest exclusions.
- Produce per-signal, per-time, family, and aggregate adequacy receipts that distinguish available, eligible, selected, evaluated, and validated evidence.
- Separate pointwise consistency from stateful dynamic prediction and validate future-holdout rollout artifacts with target-owned metrics.
- Make closure compare requested scope, covered scope, adequacy status, and predictive semantics.
- Make purpose-before-candidate executable by binding a candidate artifact to the exact frozen contract and ordered authoring evidence.
- Keep semantic-detection claims distinct from generic obligation-admission gates.
- Consume scheduled-production identity only from a target-owned sidecar and make the installed dataset-validation runtime self-contained and content-manifested.

**Non-Goals:**

- Add high-fidelity component models, commercial-tool adapters, or a universal dynamic simulator.
- Pick one universal statistically optimal sample count for every engineering project.
- Let SkillGuard derive signal importance, physical thresholds, trajectory predictions, or residuals.
- Claim that a validated rollout proves behavior outside the exact model, initial state, step, horizon, files, and thresholds in the receipt.

## Decisions

### 1. Extend the existing native validator through focused helper owners

`physicsguard.core.model_dataset_validation` and the existing validation-depth route remain the public owner. Quantitative adequacy and rollout comparison live in focused schema/core helpers and are assembled into the existing native receipt. This avoids a parallel validator and keeps the already-large pointwise evaluator from becoming the only implementation surface.

Alternative considered: implement adequacy inside SkillGuard. Rejected because it would duplicate target-domain judgment and violate the native-integrated boundary.

### 2. Derive counts from target-owned artifacts, not AI narration

Available point count and raw field count come from the hashed `DataFileManifest`; model-required variables and parameters come from the loaded hierarchy; coverage disposition comes from the hashed parameter-role matrix; selected and validated counts come from the hashed observed series and actual pointwise results. Each broad selected point carries a source row index and source identity so the receipt can prove lineage and reject duplicates or out-of-range rows.

Alternative considered: accept caller-supplied available/selected counts. Rejected because the caller could make a two-point sample look complete.

### 3. Use universal invariants plus declared threshold provenance

Every non-snapshot claim requires an adequacy plan. Universal gates require at least three distinct timestamps, positive span, unique source rows, raw-universe start/middle/end strata, complete required-signal presence, and explicit maximum time gap. They also resolve an `N`-aware anti-degeneracy floor: `min(N, max(12, ceil(sqrt(N))))`. The effective floor is the strictest count implied by this native floor, plan count/ratio, project count/ratio, current convergence count/ratio, and `N` itself in full mode. The same resolution is applied independently to every time-varying parameter, and a universal row-gap limit prevents enough points from collapsing into a few phases. Every plan also binds a predeclared selection-policy id and rationale into the sampling-policy fingerprint. Sampling modes are `full`, `stratified`, `event_aware`, `adaptive`, and `project_declared`.

Mode-specific rules add:

- `full`: every eligible manifest row is selected;
- `stratified`: declared strata and count/ratio floors pass;
- `event_aware`: strata plus every required event/coverage tag pass;
- `adaptive`: declared convergence evidence and floors pass;
- `project_declared`: thresholds carry a non-empty project source and still satisfy universal invariants.

This avoids a false universal precision while making shallow selection machine-visible.

When a complete aligned sequence is available, `full` is the default and every row is evaluated. Representative modes are intentionally bounded: their project-sourced floors cannot be lowered after results are observed, and their receipt retains selection rationale, event/phase coverage, and exact input fingerprints.

### 4. Treat signal and family coverage as part of adequacy

Broad plans must declare non-empty validation roles and critical targets. All hierarchy-required variables are critical by default and all hierarchy-required parameters must be present in the model universe. The evaluator reports raw, eligible, selected, and fully validated signal counts; per-signal valid/missing counts; signal-by-time coverage; excluded-field ratio; repeated/template exclusion reasons; and declared family/subsystem quota results.

Alternative considered: rely on the existing rule that every raw field has a disposition. Rejected because thousands of fields can be excluded with boilerplate reasons while only one or two targets are validated.

### 4a. Separate static binding depth from time-varying parameter depth

Every available parameter is classified from a named source. A static parameter has an honest one-object binding/value denominator and no temporal requirements. A time-varying parameter derives its available-point denominator from manifest rows or a bound field non-null count, then proves its own resolved dynamic floor, validated count/ratio, distinct times, span, maximum time and row gaps, universal early/middle/late, and project-declared row-position strata. Representative parameter samples additionally bind residual, observed-direction, and physical-envelope evidence.

Row presence is not model use. At every selected row the observed parameter value is applied to the executable component model. The native validator replays a counterfactual with that one parameter reset to its model baseline and measures the resulting normalized residual delta. A parameter declared sensitive must exceed its predeclared effect floor and identify affected residuals. A parameter that is genuinely irrelevant to the bounded claim may pass only through an explicit `verified_non_sensitive` ceiling, reason, and claim boundary. A disconnected or misspelled target cannot pass either route. The aggregate parameter identity ratio and each per-object row are both hard gates.

Alternative considered: give every parameter the same three synthetic time strata. Rejected because it fabricates evidence for static parameters and lets one deep parameter hide a shallow sibling.

### 5. Make prediction a separate stateful future-holdout contract

`model_semantics` is `pointwise` or `stateful_dynamic`. A pointwise receipt always records predictive status as not authorized. A predictive plan is accepted only for stateful semantics and binds exact prediction and future-holdout series, training identities, initial state, step size, signal scales, horizon, and threshold source.

PhysicsGuard compares aligned future points and emits accumulated normalized error, worst-step error, lag steps, phase error, drift, and error-growth stability. Training and future holdout are checked for path, hash, and case overlap. This validates an externally produced model rollout artifact; it does not claim that PhysicsGuard can simulate every external model itself.

Alternative considered: infer temporal prediction from pointwise residuals. Rejected because independent timestamp agreement does not prove state propagation.

### 6. Lock project closure to covered scope and receipt semantics

`validation_ready` and `validated_reuse_ready` require a passing non-snapshot adequacy receipt. `prediction_ready` additionally requires `stateful_dynamic` semantics and a passing predictive rollout receipt. Closure records the requested scope, covered scope, adequacy status, model semantics, and predictive status without recomputing native metrics.

### 7. Calibrate with positive and intentionally shallow cases

Focused tests include a representative adequate sample and intentionally shallow cases: one/two points from a 1000-point universe, endpoint-only and same-phase parameter selection, one shallow critical parameter among deep siblings, 10000 parameters or signals with only one/two selected, duplicate timestamps, skipped transient tags, repeated exclusion reasons, empty roles, snapshot closure, and pointwise prediction. A separate static case proves that time gates are not applied to static binding evidence. FlowGuard model inputs and replay labels mirror these cases so model, code, and tests bind the same obligations.

SkillGuard V2 calibrates the bridge with three current content-addressed native
outcomes: static-positive, time-varying-positive, and intentionally shallow.
The ordinary supervised check instead discovers and executes the validation
plan from `target_input_paths`; calibration data cannot impersonate target
execution. Its dynamic parameter universe uses native class identities: one
binding item and no time strata for `static`, versus the complete raw
denominator, the precommitted native `sqrt_n_stage_v1`/project/convergence
floor, early/middle/late, and model-contribution sentinels for each
`time_varying` object. Every raw row remains visible, but only native
cannot-omit event, boundary, and contribution sentinels are critical. This
lets 32 well-distributed rows represent 1000 when all native gates pass while
still rejecting 1, 2, or 3 shallow rows. Project-specific PhysicsGuard floors
remain native and may be stricter.

### 8. Retire the complete former SkillGuard V1 runtime, not only its two authority filenames

Product-level bounded snapshot and data compatibility remains a PhysicsGuard concern. It does not authorize a second SkillGuard runtime. The expanded retirement inventory includes former generic checkers, policy files, mutable reports/evidence/ledgers, target-local run outputs, and caches in addition to `work-contract.json` and `check_manifest.json`. The earlier narrow completion receipt is invalidated. A new immutable completion receipt is issued only after the exact V2 authority, PhysicsGuard family-parent consumption, source/install residual absence, and installation-currentness replay all close on one frozen identity.

### 9. Make candidate admission a separate target-owned check

Each `guard-model/contract.json` is frozen and checked without requiring a candidate. A separate `guard-model/candidate.json` then binds the current contract fingerprint, complete declared failure and obligation ids, native owner/route, and a two-event hash-linked authoring chain. Known-good and known-bad proofs depend on that candidate-binding check. This prevents a later purpose document from retroactively legitimizing an earlier shallow candidate.

### 10. Label proof strength by what the native evidence actually demonstrates

Dataset-validation failures keep `native_semantic_detection` only where an exact target-native pytest fixture directly asserts the bounded native finding or exception. Satellite proofs that only remove one governed obligation become `native_obligation_admission_gate`; their titles and claim boundary say only that a candidate without current native proof is rejected, and their expected finding is the actual `missing_target_obligation` code. SkillGuard still sees only target-declared checks and receipts.

### 11. Use one target-owned production identity sidecar and one installed runtime manifest

The scheduled package contains discovered domain inputs but no installation identity. A separate target-owned sidecar binds target id, run id, package ref/hash, trigger/execution ids, installation receipt, and installed runtime fingerprint. The loader requires the package, exactly one sidecar, and every content-addressed target input to equal the declared input set; generic request copies and in-package identity fields are rejected. Dataset validation bundles all current `physicsguard/**/*.py` sources plus a hash manifest under `.skillguard/runtime`, and guard-model admission checks that manifest without importing a global fallback.

### 12. Project target ownership through one fixed native-integrated identity

Every maintained target writes the exact PhysicsGuard owner and default route into its current SkillGuard source contract. Every real route binding uses the common `{binding_id, native_route_id, required_before_closure: true, source}` wire, and every declared purpose/candidate/known-good/known-bad check has exactly one common `{binding_id, evidence_source, native_check_id, required: true}` binding. A non-optional `skillguard.depth_profile.v2` repeats the exact owner, route inventory, complete declared-check inventory, `native-integrated` mode, `enforced` level, and sole required `enforced` closure so the compiler preserves and supervises the identity rather than stripping it as source-only metadata. Their covered obligations remain mandatory in that sole closure. `may_define_parallel_execution_route` and `may_define_skillguard_runtime_route` are both false, and the source is not independently release-eligible.

This identity is supervisory metadata, not a PhysicsGuard semantic model: prevented failures, physical/evidence boundaries, native oracles, proof strength, good/bad decisions, residual risk, and bounded claims remain exclusively in target-owned guard-model artifacts and evaluators. The depth profile contains no calibration, target classification, PhysicsGuard semantics, or selectable dimensions. Generic calibration policy, optional integration modes, compatibility readers, and alternate success routes remain forbidden.

Alternative considered: omit the integration fields to avoid duplicating PhysicsGuard semantics. Rejected because absence also hides the ownership boundary from the compiler and global router. The fixed identity records who owns execution without transferring what the route means.

## Risks / Trade-offs

- [Broad plans become more verbose] → Keep snapshot behavior backward compatible and provide complete templates plus derived defaults where authority is unambiguous.
- [The square-root floor is not project-level statistical proof] → Treat it as a growing anti-degeneracy floor plus stage/gap checks, never as a confidence interval; project and convergence floors may only strengthen it, and claims remain bounded to the exact receipt.
- [Large full-series validation is expensive] → Preserve sampling modes and TestMesh partitioning; background progress never counts as final evidence.
- [External prediction artifacts can be forged] → Bind exact hashes, model identity, training/holdout disjointness, and target-owned comparison receipt; keep producer execution provenance visible and bounded.
- [Role matrices use generic exclusions] → Enforce exclusion ratio, repeated-reason rejection, critical-target coverage, and family quotas for broad claims.
- [Peer edits stale earlier evidence] → Re-read each target before patching and rerun OpenSpec, FlowGuard, focused tests, and SkillGuard audits after the final source state.

## Migration Plan

1. Add schemas and evaluator helpers while preserving legacy snapshot receipt generation.
2. Update the repository fixture and templates so the existing broad example declares row lineage and adequacy thresholds.
3. Integrate adequacy and predictive results into native validation and project closure.
4. Update FlowGuard ownership/lifecycle/test evidence and target skills.
5. Run focused negative/positive tests, FlowGuard replay, OpenSpec verification, and relevant regression suites.
6. Remove the complete expanded V1 runtime surface, then issue a new completion receipt only after family reattachment, transactional installation parity, and installation-currentness replay.
7. Bind candidate artifacts to frozen purpose contracts, calibrate proof-strength claims, and complete the target-owned sidecar plus installed runtime manifest.
8. Leave release/version publication to the repository release workflow; this change is not archived, committed, or published until the shared identity follow-up closes.

Rollback is a source revert of this unarchived change and its implementation edits. Product-level bounded snapshot plans remain executable throughout migration, but there is no dormant SkillGuard V1 fallback.

## Open Questions

- Project-specific statistical confidence and domain event taxonomies remain target-project inputs. This change enforces their provenance and coverage, not one universal engineering threshold.
