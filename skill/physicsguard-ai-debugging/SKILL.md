---
name: physicsguard-ai-debugging
description: "Use for AI-guided debugging of engineering-simulation results: low-fidelity residual audits with hierarchy evaluate, coarse-to-fine localization of the suspicious block, competing hypotheses and the next signal to request, and candidate-model generation from a validated hierarchy. For a test-data file contract or model-vs-dataset validation alone, use the direct skill instead."
---

# PhysicsGuard AI Debugging

## Entry boundary

Accept this route when:

- An engineering-simulation result looks wrong and the fault must be localized: residual audit, coarse-to-fine refinement, competing hypotheses, next signals.
- A candidate low-fidelity model must be built from a validated hierarchy (Workflow B in the native route protocol).

Reject or hand off when:

- External-model boundary and inventory understanding is the whole request. Handoff: `physicsguard-model-understanding-preflight`.
- Signal identity, units, conversion, confidence, or temporal mapping is the whole request. Handoff: `physicsguard-signal-mapping-review`.
- A concrete test-data file contract is the whole request. Handoff: `physicsguard-test-file-contract-review`.
- Exact model/dataset validation is the whole request. Handoff: `physicsguard-model-dataset-validation`.

## Minimum workflow

1. If one hand-off listed above owns the complete request, hand off and stop.
2. Write or review the model-understanding preflight.
3. Map the external signals into an observed snapshot; review the intake when mappings are uncertain.
4. Run `python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml`.
5. Read `top_blocks`, `recommended_refinements` and the mapping issues; request the next small set of signals and refine one block. Repeat.

If `python -m physicsguard.cli --help` fails, install the engine once with `python -m pip install -e <PhysicsGuard checkout>`; there is no version gate.

## Conditional detail loading

- Load `references/native-route-protocol.md` after route selection when domain execution needs the detailed workflow.
- Do not load another PhysicsGuard skill's references merely because the skills are related; hand off to that skill instead.

## Hard gates

- Keep non-pass states and unknowns visible.
- AI narration, inventories and template previews are not evidence; only PhysicsGuard command output is.
- Keep pointwise consistency distinct from stateful prediction and keep every claim inside the exact checked boundary.

## Required outputs

- `localized_findings`
- `next_required_evidence`
- `bounded_claim`

Claim boundary: This route can license only a low-fidelity, evidence-bounded fault localization. It does not prove high-fidelity model truth or behavior outside the checked operating envelope.
