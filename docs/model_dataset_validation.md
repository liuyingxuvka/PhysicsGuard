# Model-Dataset Validation

Model-dataset validation starts after relevant test-file contracts pass. It
checks whether a low-fidelity PhysicsGuard model is consistent with contracted
test data inside an explicit boundary.

## Flow

```text
contract pass
  -> project evidence bundle gap-check when declared
  -> direct no-fit validation
  -> physical envelope checks
  -> redundant-sensor checks
  -> optional conservative calibration
  -> holdout validation
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

The report separates direct audit pass, calibration optimizer status, holdout
audit pass, final validation status, safe claim, unsafe claim boundary, and next
actions.

When a validation plan declares `evidence_registry` and `evidence_bundle_id`,
blocking project evidence gaps prevent validation pass. Review and optional gaps
remain visible in the validation claim boundary.

If the project is listed in an external database ledger, report the current
validation status, safe claim boundary, and remaining gaps as provider evidence
only. PhysicsGuard does not refresh or maintain the surrounding ledger.
