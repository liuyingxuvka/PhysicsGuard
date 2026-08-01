---
name: physicsguard-ai-debugging
description: "Use only for mixed or unclear AI-guided engineering-simulation debugging that genuinely spans multiple specialized PhysicsGuard routes, including coarse-to-fine localization and candidate-model coordination. For a clear adoption, preflight, mapping, test-file, dataset-validation, library, evidence-registry, blueprint, or closure request, use that direct skill instead."
---

# PhysicsGuard AI Debugging

## Entry boundary

Route: `route:physicsguard-ai-debugging:audit`; native owner: `physicsguard.ai-debugging`; role: `mixed/unclear coordinator`. Read `references/route-capsule.json` to confirm this exact identity and the machine-checkable decision boundary.

Accept this route only when:

- The visible engineering fault spans several PhysicsGuard responsibilities and cannot be owned by one direct route.
- The correct PhysicsGuard route remains genuinely ambiguous after comparing the ten route capsules.
- Coarse-to-fine localization requires typed handoffs among preflight, mapping, validation, and closure owners.

Reject or hand off when:

- Repository adoption or upgrade is the whole request. Handoff: `physicsguard-project-adoption`.
- External-model boundary and inventory understanding is the whole request. Handoff: `physicsguard-model-understanding-preflight`.
- Signal identity, units, conversion, confidence, or temporal mapping is the whole request. Handoff: `physicsguard-signal-mapping-review`.
- A concrete test-data file contract is the whole request. Handoff: `physicsguard-test-file-contract-review`.
- Exact model/dataset validation is the whole request. Handoff: `physicsguard-model-dataset-validation`.
- Project evidence inventory and binding gaps are the whole request. Handoff: `physicsguard-project-evidence-registry`.
- Reusable model asset compatibility is the whole request. Handoff: `physicsguard-model-library`.
- Candidate blueprint generation is the whole request. Handoff: `physicsguard-candidate-model-blueprint`.
- Audit completion or localization closure is the whole request. Handoff: `physicsguard-audit-closure`.

## Minimum workflow

1. Confirm that no single direct capsule owns the complete request; otherwise hand off and stop this composite route.
2. Verify the current PhysicsGuard runtime, then load the native route protocol only for the selected debugging work.
3. Keep every specialist's native judgment and evidence separate while coordinating the smallest necessary handoff chain.
4. Close only through the direct native owner that owns the requested final claim.

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

- `selected_native_routes`
- `localized_findings`
- `next_required_evidence`
- `bounded_claim`

Claim boundary: This route can license only a low-fidelity, evidence-bounded fault localization. It does not prove high-fidelity model truth or behavior outside the checked operating envelope.
