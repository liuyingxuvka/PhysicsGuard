# PhysicsGuard Model Understanding Preflight

Use this route before interpreting residuals for a non-trivial external model.
If a concrete testbench data file is part of the work, record the file/bench
boundary and route to `physicsguard-test-file-contract-review` before broad
analysis claims.

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
