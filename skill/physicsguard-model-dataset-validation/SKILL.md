---
name: physicsguard-model-dataset-validation
description: Use after PhysicsGuard test-file contracts pass to validate a low-fidelity model against exact dataset identities with artifact-derived coverage adequacy, temporal and per-signal depth, current mapping review, explicit time/scenario scope, pointwise residual and envelope evidence, disjoint holdout, stateful future-rollout validation when prediction is requested, native receipts, and confidence feedback.
---

# PhysicsGuard Model-Dataset Validation

Use this route after concrete test data has passed
`physicsguard-test-file-contract-review`. Do not use it to bypass failed,
partial, stale, or review-required contracts.

## Workflow

1. Check every referenced test-file contract:

   ```powershell
   python scripts/run_physicsguard.py testfile contract-check CONTRACT.yaml --pretty
   ```

2. Create or review a model validation plan:

   ```yaml
   validation_id: example_validation
   evidence_registry: path/to/project_evidence_registry.yaml
   evidence_bundle_id: example_validation_bundle
   audit_file: path/to/hierarchy.yaml
   observed_file: path/to/observed.yaml
   contracts:
     - contract: path/to/contract.yaml
       required_status: pass
   calibration:
     enabled: false
     method: none
   ```

   A broad validation claim also requires `depth`. Bind the exact data files,
   field-schema file, parameter-role file, testbench profile/version, mapping
   registry and bundle, observed-series file, and every expected SHA-256. Then
   declare `time_scope`, scenario/case ids, perturbations, and assumptions.
   When calibration is enabled, declare content- and case-disjoint `training`
   and `holdout` identities under `depth.split`.

   Set `depth.model_semantics` explicitly. `pointwise` means independent
   evaluations and cannot authorize prediction. `stateful_dynamic` means an
   external producer advances explicit state and is eligible for the separate
   future-rollout gate; the label alone is not predictive evidence.

   Every non-snapshot plan must also declare `depth.adequacy`. Select one of
   `full`, `stratified`, `event_aware`, `adaptive`, or `project_declared`, name
   the project/testbench/engineering source of every threshold, and declare
   quantitative floors for selected points and ratio, distinct timestamps,
   time span and maximum gap, signal coverage, per-signal valid points and
   ratio, exclusions, critical signals/parameters, required event/peak/
   boundary/mode tags, and any family quotas. Adaptive sampling requires a
   current convergence evidence id plus precommitted convergence count/ratio
   floors globally and for every time-varying parameter.

   Classify every hierarchy-required, critical, calibration-role, or actively
   fact-bound parameter in `parameter_temporal_policies` as `static` or
   `time_varying`, with a named classification source. Static parameters need
   current binding evidence. Each time-varying parameter must itself meet the
   declared per-parameter point count/ratio, distinct-time, span, and maximum-
   gap floors; depth in other signals cannot compensate for a one-point
   parameter history. PhysicsGuard also applies the `sqrt_n_stage_v1`
   anti-degeneracy floor `min(N, max(12, ceil(sqrt(N))))`; the effective count
   is the strictest of that floor, plan, project, convergence, and (for `full`)
   the complete raw denominator. Project policy may strengthen this floor but
   cannot weaken it.

   When a complete aligned sequence is available, use `full` and evaluate all
   rows with the native vectorized route. Representative sampling is allowed
   only for an explicitly bounded claim and only when the plan already carries
   a stable `selection_policy_id`, a concrete `selection_rationale`, a named
   threshold source, non-lowerable count/ratio floors, and event coverage. The
   native receipt computes and binds the current policy fingerprint. The AI
   must not choose one or two convenient points after seeing the result.

   A time-varying parameter must name its target-owned denominator
   (`manifest:rows` or a bound manifest field), its own point/ratio/distinct-
   time/span/maximum-gap floors, and at least three project-declared row-
   position strata. PhysicsGuard also requires universal early/middle/late
   coverage, so several points from one phase cannot impersonate a long
   history. For representative sampling, each time-varying parameter also
   needs current residual evidence, a declared perturbation with observed
   direction, and a physical envelope. It must declare `sensitive` with a
   positive normalized contribution floor or `verified_non_sensitive` with an
   effect ceiling, exact reason, and bounded claim disposition. PhysicsGuard
   applies each observed value to the executable model and replays a baseline
   counterfactual; merely carrying the parameter value in a row is not model
   use. Static parameters declare no time or contribution fields and pass only
   through current binding evidence.

3. Run validation:

   ```powershell
   python scripts/run_physicsguard.py validation run PLAN.yaml --pretty
   ```

