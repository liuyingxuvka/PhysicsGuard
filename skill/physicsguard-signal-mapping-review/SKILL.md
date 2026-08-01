---
name: physicsguard-signal-mapping-review
description: "Use directly when external signals or parameters are mapped into PhysicsGuard variables and target identity, units, conversion, revision, confidence, reviewer state, temporal depth, interval bounds, or stale conditions must be checked before residual claims."
---

# PhysicsGuard Signal Mapping Review

## Entry boundary

Route: `route:physicsguard-signal-mapping-review:review`; native owner: `physicsguard.signal-mapping-review`; role: `independent direct route`. Read `references/route-capsule.json` to confirm this exact identity and the machine-checkable decision boundary.

Accept this route only when:

- The task concerns external-signal or parameter mapping identity, unit, conversion, confidence, review, timing, or staleness.
- Mapping evidence must be resolved before residual, adequacy, or predictive checks can use it.

Reject or hand off when:

- A concrete many-field test file first needs a complete field contract. Handoff: `physicsguard-test-file-contract-review`.
- Mappings are current and the task is exact model/dataset validation. Handoff: `physicsguard-model-dataset-validation`.

## Minimum workflow

1. Bind every governed external object to its exact target, unit, conversion, revision, and evidence.
2. Load the native route protocol and check confidence, review, time coverage, intervals, and stale conditions.
3. Keep unresolved mappings visible and do not mutate observed values.

Before executing a native command, verify the installed `physicsguard` version against `runtime-requirements.json`; a missing or mismatched runtime is a visible blocker with no fallback.

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

- `mapping_status`
- `review_gaps`
- `temporal_boundary`
- `safe_mapping_claim`

Claim boundary: A mapping pass licenses only the exact external signal, target variable, conversion, revision, temporal range, and reviewed confidence in the receipt.
