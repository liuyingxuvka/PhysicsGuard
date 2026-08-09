---
name: physicsguard-model-understanding-preflight
description: "Use directly before a non-trivial external-model audit to capture the visible symptom, physical boundary, subsystem, signal, parameter, unit, assumption, access, model-semantics, and stop-condition universe; preflight is planning evidence, not residual validation."
---

# PhysicsGuard Model Understanding Preflight

## Entry boundary

Route: `route:physicsguard-model-understanding-preflight:review`; native owner: `physicsguard.model-understanding-preflight`; role: `independent direct route`. Read `references/route-capsule.json` to confirm this exact identity and the machine-checkable decision boundary.

Accept this route only when:

- A non-trivial external model must be understood before residual interpretation or blueprint work.
- The physical boundary, inventory, assumptions, access gaps, semantics, or stop conditions need a current review.

Reject or hand off when:

- The request is only to resolve signal identity, unit, conversion, or confidence. Handoff: `physicsguard-signal-mapping-review`.
- A concrete test-data file needs field-level coverage first. Handoff: `physicsguard-test-file-contract-review`.

## Minimum workflow

1. Freeze the symptom, external authority, physical boundary, and required inventory.
2. Load the native route protocol and review subsystems, signals, parameters, assumptions, uncertainty, and prediction access.
3. Proceed only inside the passed planning boundary; send unresolved mappings or files to their direct owners.

Before executing a native command, verify the installed `physicsguard` version against `runtime-requirements.json`; a missing or mismatched runtime is a visible blocker with no fallback.

## Blueprint slice

Establish the exact target identity, boundary fingerprint, independent inventory source, provider capabilities, and the first useful understanding layer. Consume only the current summary for ordinary preflight or the affected slice for a named boundary/inventory gap. This route does not author or fully review the blueprint; hand that work to `physicsguard-candidate-model-blueprint`. Missing or stale projection identity blocks without a full-scan fallback.

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

- `preflight_status`
- `understanding_record`
- `blueprint_summary_inputs`
- `first_useful_layer`
- `access_gaps`
- `next_route`

Claim boundary: Preflight licenses only that the declared low-fidelity audit boundary is sufficiently understood to proceed; unresolved access or inventory gaps remain visible blockers.
