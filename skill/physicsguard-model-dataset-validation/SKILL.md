---
name: physicsguard-model-dataset-validation
description: Use after PhysicsGuard test-file contracts pass to validate a low-fidelity model against contracted test data with direct residual checks, physical envelopes, redundant-sensor consistency, conservative bounded calibration, holdout validation, and confidence feedback.
---

# PhysicsGuard Model-Dataset Validation

Use this route after concrete test data has passed
`physicsguard-test-file-contract-review`. Do not use it to bypass failed,
partial, stale, or review-required contracts.

## Workflow

1. Check every referenced test-file contract:

   ```powershell
   python -m physicsguard.cli testfile contract-check CONTRACT.yaml --pretty
   ```

2. Create or review a model validation plan:

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

3. Run validation:

   ```powershell
   python -m physicsguard.cli validation run PLAN.yaml --pretty
   ```

4. Inspect direct no-fit residuals, physical envelope findings,
   redundant-sensor findings, calibration status, holdout status, confidence
   updates, safe claim, unsafe claim boundary, and next actions.

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

## Safe Claim Boundary

A passing validation supports only a scoped low-fidelity model-dataset claim
inside the checked contract, observed data, model, assumptions, and physical
envelopes. It is not high-fidelity proof and not commercial-model equivalence.
