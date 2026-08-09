# PhysicsGuard Model Understanding Preflight

Use this route before interpreting residuals for a non-trivial external model.
If a concrete testbench data file is part of the work, record the file/bench
boundary and route to `physicsguard-test-file-contract-review` before broad
analysis claims.

## Blueprint preflight projection

Freeze target id/revision, boundary fingerprint, provider capabilities, independent inventory inputs, intended artifact root, and first useful understanding layer. Use the current summary for ordinary preflight or the exact affected slice for one known boundary/inventory gap. Preserve blueprint/review/projection fingerprints and first gap when supplied. This route does not author or fully review the blueprint; that is a typed handoff to `physicsguard-candidate-model-blueprint`. Missing/stale identity blocks without loading the full blueprint or scanning the target as fallback.

Executable projection entry: call `physicsguard.summary_physical_blueprint_projection(blueprint, review)` for ordinary preflight or `physicsguard.affected_physical_blueprint_projection(blueprint, review, seed_ids, target_inventory_authority=authority, blueprint_base_dir=blueprint_root, authority_base_dir=authority_root)` for one named boundary or inventory gap. The affected query reruns the canonical reviewer once against the exact blueprint artifacts, frozen authority, and raw target material and requires the supplied review to equal that passing result before graph compilation; it never silently refreshes a stale review.

## Workflow

1. Create or review a preflight file based on templates/model_understanding_preflight.yaml.
2. Run:

   ```powershell
   python -m physicsguard.cli preflight review PREFLIGHT.yaml --pretty
   ```

3. If missing inputs or uncertain mappings are reported, complete them or route to signal mapping review before fault claims.
4. Before planning validation, name the intended claim scope and model
   semantics (`pointwise` or `stateful_dynamic`). Identify the authoritative
   manifest, role matrix, hierarchy, evidence registry/bundle, available time
   range, operating modes, important events/peaks/boundaries, critical
   signals/parameters, subsystem families, and the project source for
   quantitative adequacy thresholds. Classify each available model parameter
   as static or time-varying from a named source; identify the series mapping
   for every time-varying parameter. Unknowns stay explicit.
5. If prediction is intended, confirm that an official or user-owned execution
   route can preserve initial state and step semantics and produce an exact
   trajectory plus disjoint future holdout. Without that route, stop at bounded
   pointwise validation or a candidate-model blueprint.
6. Declare whether each critical observation is a point value or a bounded
   interval. For intervals, identify measurement, mapping, and model-approximation
   contributions and keep unknown bounds explicit. Also freeze the competing
   fault-hypothesis and available-signal inventories before making any
   diagnosability claim.

Preflight pass is planning evidence only. It is not residual validation.
