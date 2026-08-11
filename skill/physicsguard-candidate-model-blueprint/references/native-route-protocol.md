# PhysicsGuard Candidate Model Blueprint

Use this route when the user asks to build a candidate model from PhysicsGuard evidence.

## Canonical physical DNA

This route alone authors or fully reviews `PhysicalModelBlueprint`. First read its `artifact_root`:

- `blueprint_directory`: resolve every local `repo_path` below the blueprint directory.
- `explicit_material_root`: require one caller-selected material root and pass it as `--material-root ROOT`. Do not search the repository, download missing bytes, infer another root, or silently reuse the blueprint directory.

For a `blueprint_directory` target, run exactly:

```powershell
python -m physicsguard.cli blueprint review BLUEPRINT --target-authority AUTHORITY --pretty
```

For an `explicit_material_root` target, run exactly:

```powershell
python -m physicsguard.cli blueprint review BLUEPRINT --target-authority AUTHORITY --material-root ROOT --pretty
```

If the explicit material is not supplied, keep the review concise: report `material_root_disposition=missing`, `native_execution_status=not_run`, first gap `external_resource_not_run`, and the review's safe claim. Do not print the full blueprint merely because target bytes are unavailable.

The independently produced inventory, target/provider fingerprints, one-root hierarchy, exact parent+1 depth, typed inputs/outputs/state/effects, independent equations or constraints, compositional refinements, and native model/code/test/dataset/resource/oracle/evidence bindings must all remain explicit. Record `PhysicalModelBlueprintReview`, blueprint/review fingerprints, governed denominator, deepest licensed layer, first gap, external-identity-only bindings, and safe claim. Parsing, a template, or caller prose never supplies readiness.

Load summary for ordinary route decisions, the affected projection for a named change, and full only for authoring, complete review, or a whole-boundary claim. A projection is an in-memory view over the native directory, never an interchange package. Every projection must match the current target revision, blueprint/review/relation-set/recipe fingerprints. Missing or stale projection is a blocker, never permission for a source scan or alternate reviewer.

The sole qualification entry remains the canonical `blueprint review` command, with `--material-root ROOT` only for an explicit-material blueprint. After loading that same blueprint and deriving its matching review, use the exported `physicsguard.summary_physical_blueprint_projection`, `physicsguard.affected_physical_blueprint_projection`, `physicsguard.reverse_trace_physical_blueprint_projection`, or `physicsguard.full_physical_blueprint_projection` function for the requested read shape. Affected and reverse queries must receive `target_inventory_authority=authority`, `blueprint_base_dir=material_root_or_blueprint_root`, and `authority_base_dir=authority_root`; they rerun the canonical reviewer exactly once and admit the supplied review only when it equals that exact-current passing result field-for-field before graph compilation. These functions are read-only projections and never create, repair, or replace review authority.

## Generic FMI observation

When the target is an FMI exchange package, use the provider-neutral `physicsguard.fmi-observation-request.v1` request. Freeze the source identity, content-addressed artifacts and archive members, FMI version, `model_exchange` interface, model name/identifier, variable contract, behavior cases, and request fingerprint. The currently supported case operations are `read_after_initialization`, `event_update`, and `rejected_set`.

Every behavior case binds a restricted source-independent oracle. Keep three values separate: the caller's frozen expectation, the value returned by native FMI execution, and the value derived by the restricted oracle. The oracle may use only its declared finite inputs, source-member identities, and supported restricted expressions; the implementation under test cannot be its own oracle. A passing observation verifies the frozen package/interface/case contract only. It does not authenticate the publisher, prove the equations are physically true, or establish high-fidelity equivalence.

## In-memory projection boundary

Compose only a bounded in-memory projection when the user or downstream workflow requests one. The native directory stays authoritative and no standalone bundle is written. The public `blueprint bundle-export` and `blueprint bundle-query` routes remain visibly blocked; use the native `blueprint review` command and the owning process's read-only projection functions instead. Do not serialize a full directory into an AI prompt, invent a second summary, or create a transport artifact that competes with the native directory.

Every in-memory projection reports the native directory fingerprint, target system id, subject revision, source fingerprints, review status, deepest licensed layer, coverage counts, first gap, safe claim, claim boundary, and the selected query kind/id when present. A projection never proves current execution and always keeps `execution_claim_licensed=false`. Preserve identity-only gaps when a content-addressed source/test/resource is identified but its bytes are not available to the current owner.

## Workflow

1. Start from a passed model-understanding preflight and an independent target inventory.
2. Use validated low-fidelity hierarchy blocks, interfaces, units, assumptions, and examples.
3. Resolve the declared artifact root. For FMI material, validate the generic request and its restricted independent oracle before using native outputs.
4. Generate candidate model artifacts only through official APIs, documented exchange formats, or user-owned editable templates.
5. Run the candidate model and map outputs back into PhysicsGuard observed values. An in-memory projection is not this current execution.
6. Use residuals, quantitative adequacy, and closure to decide whether the
   blueprint is good enough or needs refinement. Do not validate only a small
   convenient subset when the claim covers a larger time/signal/parameter
   universe. Source-classify every parameter as static or time-varying, and
   require each time-varying parameter's own adequate history.
7. Declare whether the candidate is `pointwise` or `stateful_dynamic`.
   Pointwise relations cannot support simulation or prediction claims. For a
   stateful predictive claim, execute the candidate through the official
   target interface, preserve the initial state, step size, horizon, producer
   receipt, and exact trajectory identity, and validate it against a disjoint
   future holdout with the native predictive-rollout gate.
8. Keep the base task model and candidate model as separate content-addressed
   artifacts. Record the triggering hypothesis mismatch and the exact
   regression and holdout inventory. A stateful candidate additionally
   consumes the existing native predictive-rollout receipt:

   ```powershell
   python -m physicsguard.cli task-model revision CANDIDATE_REVISION.yaml --pretty
   ```

9. If a bounded projection is requested, compose it only from the exact current review, return compact status or one selector, and retain every source/query identity and gap in memory.
10. Accept the candidate only when every declared check passes. Reject an
   unapplied failed candidate. If an applied candidate fails, roll back only to
   the exact still-current base identity. Never overwrite or delete v1 during
   candidate evaluation.

A candidate model is a new engineering artifact, not a recovered commercial-model copy.
Even a passing predictive rollout is bounded to its checked horizon, signals,
thresholds, initial state, and future-holdout cases.
This loop revises only the current task model. It does not modify PhysicsGuard,
its default thresholds, its reusable model library, or an installed skill.
