# PhysicsGuard Model Library

## Reuse within one read-only task

Pass an already qualified exact current summary, affected projection or reverse trace to the next native owner when its source, material, authority, revision and selector identities remain unchanged. Combine all affected seed ids for the requested scope into one affected API call. Inspect the existing returned slice before asking for another projection of the same scope. If inputs or raw target material change, run the existing canonical qualification gate again; a prior review, summary or hash label does not bypass it. Unknown or invalid seeds block the whole request; never join separately accepted fragments to hide a rejected seed. This is task-local reuse of an actual result, without a persistent cache or new receipt.

Use this route after model-dataset validation reports exist. The model library
is an evidence index, not a raw-data database and not proof of universal model
validity.

## Blueprint reuse projection

If no blueprint is supplied or project-declared and the request is ordinary bounded native work, run the native owner directly; report blueprint_not_provided and the unexamined scope, without a blueprint PASS. If a blueprint is supplied, project-declared, or needed for a target/whole-boundary claim, require the exact current review/projection below. Missing, stale, foreign, ambiguous, or unknown-seed identity blocks that selected path; never downgrade it to bypass the requirement.

For this selected blueprint path: Index and select by exact current blueprint fingerprint, physical obligation, target profile, validity boundary, testbench, native validation receipt, and verified reuse limit. Summary supports discovery; affected supports one bounded reuse decision; full is reserved for whole-target qualification. Loose similarity, matching names, or an old validation report is not compatibility. Missing/stale projection identity blocks the selected blueprint path without scanning or validating unrelated assets.

Executable projection entry (only for a supplied/project-declared blueprint or a claim requiring its boundary): use `physicsguard.summary_physical_blueprint_projection(blueprint, review)` for discovery, `physicsguard.affected_physical_blueprint_projection(blueprint, review, seed_ids, target_inventory_authority=authority, blueprint_base_dir=blueprint_root, authority_base_dir=authority_root)` for one reuse decision, and `physicsguard.full_physical_blueprint_projection(blueprint, review)` only for explicit whole-target qualification. The affected query reruns the canonical reviewer once against the exact blueprint artifacts, frozen authority, and raw target material and requires the supplied review to equal that passing result before licensing the bounded reuse scope.

For cross-project discovery, historical search, or "which projects/models have
we tested before" questions, do not answer from one model library index alone.
Model libraries can provide provider evidence to an external database ledger,
but this PhysicsGuard route does not own database indexes, lifecycle, query, or
freshness gates.

## Workflow

1. Create or update a model library index:

   ```yaml
   library_id: example_model_library
   entries:
     - model_id: pump_loop_low_fidelity_v1
       model_file: path/to/hierarchy.yaml
       evidence_registry: path/to/project_evidence_registry.yaml
       model_context: pump_loop_model_context
       evidence_bundle_id: pump_loop_validation_bundle
       validation_reports:
         - reports/example_validation.yaml
       reuse_status: partial
   ```

2. Check the index:

   ```powershell
   python -m physicsguard.cli model-library check MODEL_LIBRARY.yaml --pretty
   ```

3. Treat missing model files, stale hashes, missing validation reports, or
   invalid report references as blocking for broad reuse claims.
   A `validated` reuse claim additionally requires a current passing native
   validation-depth receipt with exact dataset/mapping/time/scenario/split and
   report identity, compatible `covered_scope`, and a passing quantitative
   adequacy receipt over the artifact-derived universe. A scalar-only,
   snapshot, shallow, scope-incompatible, or partial receipt supports at most
   partial, explicitly bounded reuse.
   The receipt must classify every available parameter and show passing
   per-parameter dynamic floors, strata, row-gap, and executable model-
   contribution depth for each time-varying parameter; one static-looking
   value or a disconnected observation cannot silently stand in for a time
   history.
4. When evidence registry and bundle references exist, run or trust the
   `model-library check` gap gate. Blocking project evidence gaps prevent
   validated reuse; review gaps must remain visible.

5. Record predictive capability only when the entry references a current
   `stateful_dynamic` future-rollout receipt with disjoint training/holdout,
   passing metrics and stability, and an explicit checked horizon. Pointwise
   validation or reuse evidence must never be relabeled predictive.

## Safe Claim Boundary

The library can say where a model has validation evidence and known limits. It
must not store large raw data, invent fit, hide project evidence gaps,
or imply validity outside the referenced validation reports, adequacy universe,
prediction horizon, and evidence bundle.
