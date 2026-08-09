# PhysicsGuard Model Library

Use this route after model-dataset validation reports exist. The model library
is an evidence index, not a raw-data database and not proof of universal model
validity.

## Blueprint reuse projection

Index and select by exact current blueprint fingerprint, physical obligation, target profile, validity boundary, testbench, native validation receipt, and verified reuse limit. Summary supports discovery; affected supports one bounded reuse decision; full is reserved for whole-target qualification. Loose similarity, matching names, or an old validation report is not compatibility. Missing/stale projection identity blocks without scanning or validating unrelated assets.

Executable projection entry: use `physicsguard.summary_physical_blueprint_projection(blueprint, review)` for discovery, `physicsguard.affected_physical_blueprint_projection(blueprint, review, seed_ids, target_inventory_authority=authority, blueprint_base_dir=blueprint_root, authority_base_dir=authority_root)` for one reuse decision, and `physicsguard.full_physical_blueprint_projection(blueprint, review)` only for explicit whole-target qualification. The affected query reruns the canonical reviewer once against the exact blueprint artifacts, frozen authority, and raw target material and requires the supplied review to equal that passing result before licensing the bounded reuse scope.

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
5. For `validated` reuse or broad reuse-readiness claims, include the model
   library in a project closure plan and run:

   ```powershell
   python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
   ```

   The closure report must be passed before broad reuse claims. Partial or
   downgraded closure means only limited reuse wording is safe.
6. Record predictive capability only when the entry references a current
   `stateful_dynamic` future-rollout receipt with disjoint training/holdout,
   passing metrics and stability, and an explicit checked horizon. Pointwise
   validation or reuse evidence must never be relabeled predictive.

## Safe Claim Boundary

The library can say where a model has validation evidence and known limits. It
must not store large raw data, invent fit, hide project evidence gaps,
or imply validity outside the referenced validation reports, adequacy universe,
prediction horizon, and evidence bundle.
