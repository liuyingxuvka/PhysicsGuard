---
name: physicsguard-model-dataset-validation
description: "Use directly after current test-file contracts pass to validate a low-fidelity model against exact dataset, mapping, signal, parameter, time, scenario, envelope, holdout, and predictive-rollout identities with target-owned native receipts and bounded claims."
---

# PhysicsGuard Model-Dataset Validation

## Entry boundary

Route: `route:physicsguard-model-dataset-validation`; native owner: `physicsguard-model-dataset-validation`; role: `independent direct route`. Read `references/route-capsule.json` to confirm this exact identity and the machine-checkable decision boundary.

Accept this route only when:

- A concrete model and contracted dataset must be checked for bounded consistency, validation, or prediction readiness.
- Coverage adequacy, calibration/holdout separation, residual envelopes, or future rollout must be evaluated.

Reject or hand off when:

- A concrete data file lacks a current passing contract. Handoff: `physicsguard-test-file-contract-review`.
- Required mappings remain unresolved before validation. Handoff: `physicsguard-signal-mapping-review`.

## Minimum workflow

1. Verify every referenced file contract and exact model, dataset, mapping, and plan identity.
2. Load the native route protocol and run direct residual, envelope, adequacy, split, and rollout checks required by the claim.
3. Return the native receipt, current blockers, and only the exact covered scope.

Before executing a native command, verify the installed `physicsguard` version against `runtime-requirements.json`; a missing or mismatched runtime is a visible blocker with no fallback.

## Blueprint slice

Consume the current affected projection for bounded validation and the full qualified projection only when the requested claim covers the whole target. Report coverage per blueprint element and obligation, including validation mode, validity boundary, residual/oracle identity, dataset and evidence fingerprints, and every unsupported claim. This route does not author or fully review the blueprint. Aggregate pass counts cannot hide an uncovered member. Stale or missing projection identity blocks without a run-all or full-scan fallback.

## Conditional detail loading

- Load `references/native-route-protocol.md` after route selection when domain execution needs the detailed workflow.
- Load `references/native-depth-and-purpose.md` before creating, materially deepening, revising, or closing a task-local model. Do not load it for an ordinary bounded action.
- Load `references/template-pack-routing.md` only for target-owned template selection, preview, instantiation, validation, or harvest. Preview is not proof.
- Do not load another PhysicsGuard skill's references merely because the skills are related. Use an explicit typed handoff.

## Hard gates

- Preserve the target's native judgment, exact evidence identities, explicit unknowns, and non-pass states.
- Never treat AI self-report, prose completeness, progress, an inventory, or a template preview as native execution evidence.
- Keep pointwise consistency distinct from stateful prediction and keep every claim inside the exact checked boundary.
- Do not add a compatibility route, alias, fallback, copied runtime, or alternate success owner.

## Required outputs

- `validation_status`
- `depth_receipt`
- `adequacy_findings`
- `per_blueprint_element_coverage`
- `affected_slice_fingerprint`
- `unsupported_claims`
- `bounded_validation_claim`

Claim boundary: A pass licenses only the exact low-fidelity model, dataset identities, mappings, sampled universe, operating envelope, semantics, and claim scope in the receipt.