4. Inspect direct no-fit residuals, physical envelope findings,
   redundant-sensor findings, calibration status, holdout status, confidence
   updates, safe claim, unsafe claim boundary, and next actions.
   Also inspect `depth_receipt`: dataset and mapping identity, declared versus
   observed scope, scenario perturbations, split overlap, every residual point,
   invalid/missing intervals, envelope intervals, report hash, and receipt
   status. Inspect `depth_receipt.adequacy` separately: the artifact-derived
   available/eligible/selected/evaluated/validated universe, source-row
   lineage, start/middle/end strata, time gaps, event/peak/boundary/mode
   coverage, every signal's history, the signal-time matrix, critical and
   family coverage, every parameter's classification, resolved dynamic floor,
   row-gap bound, own time coverage, and counterfactual residual contribution,
   and exclusion diagnostics must pass. A scalar plan without
   `depth` remains usable only as a snapshot and must not support time-series,
   scenario, or general-understanding claims.
5. To emit only the target-owned receipt, run:

   ```powershell
   python scripts/run_physicsguard.py validation receipt PLAN.yaml --pretty
   ```

   Downstream consumers use this receipt. They must not recompute or
   reinterpret physical residuals themselves. PhysicsGuard must reconcile every
   native object and raw denominator, retain only true event/boundary/
   contribution sentinels as critical, and consume the precommitted native
   per-object floor. Treating every ordinary raw row as critical incorrectly
   turns representative validation into full validation and is a blocker.
6. If `evidence_registry` and `evidence_bundle_id` are declared, inspect
   evidence gap counts. Blocking gaps prevent validation pass; review and
   optional gaps must stay visible in the claim boundary.
7. If the validated project is listed in an external database ledger, report
   the current validation status, closure boundary, and remaining gaps as
   provider evidence only. Do not update the ledger from this PhysicsGuard
   skill.
8. For final project validation-readiness claims, include the validation plan in
   a project closure plan and run:

   ```powershell
   python scripts/run_physicsguard.py project closure PROJECT_CLOSURE_PLAN.yaml --pretty
   ```

   A passing validation report is necessary for validation claims, but project
   closure checks whether the surrounding evidence, contracts, and skipped
   checks also permit the claim. Set `required_checks.validation_depth: true`;
   closure consumes the native passing receipt and records
   `physical_recomputation: false` for that receipt gate.

## Predictive Boundary

When prediction is requested, a stateful model must declare
`depth.predictive_rollout` with exact model identity, training identities,
producer receipt, generated trajectory, unseen future-holdout identity,
training end time, initial state, step size/unit, horizon, target signals and
scales, project-sourced thresholds, and expected case ids. Training and future
evidence must be disjoint by resolved path, SHA-256, and case identity.

Inspect the native rollout receipt for alignment and strict future separation,
worst-step and accumulated normalized error, lag/phase error, drift, error
growth, and stability. Only a passing stateful receipt can be handed to
`prediction_ready` closure. PhysicsGuard validates an externally generated
trajectory; it does not turn a pointwise residual function into a simulator.

## PhysicsGuard Execution-Depth Boundary

Any non-trivial, broad, validation-ready, reuse-ready, or predictive conclusion
must run the target-owned PhysicsGuard validation route against the exact plan,
hierarchy, manifest, role matrix, evidence registry, observed series, and
prediction or holdout artifacts when present. A bundled calibration fixture
proves only the fixture and cannot stand in for current target execution.

Counts, parameter-name lists, catalog expansion, whole-receipt hashes, and
ordinal time ranges are not per-obligation evidence. Every satisfied parameter,
time-stratum, counterfactual, convergence, and prediction obligation must retain
its exact target-native semantic object, evidence reference, and content hash.
Missing, renamed, overlapping, mechanically generated, or summary-only mappings
block validation-ready, reuse-ready, and predictive closure.

A local quick check without a current PhysicsGuard execution-depth receipt is
`BOUNDARY_ONLY` or `BOUNDED_PARTIAL`. It may report the exact checked rows and
remaining gaps, but it must not claim general model understanding, deep
validation, reusable validation readiness, or prediction.

## Calibration Boundary

- First-version calibration is conservative: `none` or
  `bounded_least_squares`.
- Do not implement or claim Adam/SPSA unless a later explicit change adds that
  backend.
- Calibration may adjust only declared `calibration_candidate` parameters with
  finite bounds, finite initial values, and positive scales.
- Calibration must not mutate observed values or raw test data.
- `optimization_success` is not `validation_pass`.
- If holdout validation fails, the final validation claim is partial or failed
  even when the optimizer converged.
- Training and holdout must be disjoint by resolved path, content hash, and
  case id. Renaming identical content does not create a valid holdout.
- The plan's selected rows and signals do not define the coverage universe.
  PhysicsGuard derives it from current manifests, role matrices, hierarchy,
  and evidence bindings; exclusions need explicit, non-template reasons.

## Safe Claim Boundary

