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
