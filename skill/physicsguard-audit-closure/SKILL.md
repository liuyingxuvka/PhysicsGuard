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
2. Load the native route protocol and reconcile failures, skips, stale evidence, mappings, refinements, predictive conditions, and any supplied portable bundle identity or query gap.
3. Keep frozen bundle cases and current target-native execution as separate states; return one exact closure state and a claim that does not exceed current evidence.

Before executing a native command, verify the installed `physicsguard` version against `runtime-requirements.json`; a missing or mismatched runtime is a visible blocker with no fallback.

## Blueprint closure input

Consume a current whole or affected `PhysicalModelBlueprintReview` projection matching the requested claim. A supplied portable bundle is a frozen interpretation projection only: preserve its bundle/source identities, `observed_at_export_unlicensed`, compact or exact-one-selector query status, `portable_query_identity_only_terminal` gaps, frozen case result, and `execution_claim_licensed=false`. Report current native execution separately and never turn bundle presence, a frozen-case pass, or an AI answer into fresh evidence or closure. This route does not author or fully review the blueprint; missing, stale, ambiguous, unsupported, unresolved, or not-run evidence remains non-pass and cannot broaden to a repository scan or larger projection.

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
- `blueprint_scope_fingerprint`
- `blueprint_depth_and_first_gap`
- `portable_bundle_identity`
- `portable_query_status`
- `frozen_case_status`
- `current_execution_status`
- `execution_claim_licensed`
- `blockers`
- `next_actions`

Claim boundary: Closure proves only the exact requested audit scope represented by current native receipts; skipped, stale, partial, and predictive gaps remain non-pass.
