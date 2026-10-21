---
name: physicsguard-candidate-model-blueprint
description: "Use directly for initial target inventory or a bounded candidate blueprint draft with explicit evidence gaps, and as the sole full blueprint reviewer. Current native validation and checked rollout boundaries are required for target-model generation eligibility; a draft never claims recovered commercial-model equivalence."
---

# PhysicsGuard Candidate Model Blueprint

## Entry boundary

Accept this route only when:

- The user asks for initial target inventory or a candidate blueprint draft, including explicit evidence gaps.
- The user requests full blueprint review or target-model generation eligibility from current validated PhysicsGuard evidence.

Reject or hand off when:

- Understanding or validation work is requested as its own task, rather than drafting or reviewing the blueprint. Handoff: `physicsguard-model-understanding-preflight`.
- Dataset validation evidence must be produced before a generation-eligibility claim. Handoff: `physicsguard-model-dataset-validation`.

## Minimum workflow

1. For an initial draft, inventory the authoring target and available evidence, keep missing inventory/validation as explicit gaps, and return the bounded draft without claiming eligibility. For full review or generation, bind an independently inventoried target and resolve `blueprint_directory` versus `explicit_material_root`.
2. When review is requested, run the canonical review with `--material-root ROOT` only for `explicit_material_root`; preserve all hierarchy, interface, physical-semantics and exact native binding requirements. Missing evidence remains non-pass.
3. For FMI targets, use the provider-neutral `physicsguard.fmi-observation-request.v1` contract and its restricted source-independent oracle; keep caller expectations, native outputs, and oracle results distinct.
4. Use the full projection only for authoring or a whole-boundary review. Keep the native blueprint directory, tests, and bindings as DNA; on explicit request, compose only an in-memory projection or one selector while preserving every identity-only and execution-licensing gap.
5. Only after current native validation establishes generation eligibility, generate a target-model candidate through an official or user-owned interface, map outputs back to PhysicsGuard, and accept only inside the checked validation and rollout boundary.

If `python -m physicsguard.cli --help` fails, install the engine once with `python -m pip install -e <PhysicsGuard checkout>`; there is no version gate.

## Blueprint ownership and loading

This is the sole PhysicsGuard route that authors or fully reviews `PhysicalModelBlueprint`. Initial inventory/draft authoring may start from available evidence and return explicit gaps; it grants no generation eligibility, validated status, strict revision, or closure. Full review and target-model generation eligibility still require their current independent inventory and native validation evidence. Resolve `artifact_root` before review: `blueprint_directory` binds local `repo_path` values below the blueprint directory, while `explicit_material_root` requires the caller-selected `--material-root` and never triggers discovery, download, or repository fallback. Without that material, return the concise `external_resource_not_run` boundary and `native_execution_status=not_run`. The blueprint directory, its tests, and its model/code/evidence bindings are the target DNA. A compact projection may be composed in memory for one requested `module`, `element`, `case`, `impact`, or `reverse` selector; the retired disk bundle route remains visibly blocked. When qualification is requested, run the canonical review with `python -m physicsguard.cli blueprint review BLUEPRINT --target-authority AUTHORITY --pretty`.

## Conditional detail loading

- Load `references/native-route-protocol.md` after route selection when domain execution needs the detailed workflow.
- Do not load another PhysicsGuard skill's references merely because the skills are related. Use an explicit typed handoff.

## Hard gates

- Preserve the target's native judgment, exact evidence identities, explicit unknowns, and non-pass states.
- Never treat AI self-report, prose completeness, progress, an inventory, or a template preview as native execution evidence.
- Keep pointwise consistency distinct from stateful prediction and keep every claim inside the exact checked boundary.
- Do not add a compatibility route, alias, fallback, copied runtime, or alternate success owner.

## Required outputs

- `candidate_blueprint`
- `physical_blueprint_review_if_requested`
- `blueprint_fingerprint_when_present`
- `material_root_disposition`
- `native_execution_status`
- `deepest_licensed_layer`
- `first_gap`
- `safe_claim`
- `native_directory_dna_status`
- `in_memory_query_identity_and_gaps_if_requested`
- `execution_claim_licensed`
- `generation_eligibility`
- `rollout_boundary`
- `blockers`

Claim boundary: Generation eligibility covers only a candidate low-fidelity blueprint for the declared target and interfaces; it is not an implemented or validated high-fidelity model.
