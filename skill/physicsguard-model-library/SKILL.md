---
name: physicsguard-model-library
description: "Use directly to index or select reusable PhysicsGuard model assets and check profile, testbench, validation-receipt, known-limit, gap, predictive-horizon, and bounded-reuse compatibility without storing raw datasets or implying universal validity."
---

# PhysicsGuard Model Library

## Entry boundary

Route: `route:physicsguard-model-library:reuse`; native owner: `physicsguard.model-library`; role: `independent direct route`. Read `references/route-capsule.json` to confirm this exact identity and the machine-checkable decision boundary.

Accept this route only when:

- The task is to index validated model assets or decide whether one is reusable for a named target context.
- Asset, profile, testbench, validation, gap, or predictive-horizon compatibility must be checked.

Reject or hand off when:

- The asset has no current model/dataset validation receipt. Handoff: `physicsguard-model-dataset-validation`.
- The request is a cross-project database or historical-ledger query. Handoff: `none`.

## Minimum workflow

1. Bind the selected asset and exact target profile/testbench context.
2. Load the native route protocol and check current compatibility, validation, gaps, and known limits.
3. Report only the exact reusable boundary; keep database-level discovery out of scope.

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

- `compatible_assets`
- `reuse_status`
- `gaps`
- `bounded_reuse_scope`

Claim boundary: Library readiness licenses only the selected asset/profile/testbench combination and exact bounded reuse scope; it does not validate a new project automatically.