A passing validation supports only a scoped low-fidelity model-dataset claim
inside the exact checked contract, file hashes, mapping review, time points,
scenarios, perturbations, model, assumptions, residual series, and physical
envelopes plus the referenced project evidence bundle. It is not high-fidelity
proof, dynamic interpolation, universal model understanding, or
commercial-model equivalence.



<!-- BEGIN MANAGED VALIDATED TEMPLATE PACK -->
## Validated Template Pack Routing

- Target families: `physicsguard`; native owner: `physicsguard.purpose-pack-selector.v1`.
- Current catalogs: `physicsguard.purpose-template-packs` revision `1`.
- Resolve the task through this Guard's native router first, then ask the target-owned adapter for a current neutral projection; never infer a template from wording or a skill name.
- Preserve the adapter's complete candidate and rejection accounting. Zero candidates may use only the declared validated base; one candidate gets a read-only preview; many candidates require complete dependencies, pairwise compatibility, one field owner, and target-authored dominance or must block as ambiguous.
- Recompute the projection immediately before applying a preview. A stale request, catalog, route, builder, validator, or content identity blocks all writes.
- Hand the selected preview to the target-declared builder and consume every target-native validator receipt. Template structure is not domain validity, completion, installation, release, or publication evidence.
- Record a harvest disposition after creating or materially deepening a reusable model, and keep no-match evidence visible.
- Declared validated bases: `physicsguard.base.audit-work-package`.
- Template inventory: `physicsguard.base.audit-work-package`, `physicsguard.dataset-validation-basic`, `physicsguard.dataset-validation-comprehensive`, `physicsguard.model-understanding-preflight`, `physicsguard.signal-mapping-core`, `physicsguard.signal-mapping-evidence`.
- Native validator inventory: `physicsguard.template-pack-instance-validator.v1`, `physicsguard.template-pack-manifest-validator.v1`, `physicsguard.template-pack-selection-validator.v1`.
- Claim boundaries: The catalog supports deterministic workflow-pack selection and structural native validation only; physical truth, dataset adequacy, audit_pass, installation, and release require separate current PhysicsGuard evidence.
<!-- END MANAGED VALIDATED TEMPLATE PACK -->

<!-- BEGIN MANAGED PURPOSE AND BLOCKABILITY -->
## PhysicsGuard dynamic model-purpose and family baseline

Family capability baseline purpose: Prevent a model/dataset consistency or predictive claim unless exact model, dataset, mapping, signal, parameter, time, scenario, physical-envelope, and claim-scope obligations pass the native evaluator.

Family route bounded claim: A pass licenses only the exact low-fidelity model, dataset identities, mappings, sampled universe, operating envelope, semantics, and claim scope in the receipt.

Family baseline proof boundary: A pass licenses only the exact low-fidelity model, dataset identities, mappings, sampled universe, operating envelope, semantics, and claim scope in the receipt.

The bundled `guard-model/` files declare these maintained family baseline regression classes:

- `Validation identity is wrong` (native_semantic_detection): block when the model, dataset, plan, mapping, split, or receipt identity is missing, stale, or mismatched. Claim boundary: Native semantic detection is limited to tests/test_validation_depth_receipts.py::test_changed_dataset_content_makes_receipt_stale and its asserted observation 'dataset_identity_stale'.
- `Coverage universe is shallow` (native_semantic_detection): block when signals, parameters, timepoints, events, scenarios, or families are missing or inadequately sampled. Claim boundary: Native semantic detection is limited to tests/test_validation_adequacy.py::test_10000_signals_with_only_two_selected_are_blocked and its asserted observation 'signal_coverage_ratio_not_met'.
- `Physical relation or envelope is violated` (native_semantic_detection): block when native residual, unit, sign, balance, constitutive, or physical-envelope checks fail. Claim boundary: Native semantic detection is limited to tests/test_model_dataset_validation.py::test_conservative_calibration_does_not_turn_direct_failure_into_pass and its asserted observation 'direct_validation_audit_failed'.
- `Prediction semantics are overclaimed` (native_semantic_detection): block when pointwise evidence or a stale/partial rollout is used to authorize prediction. Claim boundary: Native semantic detection is limited to tests/test_predictive_rollout_validation.py::test_pointwise_prediction_is_forbidden and its asserted observation 'pointwise_prediction_forbidden'.
- `Validation scope is overreached` (native_semantic_detection): block when the requested claim exceeds the native receipt's covered scope. Claim boundary: Native semantic detection is limited to tests/test_validation_adequacy.py::test_snapshot_receipt_cannot_satisfy_validation_ready_closure and its asserted observation 'snapshot_scope_incompatible'.

These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.

For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.

Use `guard-model/verify.py check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.

`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.

`guard-model/verify.py` is the PhysicsGuard-native verifier. It proves only the declared family baseline and never replaces current task evidence or PhysicsGuard domain judgment.
<!-- END MANAGED PURPOSE AND BLOCKABILITY -->
