# PhysicsGuard Model-Dataset Validation

## Entry boundary

Accept this route only when:

- A concrete model and contracted dataset must be checked for bounded consistency, validation, or prediction readiness.
- Coverage adequacy, calibration/holdout separation, residual envelopes, or future rollout must be evaluated.

Reject or hand off when:

- A concrete data file lacks a current passing contract. Handoff: the `test-file-contract-review` route.
- Required mappings remain unresolved before validation. Handoff: the `signal-mapping-review` route.

## Minimum workflow

1. Check that every referenced test-file contract passes.
2. Following the route protocol below, run `python -m physicsguard.cli validation run PLAN.yaml`.
3. Return the status, the `depth_summary`, open warnings, and only the covered scope.

## Required outputs

- `validation_status`
- `depth_summary`
- `adequacy_findings`
- `unsupported_claims`
- `bounded_validation_claim`

Claim boundary: A pass licenses only the exact low-fidelity model, dataset identities, mappings, sampled universe, operating envelope, semantics, and claim scope in the report.

## Route protocol

Use this route after concrete test data has passed
the `test-file-contract-review` route. Do not use it to bypass failed,
partial, stale, or review-required contracts.

## Workflow

1. Create or review a model validation plan:

   ```yaml
   validation_id: example_validation
   audit_file: path/to/hierarchy.yaml
   observed_file: path/to/observed.yaml
   contracts:
     - contract: path/to/contract.yaml
       required_status: pass
   calibration:
     enabled: false
     method: none
   ```

   A broad validation claim also needs `depth`: name the data files, field
   schema, parameter roles, testbench profile/version, and observed series by
   path, then declare `time_scope`, scenario/case ids, perturbations, and
   assumptions. When calibration is enabled, declare disjoint `training` and
   `holdout` files under `depth.split`. Every required signal needs a mapping
   edge with unit evidence, enough confidence, and no review flag in the
   referenced contracts.

   Set `depth.model_semantics` explicitly. `pointwise` means independent
   evaluations and cannot authorize prediction. `stateful_dynamic` means an
   external producer advances explicit state and is eligible for the
   future-rollout check; the label alone is not predictive evidence.

   For a non-snapshot claim, add `depth.adequacy` with project-sourced floors
   (selected points, distinct timestamps, span, maximum gap, per-signal and
   per-parameter depth, critical signals and parameters, families) and classify
   each relevant parameter as `static` or `time_varying` in
   `parameter_temporal_policies`. PhysicsGuard computes these coverages and
   reports every shortfall as a warning.

2. Run validation once:

   ```powershell
   python -m physicsguard.cli validation run PLAN.yaml
   ```

3. The default output is a compact summary: `status`, the direct no-fit
   result, calibration and holdout status, `findings` (envelope,
   redundant-sensor, mapping and adequacy), safe claim, unsafe claim boundary
   and next actions. Add `--json` only for the full `depth` computation or the
   confidence updates. Then read
   `depth_summary`: covered scope, mapping status, series audit result,
   envelope violations, split status, and `adequacy` (signals and parameters
   below their floors). Every adequacy warning narrows the claim; a plan
   without `depth` supports only a snapshot.

## Predictive Boundary

Prediction needs `model_semantics: stateful_dynamic` and a
`depth.predictive_rollout` plan whose future holdout is disjoint from training by
path, file content, and case id. PhysicsGuard compares the externally generated
trajectory (alignment, error, lag, drift, stability); it does not turn a
pointwise relation into a simulator.

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
- Training and holdout must be disjoint by resolved path, file content, and
  case id. Renaming identical content does not create a valid holdout.
- The plan's selected rows and signals do not define the coverage universe.
  PhysicsGuard derives it from current manifests, role matrices, hierarchy,
  and contract mapping edges; exclusions need explicit, non-template reasons.

## Safe Claim Boundary

A passing validation supports only a scoped low-fidelity model-dataset claim
inside the checked contracts, files, mapping review, time points, scenarios,
perturbations, model, assumptions, residual series, and physical envelopes. It
is not high-fidelity
proof, dynamic interpolation, universal model understanding, or
commercial-model equivalence.
