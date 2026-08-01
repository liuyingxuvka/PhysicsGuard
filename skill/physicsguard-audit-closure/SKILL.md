---
name: physicsguard-audit-closure
description: "Use directly before claiming a PhysicsGuard audit, localization, validation, reuse, or prediction result is complete; reconcile required native checks, blockers, stale or skipped evidence, mappings, refinements, holdout and rollout evidence, and the exact safe claim boundary."
---

# PhysicsGuard Audit Closure

## Entry boundary

Route: `route:physicsguard-audit-closure:close`; native owner: `physicsguard.audit-closure`; role: `independent direct route`. Read `references/route-capsule.json` to confirm this exact identity and the machine-checkable decision boundary.

Accept this route only when:

- The requested outcome is a final audit, localization, validation, reuse, handoff, or prediction-readiness claim.
- Current native results must be reconciled into passed, partial, downgraded, or blocked closure.

Reject or hand off when:

- Evidence is still being generated or the physical fault is still being localized. Handoff: `physicsguard-ai-debugging`.
- The request is only to build the project evidence map. Handoff: `physicsguard-project-evidence-registry`.

## Minimum workflow

1. Bind the exact requested claim and current native receipt inventory.
2. Load the native route protocol and reconcile failures, skips, stale evidence, mappings, refinements, and predictive conditions.
3. Return one exact closure state and a claim that does not exceed current evidence.

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

- `closure_status`
- `safe_claim`
- `blockers`
- `next_actions`

Claim boundary: Closure proves only the exact requested audit scope represented by current native receipts; skipped, stale, partial, and predictive gaps remain non-pass.
