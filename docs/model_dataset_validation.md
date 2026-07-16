# Model-Dataset Validation

Model-dataset validation starts after relevant test-file contracts pass. It
checks whether a low-fidelity PhysicsGuard model is consistent with contracted
test data inside an explicit boundary.

## Flow

```text
contract pass
  -> project evidence bundle gap-check when declared
  -> exact dataset/schema/testbench/parameter-role identity
  -> current signal-mapping review gate
  -> direct no-fit validation
  -> explicit snapshot/time-window/scenario-set scope
  -> artifact-derived sample universe and per-object adequacy
  -> pointwise residual-series and physical-envelope checks
  -> redundant-sensor checks
  -> optional conservative calibration
  -> content/path/case-disjoint holdout validation
  -> native validation-depth receipt and report hash
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
python -m physicsguard.cli validation receipt PLAN.yaml --pretty
```

The report separates direct audit pass, calibration optimizer status, holdout
audit pass, final validation status, safe claim, unsafe claim boundary, and next
actions.

The optional `depth` section is required for broad validation-readiness claims.
It binds exact SHA-256 identities for data files, field schema, parameter roles,
testbench profile/version, mapping registry, and observed series. It also
declares time scope, scenario/case ids, perturbations, assumptions, and—when
calibration is enabled—disjoint training and holdout identities.

The depth receipt preserves every evaluated point, missing/invalid intervals,
aggregate residual statistics, physical-envelope violation intervals, mapping
review state, and the containing report identity. A legacy plan without
`depth` remains executable but its receipt is partial and snapshot-only. One
or two scalar checks never imply temporal behavior or general model
understanding.

Project closure and supervisory contract tools consume the native receipt.
They must not recompute physical residuals or reinterpret PhysicsGuard's
physical pass/fail logic.

When a validation plan declares `evidence_registry` and `evidence_bundle_id`,
blocking project evidence gaps prevent validation pass. Review and optional gaps
remain visible in the validation claim boundary.

If the project is listed in an external database ledger, report the current
validation status, safe claim boundary, and remaining gaps as provider evidence
only. PhysicsGuard does not refresh or maintain the surrounding ledger.

A passing depth receipt is still bounded low-fidelity evidence. It does not
recover commercial solver internals, prove commercial-model equivalence, or
license extrapolation outside the exact files, mappings, time points, and
scenarios in the receipt.

## Quantitative validation adequacy

Every non-snapshot depth plan must include an `adequacy` policy whose thresholds
come from a named project, testbench, engineering, or approved review source.
It also names a stable `selection_policy_id` and explains the predeclared
selection in `selection_rationale`; the resulting policy fingerprint prevents
an AI from lowering the sample after seeing the result.
PhysicsGuard derives the available point/signal/parameter universe from the
hashed manifest, role matrix, hierarchy, evidence registry, and bundle. A plan
cannot establish coverage merely by declaring its own selected count.

The native adequacy receipt distinguishes available, eligible, selected,
evaluated, and validated points and signals. It checks source-row lineage and
uniqueness; start/middle/end strata; distinct timestamps, span, and maximum
gap; required events, peaks, boundaries, and operating modes; per-signal point
count, ratio, span, and gap; critical signals and hierarchy-required
parameters; subsystem/family quotas; and exclusion ratios and repeated
template reasons. Every hierarchy, critical, calibration, or fact-bound
parameter is separately classified from a named project source as `static` or
`time_varying`. Static parameters need one current binding/value identity and
are never forced through time strata. Each time-varying parameter names its
denominator as `manifest:rows` or a bound manifest field with a non-null count,
then independently passes its own selected/available ratio, validated count,
distinct-time, span, maximum-gap, universal early/middle/late, and at least
three project-declared row-position strata. The strata use the raw row universe,
not the minimum and maximum of the selected subset, so several early-phase
points cannot relabel themselves as full-window coverage. One shallow parameter
cannot hide behind many deep parameters. Supported sampling policies are `full`, `stratified`,
`event_aware`, `adaptive`, and `project_declared`; adaptive sampling additionally
requires a declared convergence receipt and precommitted convergence floors.

Representative modes also apply the native `sqrt_n_stage_v1` floor
`min(N, max(12, ceil(sqrt(N))))` to the global point universe and independently
to every time-varying parameter. The final count is the strictest count implied
by the native, plan, project, and current convergence count/ratio floors. Full
mode additionally requires `N`. The native row-gap limit and universal plus
project strata prevent a formally large sample from collapsing into one phase.
For example, the native anti-degeneracy floor is 32 for `N=1000`: three widely
spaced points still fail, while 32 well-distributed points can proceed to the
remaining project and physics gates without forcing all 1000 rows.

When the complete aligned sequence is available, `full` is the default and the
native evaluator validates every row. Representative modes remain available for
large projects, but they authorize only a bounded claim and retain their
predeclared count/ratio, event and phase floors. Each representatively sampled
time-varying parameter also needs native residual evidence, a declared
perturbation observed at more than one value, and a physical envelope. Each
observed parameter value is actually applied to the executable component model.
PhysicsGuard then resets that one parameter to its model baseline and compares
the normalized residuals. A sensitive parameter must cross its declared effect
floor and identify affected residuals; a verified non-sensitive parameter must
stay below its ceiling and carry an exact reason and bounded claim disposition.
A disconnected parameter, a misspelled model target, or a value that is merely
stored in the observation cannot pass this gate.

These are universal minimum safeguards, not an attempt to prescribe
project-level numerical accuracy. A project can and should set stricter floors.
One or two points from a 1,000-row parameter history, several points from only
one phase, two parameters from a 10,000-parameter universe, two signals from a
10,000-signal universe, duplicate timestamps, or thousands of identical
exclusion reasons cannot support a broad validation claim.

For non-trivial, broad, reuse-ready, or predictive conclusions, the native
receipt must then be consumed by a current SkillGuard V2 supervised run bound
to the exact target input paths. A quick local run without that receipt remains
`BOUNDARY_ONLY` or `BOUNDED_PARTIAL`; the supervisor does not recompute PhysicsGuard
physics, adequacy, or rollout metrics.

The supervised run executes the validation plan from the target-input set; its
portable calibration project is never accepted as a substitute for the target
project. Separate content-addressed calibrations prove one honest static
binding, one adequate time-varying history, and rejection of an intentionally
shallow history. SkillGuard's parameter projection is class-aware: static
objects have no invented time points, while each time-varying object preserves
its raw denominator, native dynamic floor, early/middle/late strata, and
model-contribution sentinels. Ordinary rows remain visible in the denominator
but are not all marked critical; otherwise representative sampling would be
silently converted into full sampling. PhysicsGuard's project or convergence
policy may and usually should be stricter than the native floor.

## Predictive rollout

`model_semantics: pointwise` means each observation is evaluated independently.
It may support a bounded consistency check, but it cannot support a prediction
claim. Prediction requires `model_semantics: stateful_dynamic` plus a
`predictive_rollout` plan that binds the exact model, training inputs,
externally produced trajectory, and disjoint future holdout by path, SHA-256,
and case identity.

The rollout must declare its producer receipt, initial state, step size and
unit, horizon, target signals and scales, and project-sourced thresholds.
PhysicsGuard checks alignment, strict future separation, worst-step and
accumulated normalized error, lag/phase error, drift, error growth, and
stability. PhysicsGuard validates the supplied stateful trajectory; it does not
pretend a pointwise residual formula is a simulator or reconstruct hidden
commercial-model dynamics.
