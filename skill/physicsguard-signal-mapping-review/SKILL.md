---
name: physicsguard-signal-mapping-review
description: "Use directly when external signals or parameters are mapped into PhysicsGuard variables and target identity, units, conversion, revision, confidence, reviewer state, temporal depth, interval bounds, or stale conditions must be checked before residual claims."
---

# PhysicsGuard Signal Mapping Review

## Entry boundary

Accept this route only when:

- The task concerns external-signal or parameter mapping identity, unit, conversion, confidence, review, timing, or staleness.
- Mapping evidence must be resolved before residual, adequacy, or predictive checks can use it.

Reject or hand off when:

- A concrete many-field test file first needs a complete field contract. Handoff: `physicsguard-test-file-contract-review`.
- Mappings are current and the task is exact model/dataset validation. Handoff: `physicsguard-model-dataset-validation`.

## Minimum workflow

1. Bind every governed external object to its exact target, unit, conversion, revision, and evidence.
2. Load the native route protocol and check confidence, review, time coverage, intervals, and stale conditions.
3. Keep unresolved mappings visible and do not mutate observed values.

If `python -m physicsguard.cli --help` fails, install the engine once with `python -m pip install -e <PhysicsGuard checkout>`; there is no version gate.

## Conditional detail loading

- Load `references/native-route-protocol.md` after route selection when domain execution needs the detailed workflow.
- Do not load another PhysicsGuard skill's references merely because the skills are related; hand off to that skill instead.

## Hard gates

- Keep non-pass states and unknowns visible.
- AI narration, inventories and template previews are not evidence; only PhysicsGuard command output is.
- Keep pointwise consistency distinct from stateful prediction and keep every claim inside the exact checked boundary.

## Required outputs

- `mapping_status`
- `review_gaps`
- `temporal_boundary`
- `safe_mapping_claim`

Claim boundary: A mapping pass licenses only the exact external signal, target variable, conversion, revision, temporal range, and reviewed confidence in the receipt.
