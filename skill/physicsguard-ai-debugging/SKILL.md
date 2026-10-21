---
name: physicsguard-ai-debugging
description: "Use only for mixed or unclear AI-guided engineering-simulation debugging that genuinely spans multiple specialized PhysicsGuard routes, including coarse-to-fine localization and candidate-model coordination. For a clear adoption, preflight, mapping, test-file, dataset-validation, library, evidence-registry, blueprint, or closure request, use that direct skill instead."
---

# PhysicsGuard AI Debugging

## Entry boundary

Accept this route only when:

- The visible engineering fault spans several PhysicsGuard responsibilities and cannot be owned by one direct route.
- The correct PhysicsGuard route remains ambiguous after reading the hand-off list below.
- Coarse-to-fine localization requires typed handoffs among preflight, mapping, validation, and closure owners.

Reject or hand off when:

- External-model boundary and inventory understanding is the whole request. Handoff: `physicsguard-model-understanding-preflight`.
- Signal identity, units, conversion, confidence, or temporal mapping is the whole request. Handoff: `physicsguard-signal-mapping-review`.
- A concrete test-data file contract is the whole request. Handoff: `physicsguard-test-file-contract-review`.
- Exact model/dataset validation is the whole request. Handoff: `physicsguard-model-dataset-validation`.
- Reusable model asset compatibility is the whole request. Handoff: `physicsguard-model-library`.
- Candidate blueprint generation is the whole request. Handoff: `physicsguard-candidate-model-blueprint`.

## Minimum workflow

1. If one hand-off listed above owns the complete request, hand off and stop.
2. Verify the current PhysicsGuard runtime, then load the native route protocol only for the selected debugging work.
3. Keep every specialist's native judgment and evidence separate while coordinating the smallest necessary handoff chain.
4. Close only through the direct native owner that owns the requested final claim.

If `python -m physicsguard.cli --help` fails, install the engine once with `python -m pip install -e <PhysicsGuard checkout>`; there is no version gate.

## Conditional detail loading

- Load `references/native-route-protocol.md` after route selection when domain execution needs the detailed workflow.
- Do not load another PhysicsGuard skill's references merely because the skills are related; hand off to that skill instead.

## Hard gates

- Keep non-pass states and unknowns visible.
- AI narration, inventories and template previews are not evidence; only PhysicsGuard command output is.
- Keep pointwise consistency distinct from stateful prediction and keep every claim inside the exact checked boundary.

## Required outputs

- `selected_native_routes`
- `localized_findings`
- `next_required_evidence`
- `bounded_claim`

Claim boundary: This route can license only a low-fidelity, evidence-bounded fault localization. It does not prove high-fidelity model truth or behavior outside the checked operating envelope.
