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

## Blueprint slice

If no blueprint is supplied or project-declared and the request is ordinary bounded native work, run the native owner directly; report blueprint_not_provided and the unexamined scope, without a blueprint PASS. If a blueprint is supplied, project-declared, or needed for a target/whole-boundary claim, require the exact current review/projection below. Missing, stale, foreign, ambiguous, or unknown-seed identity blocks that selected path; never downgrade it to bypass the requirement.

For this selected blueprint path: Consume the affected slice for the concrete file/dataset/testbench path. Bind deterministic files and fields to exact blueprint input/output/state/effect ports, physical obligations, expected evidence, units, frames, and time semantics. The contract does not author or qualify the full blueprint. A missing, stale, foreign, or ambiguous slice blocks the selected blueprint path without broadening to all fields, all models, or the full blueprint.

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
- `blueprint_interface_bindings_when_present`
- `affected_slice_fingerprint_when_present`
- `mapping_gaps`
- `safe_analysis_boundary`

Claim boundary: A pass covers only the exact test files, fields, units, timing, model/testbench versions, signal mappings, and depth represented in the receipt.
