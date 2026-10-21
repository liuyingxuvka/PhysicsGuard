---
name: physicsguard-model-library
description: "Use directly to index or select reusable PhysicsGuard model assets and check profile, testbench, validation-receipt, known-limit, gap, predictive-horizon, and bounded-reuse compatibility without storing raw datasets or implying universal validity."
---

# PhysicsGuard Model Library

## Entry boundary

Accept this route only when:

- The task is to index validated model assets or decide whether one is reusable for a named target context.
- Asset, profile, testbench, validation, gap, or predictive-horizon compatibility must be checked.

Reject or hand off when:

- The asset has no current model/dataset validation receipt. Handoff: `physicsguard-model-dataset-validation`.
- The request is a cross-project database or historical-ledger query. Handoff: `none`.

## Minimum workflow

1. Bind the selected asset and exact target profile/testbench context.
2. Load the native route protocol and check current compatibility, validation, gaps, and known limits.
3. Report only the exact reusable boundary; keep database-level discovery out of scope.

If `python -m physicsguard.cli --help` fails, install the engine once with `python -m pip install -e <PhysicsGuard checkout>`; there is no version gate.

## Conditional detail loading

- Load `references/native-route-protocol.md` after route selection when domain execution needs the detailed workflow.
- Do not load another PhysicsGuard skill's references merely because the skills are related; hand off to that skill instead.

## Hard gates

- Keep non-pass states and unknowns visible.
- AI narration, inventories and template previews are not evidence; only PhysicsGuard command output is.
- Keep pointwise consistency distinct from stateful prediction and keep every claim inside the exact checked boundary.

## Required outputs

- `compatible_assets`
- `reuse_status`
- `verified_reuse_limits`
- `gaps`
- `bounded_reuse_scope`

Claim boundary: Library readiness licenses only the selected asset/profile/testbench combination and exact bounded reuse scope; it does not validate a new project automatically.
