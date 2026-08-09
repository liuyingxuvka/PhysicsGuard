---
name: physicsguard-project-adoption
description: "Use directly to audit, adopt, or upgrade a target repository's PhysicsGuard workflow records and current toolchain/artifact identity before non-trivial PhysicsGuard work; adoption is workflow evidence only, not physical validation or closure."
---

# PhysicsGuard Project Adoption

## Entry boundary

Route: `route:physicsguard-project-adoption:audit`; native owner: `physicsguard.project-adoption`; role: `independent direct route`. Read `references/route-capsule.json` to confirm this exact identity and the machine-checkable decision boundary.

Accept this route only when:

- The task is to check, create, or upgrade PhysicsGuard repository adoption records.
- Current toolchain, artifact inventory, blockers, or affected revalidation must be established.

Reject or hand off when:

- The project is adopted and the task is to map its files and evidence gaps. Handoff: `physicsguard-project-evidence-registry`.
- The user asks whether a model result is validated or complete. Handoff: `physicsguard-audit-closure`.

## Minimum workflow

1. Run the read-only project audit first and compare current runtime and repository records.
2. Load the native route protocol; adopt or upgrade only when authorized and necessary.
3. Report workflow readiness separately from physical execution, validation, installation, and release.

Before executing a native command, verify the installed `physicsguard` version against `runtime-requirements.json`; a missing or mismatched runtime is a visible blocker with no fallback.

## Blueprint adoption record

Record the current blueprint identity when one exists: canonical path, blueprint/review fingerprint, target revision and scope, artifact-root meaning, native authority identities, and whether the available projection is summary, affected, or full. This route does not author or fully review the blueprint. Adoption never derives completeness or physical truth. A missing or stale blueprint is reported as an adoption gap; this route does not create an alternate blueprint or silently scan the repository.

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

- `adoption_status`
- `toolchain_status`
- `blueprint_identity`
- `adoption_boundary`
- `blockers`
- `required_revalidation`

Claim boundary: Adoption proves only current workflow records and toolchain/artifact readiness; it never substitutes for model execution, validation, closure, installation, or release evidence.
