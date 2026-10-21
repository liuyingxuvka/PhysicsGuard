---
name: physicsguard-model-dataset-validation
description: "Use directly after test-file contracts pass to check a low-fidelity model against the contracted dataset: no-fit residuals, envelopes, calibration with holdout, and validation-depth warnings, with bounded claims."
---

# PhysicsGuard Model-Dataset Validation

## Entry boundary

Accept this route only when:

- A concrete model and contracted dataset must be checked for bounded consistency, validation, or prediction readiness.
- Coverage adequacy, calibration/holdout separation, residual envelopes, or future rollout must be evaluated.

Reject or hand off when:

- A concrete data file lacks a current passing contract. Handoff: `physicsguard-test-file-contract-review`.
- Required mappings remain unresolved before validation. Handoff: `physicsguard-signal-mapping-review`.

## Minimum workflow

1. Check that every referenced test-file contract passes.
2. Load the native route protocol and run `python -m physicsguard.cli validation run PLAN.yaml`.
3. Return the status, the `depth_summary`, open warnings, and only the covered scope.

If `python -m physicsguard.cli --help` fails, install the engine once with `python -m pip install -e <PhysicsGuard checkout>`; there is no version gate.

## Conditional detail loading

- Load `references/native-route-protocol.md` after route selection when domain execution needs the detailed workflow.
- Do not load another PhysicsGuard skill's references merely because the skills are related; hand off to that skill instead.

## Hard gates

- Keep non-pass states and unknowns visible.
- AI narration, inventories and template previews are not evidence; only PhysicsGuard command output is.
- Keep pointwise consistency distinct from stateful prediction and keep every claim inside the exact checked boundary.

## Required outputs

- `validation_status`
- `depth_summary`
- `adequacy_findings`
- `unsupported_claims`
- `bounded_validation_claim`

Claim boundary: A pass licenses only the exact low-fidelity model, dataset identities, mappings, sampled universe, operating envelope, semantics, and claim scope in the report.
