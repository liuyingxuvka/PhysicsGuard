---
name: physicsguard-model-library
description: Use when indexing reusable PhysicsGuard model assets, validation reports, compatible testbench profiles, known limits, and reuse status without storing raw datasets or overclaiming model validity.
---

# PhysicsGuard Model Library

Use this route after model-dataset validation reports exist. The model library
is an evidence index, not a raw-data database and not proof of universal model
validity.

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

## Safe Claim Boundary

The library can say where a model has validation evidence and known limits. It
must not store large raw data, invent fit, hide project evidence gaps,
or imply validity outside the referenced validation reports and evidence bundle.
