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

1. Bind one independently inventoried target, resolve `blueprint_directory` versus `explicit_material_root`, and author or load its canonical `PhysicalModelBlueprint`.
2. Run the canonical review with `--material-root ROOT` only when the blueprint declares `explicit_material_root`; reconcile hierarchy/refinement, typed interfaces/state/effects, independent physical semantics, and exact native model/code/test/resource/oracle bindings.
3. For FMI targets, use the provider-neutral `physicsguard.fmi-observation-request.v1` contract and its restricted source-independent oracle; keep caller expectations, native outputs, and oracle results distinct.
4. Use the full projection only for authoring or a whole-boundary review. Keep the native blueprint directory, tests, and bindings as DNA; on explicit request, compose only an in-memory projection or one selector while preserving every identity-only and execution-licensing gap.
5. Generate a target-model candidate only through an official or user-owned interface, map outputs back to PhysicsGuard, and accept only inside the checked validation and rollout boundary.

Before executing a native command, verify the installed `physicsguard` version against `runtime-requirements.json`; a missing or mismatched runtime is a visible blocker with no fallback.

## Blueprint ownership and loading

This is the sole PhysicsGuard route that authors or fully reviews `PhysicalModelBlueprint`. Resolve `artifact_root` before review: `blueprint_directory` binds local `repo_path` values below the blueprint directory, while `explicit_material_root` requires the caller-selected `--material-root` and never triggers discovery, download, or repository fallback. Without that material, return the concise `external_resource_not_run` boundary and `native_execution_status=not_run`. The blueprint directory, its tests, and its model/code/evidence bindings are the target DNA. A compact projection may be composed in memory for one requested `module`, `element`, `case`, `impact`, or `reverse` selector; the retired disk bundle route remains visibly blocked. Run the canonical review with `python -m physicsguard.cli blueprint review BLUEPRINT --target-authority AUTHORITY --pretty`.

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
- `physical_blueprint_review`
- `blueprint_fingerprint`
- `material_root_disposition`
- `native_execution_status`
- `deepest_licensed_layer`
- `first_gap`
- `safe_claim`
- `native_directory_dna_status`
- `in_memory_query_identity_and_gaps`
- `execution_claim_licensed`
- `generation_eligibility`
- `rollout_boundary`
- `blockers`

Claim boundary: Generation eligibility covers only a candidate low-fidelity blueprint for the declared target and interfaces; it is not an implemented or validated high-fidelity model.
