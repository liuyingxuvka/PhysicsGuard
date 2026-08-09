---
name: physicsguard-test-file-contract-review
description: "Use directly when concrete testbench or test-data files require deterministic file/field identity, units, timing, testbench version, parameter roles, mapping evidence, model binding, temporal depth, and project-gap coverage before AI analysis or validation."
---

# PhysicsGuard Test File Contract Review

## Entry boundary

Route: `route:physicsguard-test-file-contract-review:check`; native owner: `physicsguard.test-file-contract-review`; role: `independent direct route`. Read `references/route-capsule.json` to confirm this exact identity and the machine-checkable decision boundary.

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

Before executing a native command, verify the installed `physicsguard` version against `runtime-requirements.json`; a missing or mismatched runtime is a visible blocker with no fallback.

## Blueprint slice

Consume the affected slice for the concrete file/dataset/testbench path. Bind deterministic files and fields to exact blueprint input/output/state/effect ports, physical obligations, expected evidence, units, frames, and time semantics. The contract does not author or qualify the full blueprint. A missing, stale, foreign, or ambiguous slice blocks without broadening to all fields, all models, or the full blueprint.

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

- `contract_status`
- `field_dispositions`
- `blueprint_interface_bindings`
- `affected_slice_fingerprint`
- `mapping_gaps`
- `safe_analysis_boundary`

Claim boundary: A pass covers only the exact test files, fields, units, timing, model/testbench versions, signal mappings, and depth represented in the receipt.
