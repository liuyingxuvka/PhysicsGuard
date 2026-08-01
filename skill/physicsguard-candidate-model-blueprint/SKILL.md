---
name: physicsguard-candidate-model-blueprint
description: "Use directly to turn a validated PhysicsGuard hierarchy into a bounded candidate model blueprint through an official target-model interface; require ready blocks, interfaces, mappings, model semantics, validation and rollout boundaries, without claiming recovered commercial-model equivalence."
---

# PhysicsGuard Candidate Model Blueprint

## Entry boundary

Route: `route:physicsguard-candidate-model-blueprint:build`; native owner: `physicsguard.candidate-model-blueprint`; role: `independent direct route`. Read `references/route-capsule.json` to confirm this exact identity and the machine-checkable decision boundary.

Accept this route only when:

- The user asks to build a candidate model from already validated PhysicsGuard evidence.
- Generation readiness, interfaces, or rollout boundaries must be decided before target-model creation.

Reject or hand off when:

- The hierarchy or external-model boundary is not yet understood. Handoff: `physicsguard-model-understanding-preflight`.
- The model still lacks current dataset validation evidence. Handoff: `physicsguard-model-dataset-validation`.

## Minimum workflow

1. Confirm the hierarchy, block, mapping, and interface readiness evidence.
2. Load the native route protocol and generate only through an official or user-owned interface.
3. Map outputs back to PhysicsGuard and accept only inside the checked validation and rollout boundary.

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

- `candidate_blueprint`
- `generation_eligibility`
- `rollout_boundary`
- `blockers`

Claim boundary: Generation eligibility covers only a candidate low-fidelity blueprint for the declared target and interfaces; it is not an implemented or validated high-fidelity model.
