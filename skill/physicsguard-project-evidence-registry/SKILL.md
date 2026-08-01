---
name: physicsguard-project-evidence-registry
description: "Use directly to create, audit, or navigate one PhysicsGuard project's evidence registry, profile, artifact map, binding expectations, evidence bundles, physical facts, critical gaps, and closure handoffs without replacing file contracts or model validation."
---

# PhysicsGuard Project Evidence Registry

## Entry boundary

Route: `route:physicsguard-project-evidence-registry:check`; native owner: `physicsguard.project-evidence-registry`; role: `independent direct route`. Read `references/route-capsule.json` to confirm this exact identity and the machine-checkable decision boundary.

Accept this route only when:

- One project's files, facts, bindings, bundles, and evidence gaps must be discovered or reconciled.
- An AI onboarding map or project-level evidence handoff is required.

Reject or hand off when:

- One concrete test file needs its field contract checked. Handoff: `physicsguard-test-file-contract-review`.
- The request is cross-project historical or database-ledger search. Handoff: `none`.

## Minimum workflow

1. Discover and reconcile the current project profile, artifacts, facts, and binding expectations.
2. Load the native route protocol and preserve required, critical, exempt, unknown, and unresolved rows explicitly.
3. Return the navigation map and gaps; send proof claims to their direct validation or closure owner.

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

- `reconciled_inventory`
- `binding_map`
- `critical_gaps`
- `closure_handoff`

Claim boundary: Registry closure covers only the exact current project evidence bundle and declared roles/bindings; unresolved critical gaps or out-of-scope files remain blocking.
