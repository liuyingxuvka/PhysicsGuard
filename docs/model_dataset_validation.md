# Model-Dataset Validation

Model-dataset validation starts after relevant test-file contracts pass. It
checks whether a low-fidelity PhysicsGuard model is consistent with contracted
test data inside an explicit boundary.

## Flow

```text
contract pass
  -> dataset/schema/testbench/parameter-role files
  -> contract mapping-edge review
  -> direct no-fit validation
  -> explicit snapshot/time-window/scenario-set scope
  -> artifact-derived sample universe and per-object adequacy
  -> pointwise residual-series and physical-envelope checks
  -> redundant-sensor checks
  -> optional conservative calibration
  -> content/path/case-disjoint holdout validation
  -> validation-depth warnings and a compact depth summary
  -> confidence feedback
```

The first version supports `none`, `bounded_least_squares`, and
`coarse_grid_then_least_squares`. The coarse-grid mode only chooses a small
bounded starting point before least squares; it is not a global optimizer.
Adam and SPSA are future backends. Optimizer convergence is reported as
`optimization_success`; it is not the same as validation pass.

Calibration may change only explicit bounded calibration parameters. It must
not change observed values.

## Commands

```powershell
python -m physicsguard.cli validation run PLAN.yaml --pretty
```

The report contains a compact `depth_summary` and the full `depth` details.

The report separates direct audit pass, calibration optimizer status, holdout
audit pass, final validation status, safe claim, unsafe claim boundary, and next
actions.

The optional `depth` section is required for broad validation-readiness claims.
It names the data files, field schema, parameter roles, testbench
profile/version, and observed series by path; the required signals are checked
against the field declarations of the referenced single-file contracts. It also
declares time scope, scenario/case ids, perturbations, assumptions, and—when
calibration is enabled—disjoint training and holdout files.

The `depth` details keep every evaluated point, missing/invalid intervals,
aggregate residual statistics, physical-envelope violation intervals, and the
mapping review. A legacy plan without `depth` remains executable but is reported
as snapshot-only. One or two scalar checks never imply temporal behavior or
general model understanding.

If the project is listed in an external database ledger, report the current
validation status, safe claim boundary, and remaining gaps as provider evidence
only. PhysicsGuard does not refresh or maintain the surrounding ledger.

A passing depth check is still bounded low-fidelity evidence. It does not
recover commercial solver internals, prove commercial-model equivalence, or
license extrapolation outside the exact files, mappings, time points, and
scenarios that were checked.

## Quantitative validation adequacy

Every non-snapshot depth plan should include an `adequacy` policy whose
thresholds come from a named project, testbench, engineering, or review source.
PhysicsGuard derives the available point, signal, and parameter universe from
the manifest, contract field roles, hierarchy, and contract fields, so a plan
cannot establish coverage merely by declaring its own selected count.

The adequacy computations check temporal spread (distinct timestamps, span,
maximum gap, start/middle/end strata, events, peaks, boundaries, modes),
per-signal depth, critical signals and parameters, family quotas, exclusions,
and every time-varying parameter separately (its own point count, ratio, span,
gap, strata, and counterfactual model contribution). Static parameters are
bound by the value the executable model declares. Representative sampling also
applies the `sqrt_n_stage_v1` floor `min(N, max(12, ceil(sqrt(N))))`.

Every adequacy shortfall is reported as a **warning**: the validation status
becomes `partial`, `depth_summary.adequacy` lists the signals and parameters
below their floors, and the safe claim stays inside the covered scope. One or
two points from a long history, several points from one phase, or a few
signals from a large universe cannot support a broad validation claim.

## Predictive rollout

`model_semantics: pointwise` means each observation is evaluated independently.
It may support a bounded consistency check, but it cannot support a prediction
claim. Prediction requires `model_semantics: stateful_dynamic` plus a
`predictive_rollout` plan that binds the exact model, training inputs,
externally produced trajectory, and disjoint future holdout by path, file
content, and case identity.

The rollout must declare its initial state, step size and unit, horizon,
target signals and scales, and project-sourced thresholds. A
`producer_id` naming the run that produced the trajectory is optional.
PhysicsGuard checks alignment, strict future separation, worst-step and
accumulated normalized error, lag/phase error, drift, error growth, and
stability. PhysicsGuard validates the supplied stateful trajectory; it does not
pretend a pointwise residual formula is a simulator or reconstruct hidden
commercial-model dynamics.

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
