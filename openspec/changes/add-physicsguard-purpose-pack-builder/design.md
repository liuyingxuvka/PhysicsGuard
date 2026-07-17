## Context

PhysicsGuard already owns reviewed low-fidelity starter assets and a large generator that materializes hierarchical examples and regression tests. That generator is the sole owner of its physical content, assumptions, refinement rules, and write paths. The missing behavior is a target-native way to choose a reviewed purpose pack before an AI starts new work, account for every candidate, compose only safe fragments, and bind the generated work package to current PhysicsGuard validation.

The repository has ten peer-modified `SKILL.md` files. This change must remain isolated from them, from the existing generator, and from existing templates. OpenSpec is an external provider and is not modified. The project-level FlowGuard adoption record is older than the installed 0.57.0 runtime; its read-only upgrade preview is currently blocked by a missing canonical suite map, so this change can provide current model evidence only for its own new boundary and cannot claim repository-wide FlowGuard adoption closure.

## Goals / Non-Goals

**Goals:**

- Publish one PhysicsGuard-owned manifest with stable content identities and native route/check bindings.
- Deterministically resolve zero, one, or many eligible templates without lexical guessing.
- Permit composition only with explicit compatibility, satisfied dependencies, canonical order, and one field owner.
- Produce separate immutable selection and instance identities.
- Validate the manifest, decision, generated artifact, unresolved placeholders, and PhysicsGuard safety boundary with target-owned validators.
- Keep known-good and known-bad behavior executable in focused fixtures and tests.

**Non-Goals:**

- Do not create, infer, or validate real physical equations from route names or template names.
- Do not modify or replace the expanded starter-pack generator or any existing template.
- Do not make template rendering equivalent to optimizer convergence, `audit_pass`, model validity, dataset validity, installation parity, or release readiness.
- Do not create a second SkillGuard runtime authority or a central copy of PhysicsGuard domain semantics.

## Decisions

### 1. Add an isolated target-owned adapter

Add `physicsguard.template_packs` as a small selection/receipt adapter. It consumes a new manifest but references existing reviewed assets by portable repository-relative paths. It does not import or call the old materializer and therefore cannot acquire its physical-content or filesystem-write ownership.

This is preferred over extending the large generator because selection and receipt semantics are independent from domain asset generation. It is preferred over a new global template service because PhysicsGuard must remain the semantic owner.

### 2. Make the manifest content-addressed

The YAML manifest declares a catalog id/revision/digest, one optional approved base id, and templates with their own revisions/digests, family, native routes, hard applicability rules, required/provided fragments, field ownership, compatibility/conflicts/dominance, parameter schema, generated artifact surfaces, builder id, validator ids, body, and claim boundary.

Digests are computed from canonical JSON projections with the digest field omitted. Unknown or structurally invalid fields, stale digests, duplicate ids, missing native bindings, and unresolved referenced ids fail closed.

### 3. Use a finite decision algorithm

The native family and route are supplied by the caller before catalog evaluation. Every non-base manifest candidate is accounted for exactly once as eligible or rejected with a deterministic reason.

- Zero eligible domain templates selects the declared validated base and records no-match/harvest-required, or blocks if there is no base.
- One eligible template becomes `single_selected`.
- Several templates become `strictly_dominated_selection` only when one target-authored candidate explicitly dominates all others.
- Otherwise, several templates become `composed` only when dependencies are satisfied, every pair is explicitly compatible, conflicts are absent, and every generated field/artifact surface has exactly one owner.
- All unresolved cases become `ambiguous_template_selection` and cannot instantiate.

Template id order is used only to make output canonical; it never resolves ambiguity.

### 4. Keep selection and instantiation separate

The selection receipt fingerprint binds the request fingerprint, native route, catalog identity, complete candidate accounting, selected identities, composition order, field-owner map, disposition, and reasons.

Instantiation resolves declared input/parameter placeholders into one canonical artifact, rejects undeclared or missing parameters, scans recursively for unresolved placeholders, and calculates artifact and instance fingerprints. The instance fingerprint binds the selection fingerprint, exact parameters, builder id, artifact identity, validator ids, and validation result.

### 5. PhysicsGuard validators retain the claim boundary

Native validators check manifest currentness, decision completeness, allowed terminal behavior, field-owner parity, placeholder closure, and required PhysicsGuard guardrails (`si_units_required`, explicit assumptions, native validation, and a non-empty claim boundary). These are structural workflow checks. They do not judge physical truth, recover a commercial model, validate datasets, or produce `audit_pass`.

### 6. Negative semantics stay in test fixtures

Production manifests contain only real PhysicsGuard purpose packs. Ambiguous, colliding, no-base, stale-digest, and unresolved-placeholder variants live under the new focused fixture directory and are sealed or intentionally corrupted by the fixture harness. This prevents failure-only template ids from becoming production candidates.

### 7. Project a target-owned neutral SkillGuard handoff

`physicsguard.skillguard_template_adapter` calls the current native manifest validator and selector first, then projects the complete catalog and applicability rows into `skillguard.target_template_projection.v1`. The projection is intentionally unsealed: SkillGuard may apply neutral canonical identities, but it cannot invent a PhysicsGuard route, candidate, predicate, builder, validator, or safe claim. Native catalog, builder, validator, body, and artifact identities remain explicit content inputs, and central selection must reproduce the native zero/one/many or strict-dominance outcome.

## Risks / Trade-offs

- **[Risk] A broad base pack hides a missing domain template** → The base terminal records exact no-match evidence and `harvest_required`; high-risk callers may provide a manifest without a base to force a block.
- **[Risk] Composition creates inconsistent work packages** → Require explicit pairwise compatibility, fragment dependencies, one-owner maps, and a materialized preview before native validation.
- **[Risk] Content-addressed manifests are awkward to edit** → Expose deterministic digest helpers and test byte-stable reloading.
- **[Risk] Structural validation is mistaken for physical validation** → Preserve explicit claim boundaries in every template, receipt, validator result, and test expectation.
- **[Risk] The stale project adoption record overstates confidence** → Keep it as a visible blocker and scope evidence to this new model/module/test boundary.

## Migration Plan

1. Freeze this OpenSpec change and its existing-owner preflight.
2. Add the manifest, adapter, fixtures, and tests as new paths only.
3. Run the risk-intent model against correct and broken selection behavior.
4. Run focused tests, import/compile checks, and OpenSpec status; fix only this change's failures.
5. Hand the isolated result to the parent integration owner. Repository-wide FlowGuard/SkillGuard adoption, skill prompt edits, installation, commit, and push remain outside this subtask.

Rollback is deletion of the new untracked paths before integration. Existing starter assets and peer-modified skills are unchanged.

## Open Questions

- Which SkillGuard compiler fragment identity will eventually consume the target manifest after the shared executable-runtime owner hands off?
- Which installed PhysicsGuard skill should expose this adapter first once the ten peer-modified entrypoints are reconciled?
