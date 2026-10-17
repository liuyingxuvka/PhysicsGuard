## Context

The existing model-dataset validator owns exact dataset identity, signal mapping, pointwise residual evaluation, physical envelopes, split identity, and the native depth receipt. Its current time gate distinguishes one-point snapshots from multi-point evidence, but the selected sample is self-declared and is not reconciled with raw manifest row counts, hierarchy-required targets, timestamp distribution, or a predictive trajectory contract. Project closure consumes a passing receipt without comparing the requested closure claim to the receipt's scope or model semantics.

PhysicsGuard must remain a low-fidelity audit framework. It must not reverse engineer a commercial solver or pretend that a target-neutral supervisor can choose domain sample sizes. PhysicsGuard owns validation, adequacy, prediction and current evidence boundaries.

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
- Claim that a validated rollout proves behavior outside the exact model, initial state, step, horizon, files, and thresholds in the receipt.

## Decisions

### 1. Extend the existing native validator through focused helper owners

`physicsguard.core.model_dataset_validation` and the existing validation-depth route remain the public owner. Quantitative adequacy and rollout comparison live in focused schema/core helpers and are assembled into the existing native receipt. This avoids a parallel validator and keeps the already-large pointwise evaluator from becoming the only implementation surface.


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

### 7. Verify native behavior once

Use the existing native adequacy, predictive-rollout, model-dataset, current-model and depth tests. Ordinary validation runs produce their own depth receipt; the receipt command is an alternate output path. Strict model creation/revision/closure keeps its exact candidate and independent evidence requirements. Consumer maintenance uses current map pointers and ordinary file generation/install/sync without an author-proof supervisor.

## Risks / Trade-offs

- [Broad plans become more verbose] → Keep snapshot behavior backward compatible and provide complete templates plus derived defaults where authority is unambiguous.
- [The square-root floor is not project-level statistical proof] → Treat it as a growing anti-degeneracy floor plus stage/gap checks, never as a confidence interval; project and convergence floors may only strengthen it, and claims remain bounded to the exact receipt.
- [Large full-series validation is expensive] → Preserve sampling modes and TestMesh partitioning; background progress never counts as final evidence.
- [External prediction artifacts can be forged] → Bind exact hashes, model identity, training/holdout disjointness, and target-owned comparison receipt; keep producer execution provenance visible and bounded.
- [Role matrices use generic exclusions] → Enforce exclusion ratio, repeated-reason rejection, critical-target coverage, and family quotas for broad claims.

## Migration Plan

1. Add schemas and evaluator helpers while preserving legacy snapshot receipt generation.
2. Update the repository fixture and templates so the existing broad example declares row lineage and adequacy thresholds.
3. Integrate adequacy and predictive results into native validation and project closure.
4. Update FlowGuard ownership/lifecycle/test evidence and target skills.
5. Run focused negative/positive tests, FlowGuard replay, OpenSpec verification, and relevant regression suites.
6. Retire obsolete author-control files and verify ordinary consumer installation/sync in a temporary directory.
7. Bind candidate artifacts to frozen purpose contracts, calibrate proof-strength claims, and complete the target-owned sidecar plus installed runtime manifest.
8. Leave release/version publication to the repository release workflow; this change is not archived, committed, or published until the shared identity follow-up closes.


## Open Questions

- Project-specific statistical confidence and domain event taxonomies remain target-project inputs. This change enforces their provenance and coverage, not one universal engineering threshold.

Current maintenance uses the repository map, ordinary pytest, native validation models and the transactional consumer installer. Obsolete family author-proof receipts and control manifests are retired.
