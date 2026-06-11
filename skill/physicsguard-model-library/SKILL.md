---
name: physicsguard-model-library
description: Use when indexing reusable PhysicsGuard model assets, validation reports, compatible testbench profiles, known limits, and reuse status without storing raw datasets or overclaiming model validity.
---

# PhysicsGuard Model Library

Use this route after model-dataset validation reports exist. The model library
is an evidence index, not a raw-data database and not proof of universal model
validity.

## Workflow

1. Create or update a model library index:

   ```yaml
   library_id: example_model_library
   entries:
     - model_id: pump_loop_low_fidelity_v1
       model_file: path/to/hierarchy.yaml
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

## Safe Claim Boundary

The library can say where a model has validation evidence and known limits. It
must not store large raw data, invent compatibility, or imply validity outside
the referenced validation reports.
