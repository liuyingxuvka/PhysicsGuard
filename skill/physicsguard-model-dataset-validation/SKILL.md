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

3. Run validation:

   ```powershell
   python -m physicsguard.cli validation run PLAN.yaml --pretty
   ```

4. Inspect direct no-fit residuals, physical envelope findings,
   redundant-sensor findings, calibration status, holdout status, confidence
   updates, safe claim, unsafe claim boundary, and next actions.
5. If `evidence_registry` and `evidence_bundle_id` are declared, inspect
   evidence gap counts. Blocking gaps prevent validation pass; review and
   optional gaps must stay visible in the claim boundary.
6. If the validated project is listed in an external database ledger, report
   the current validation status, closure boundary, and remaining gaps as
   provider evidence only. Do not update the ledger from this PhysicsGuard
   skill.
7. For final project validation-readiness claims, include the validation plan in
   a project closure plan and run:

   ```powershell
   python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
   ```

   A passing validation report is necessary for validation claims, but project
   closure checks whether the surrounding evidence, contracts, and skipped
   checks also permit the claim.

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
envelopes plus the referenced project evidence bundle. It is not high-fidelity
proof and not commercial-model equivalence.

<!-- BEGIN SKILLGUARD CONTRACT LAYER -->
## Purpose
Bind each physicsguard run to the declared integration mode, evidence, blockers, residual_risk, and claim_boundary.
## Entrypoint Scope
Covers physicsguard-model-dataset-validation plus explicitly routed local materials; no unrelated repos, private files, external services, publication, or release claims unless requested and routed.
## Local Material Routing
Use workspace, skill directory, user files, or configured project paths; keep private machine paths local and public instructions portable.
## Entrypoint Acceptance Map
Use SkillGuard as the runtime contract executor attached to the native route/check owner: PhysicsGuard skill family and local PhysicsGuard model/test workflow. It enforces contract gates through that native owner before progress or closure; duplicate SkillGuard-owned execution paths are invalid. Declared gates/routes: model understanding, evidence mapping, validation, closure.
## Use When
Use when the request matches physicsguard-model-dataset-validation and needs this governed workflow, materials, checks, or handoff behavior.
## Do Not Use When
Do not use outside the domain, without required materials, when a more specific skill owns the work, or for tiny direct answers.
## Required Workflow
Select the target-owned native route/check surface, run the SkillGuard contract gates around the native workflow, collect evidence, run checks, fix failures, then report.
## Hard Gates
Do not skip phases, do not replace required evidence with prose, do not treat stale reports as current, do not weaken validation to pass, and do not claim completion when blockers remain.
## Output Requirements
Report evidence, failures, blockers, skipped_checks with reasons, residual_risk, and claim_boundary; distinguish checked, unchecked, blocked, and uncertain.
## SkillGuard Maintenance
Keep `.skillguard` contracts, checks, evidence, and ledger current; rerun SkillGuard after entrypoint, route, evidence, or closure changes.
<!-- END SKILLGUARD CONTRACT LAYER -->
