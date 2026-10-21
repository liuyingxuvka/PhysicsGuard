---
name: physicsguard-test-file-contract-review
description: "Use directly when concrete testbench or test-data files require deterministic file/field identity, units, timing, testbench version, parameter roles, mapping evidence, model binding, temporal depth, and project-gap coverage before AI analysis or validation."
---

# PhysicsGuard Test File Contract Review

## Entry boundary

Accept this route only when:

- One or more concrete testbench, test-data, log, sensor, command, measurement, calibration, or fixture files are in scope.
- File and field contracts must pass before broad AI analysis or dataset validation.

Reject or hand off when:

- No concrete test-data file is in scope. Handoff: `physicsguard-model-understanding-preflight`.
- Current file contracts pass and model/dataset consistency is now the request. Handoff: `physicsguard-model-dataset-validation`.

## Minimum workflow

1. Generate deterministic file and field identity before AI mapping judgment.
2. Load the native route protocol and reconcile every field, role, unit, timing, mapping, and model binding.
3. Block broad analysis until the exact contract passes; hand validation to the dataset route afterward.

If `python -m physicsguard.cli --help` fails, install the engine once with `python -m pip install -e <PhysicsGuard checkout>`; there is no version gate.

## Conditional detail loading

- Load `references/native-route-protocol.md` after route selection when domain execution needs the detailed workflow.
- Do not load another PhysicsGuard skill's references merely because the skills are related; hand off to that skill instead.

## Hard gates

- Keep non-pass states and unknowns visible.
- AI narration, inventories and template previews are not evidence; only PhysicsGuard command output is.
- Keep pointwise consistency distinct from stateful prediction and keep every claim inside the exact checked boundary.

## Required outputs

- `contract_status`
- `field_dispositions`
- `mapping_gaps`
- `safe_analysis_boundary`

Claim boundary: A pass covers only the exact test files, fields, units, timing, model/testbench versions, signal mappings, and depth represented in the receipt.
