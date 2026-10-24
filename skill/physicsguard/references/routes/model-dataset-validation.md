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
   schema, parameter roles, contract metadata/version, and observed series by
   path, then declare `time_scope`, scenario/case ids, perturbations, and
   assumptions. When calibration is enabled, declare disjoint `training` and
   `holdout` files under `depth.split`. Every required signal needs a field
   mapping with unit evidence, enough confidence, and no review flag in the
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
   Representative sampling also applies `sqrt_n_stage_v1`: `min(N, max(12, ceil(sqrt(N))))`; requested strata cover start/middle/end, events, peaks, boundaries and modes, and every time-varying parameter needs its own temporal coverage and model contribution.

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
The rollout declares initial state, step size/unit, horizon, declared signals/scales and project-sourced thresholds; optional `producer_id` identifies the trajectory-producing run.

## Calibration Boundary

- Calibration supports `none`, `bounded_least_squares` and `coarse_grid_then_least_squares`; the coarse grid only chooses a bounded starting point before least squares, not a global optimum.
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
  and contract fields; exclusions need explicit, non-template reasons.

## Safe Claim Boundary

A passing validation supports only a scoped low-fidelity model-dataset claim
inside the checked contracts, files, mapping review, time points, scenarios,
perturbations, model, assumptions, residual series, and physical envelopes. It
is not high-fidelity
proof, dynamic interpolation, universal model understanding, or
commercial-model equivalence.
For an external database ledger, return this validation status, safe boundary and remaining gaps as provider evidence; PhysicsGuard does not refresh or maintain the surrounding ledger.

## Single-file data mapping
`testfile manifest` → `testfile contract-check` → `testfile snapshot|series`
reads one contract's `fields`. Use `references/templates/test_file_contract.yaml`
in the installed skill. A validation plan's `depth.dataset.parameter_roles` and
`testbench` references point to that same contract; `metadata.testbench_version`
records the version named by the validation plan. Generated series use the
contract ID as `source_identity_id`; use that identity for its dataset file.
Units are converted before evaluation, with factor/offset and field@row retained.
Missing files, uncertain mappings, scope overreach, overlapping holdouts and
pointwise predictive claims remain hard gates. Ignored fields stay outside the
validated claim; adequacy floors must reflect their declared exclusion.

## Failing intervals and optional floors
The summary groups consecutive failed points until a passing/unevaluated point,
a scenario boundary, or a different worst block. `failing_intervals` names the
start/end point and time, count, worst block/residual and maximum absolute
normalized residual. Full JSON retains every evaluated point and interval
finding details retain the point IDs; the summary does not repeat point rows.

Start with the installed `references/templates/model_validation_plan.yaml`.
`depth.adequacy: {}` uses the manifest's usable point count, time span and maximum
gap. Adjacent-row contracts have N-1 usable single-step points from N raw rows.
Only declared additional signal/parameter floors, tag requirements, strata and
family quotas are enforced; their shortfalls remain warnings. Explicit parameter
classification/contribution evidence and all native hard gates remain required
when that parameter scope is requested. Manifest metadata records the actual
maximum gap; refresh older manifests to obtain those facts.

Contract field mappings supply validation roles by default. Plan rows override only explicitly authored fields for the same target. When `depth.observed_series` is omitted, validation reads the native contract series in memory. A missing declared input is reported once; dependent checks are marked `not_run`. Mapping confidence uses `high`, `medium`, `low` or `proposed`; measurement and computed validation confidence stay numeric.
