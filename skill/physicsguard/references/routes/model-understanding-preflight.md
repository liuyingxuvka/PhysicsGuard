# PhysicsGuard Model Understanding Preflight

## Entry boundary

Accept this route only when:

- A non-trivial external model must be understood before residual interpretation or blueprint work.
- The physical boundary, inventory, assumptions, access gaps, semantics, or stop conditions need a current review.

Reject or hand off when:

- The request is only to resolve signal identity, unit, conversion, or confidence. Handoff: the `signal-mapping-review` route.
- A concrete test-data file needs field-level coverage first. Handoff: the `test-file-contract-review` route.

## Minimum workflow

1. Freeze the symptom, external authority, physical boundary, and required inventory.
2. Following the route protocol below, review subsystems, signals, parameters, assumptions, uncertainty, and prediction access.
3. Proceed only inside the passed planning boundary; send unresolved mappings or files to their direct owners.

## Required outputs

- `preflight_status`
- `understanding_record`
- `access_gaps`
- `next_route`

Claim boundary: Preflight licenses only that the declared low-fidelity audit boundary is sufficiently understood to proceed; unresolved access or inventory gaps remain visible blockers.

## Route protocol

Use this route before interpreting residuals for a non-trivial external model.
If a concrete testbench data file is part of the work, record the file/bench
boundary and route to the `test-file-contract-review` route before broad
analysis claims.

## Workflow

1. Create or review a preflight file starting from `references/templates/model_understanding_preflight.yaml` in this skill's directory.
2. Run:

   ```powershell
   python -m physicsguard.cli preflight review PREFLIGHT.yaml
   ```

3. If missing inputs or uncertain mappings are reported, complete them or route to signal mapping review before fault claims.
4. Before planning validation, name the intended claim scope and model
   semantics (`pointwise` or `stateful_dynamic`). Identify the authoritative
   manifest, role matrix, hierarchy, contract mapping edges, available time
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
