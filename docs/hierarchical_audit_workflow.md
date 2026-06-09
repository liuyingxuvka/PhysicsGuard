# Hierarchical Audit Workflow

PhysicsGuard hierarchical audit is a coarse-to-fine diagnostic workflow for complex engineering simulations. It does not reproduce a large external model at full detail. It builds a low-fidelity audit model, rolls residuals up into logical blocks, ranks suspicious blocks, and recommends the next audit template to run.

## Motivation

Large engineering models can fail for many reasons: wrong units, inconsistent pressure or flow scaling, broken power balances, map misuse, bad signal mapping, or boundary conditions that contradict physics. A single flat residual list can identify a mismatch, but it does not always say which subsystem should be refined next.

Hierarchical audit adds a block structure over the existing residual system. Level 0 can check a whole-system balance. Level 1 can check major subsystems. Level 2 can check component groups. Level 3 can check signal chains, maps, parameters, and boundaries. The same hierarchy can be run as a solved low-fidelity reference or as a direct observed-value evaluation.

## Core Concepts

`AuditBlockSpec` defines a logical block:

- `id`: stable block identifier.
- `level`: coarse-to-fine level, starting at 0.
- `parent_id`: optional parent block.
- `components`: component ids from the wrapped `SystemSpec`.
- `required_variables` and `required_parameters`: data needed for confident diagnosis.
- `expected_residual_keys`: residuals expected to inform this block.
- `refinement_template_ids`: known deeper templates that can inspect this block.

`BlockIndex` validates the hierarchy, maps components to blocks, and assigns residual diagnostics to blocks. Component residuals go to the owning block. Connection residuals between child blocks under the same parent roll up to that parent when possible. Boundary residuals use the owning component in the boundary variable.

## Residual Roll-Up

Each block receives:

- active audit residuals such as `equation`, `connection`, `boundary`, and configured `soft_check` residuals;
- diagnostic-only `post_check` residuals;
- missing required variables and parameters;
- recommended refinements triggered by block score and residual keys.

Unassigned residuals are reported explicitly. This keeps the report machine-readable and helps improve the block hierarchy over time.

## Block Score

`BlockScoringSpec` controls how residuals become a block score:

- `max`: largest absolute normalized residual.
- `rms`: root mean square of absolute normalized residuals.
- `top_k_mean`: mean of the top `k` absolute normalized residuals.
- `weighted_sum`: weighted sum by diagnostic key.

By default, `post_check` residuals are visible but excluded from block score so they do not pull or dominate the solved reference model.

## Confidence Score

`ConfidenceScoringSpec` is a heuristic, not statistical certainty. It starts from `base_confidence`, subtracts penalties for missing required variables, missing required parameters, defaulted data, or weak residual evidence, then clips to `[min_confidence, max_confidence]`.

Use confidence to decide whether a suspicious block has enough data or whether more signals should be exported before deeper debugging.

## Refinement Rules

`RefinementRuleSpec` recommends next templates when a block is suspicious. A rule can match:

- a specific block id;
- diagnostic keys;
- residual roles;
- score threshold;
- optional minimum confidence.

Rules return `RecommendedRefinement` objects with template ids, required variables, required parameters, rationale, priority, trigger score, and trigger diagnostic keys. The first version never executes these templates automatically.

## Recommended Workflow

1. Run `physicsguard project audit` so the AI has the active repository, package version, skill routes, and adoption record.
2. Complete or review the model-understanding preflight before writing the first hierarchy.
3. Run a Level 0 whole-system hierarchical audit. For external model results, prefer `hierarchy evaluate` so observed values are not moved by a solver.
4. Review the external-model intake and signal mappings before treating residuals as fault-localization evidence.
5. Inspect `audit_pass`, `top_blocks`, `top_residuals`, `signal_mapping_ledger`, `bug_family_followups`, and `recommended_refinements`.
6. If the Level 0 score is acceptable and closure evidence is clean, stop or accept coarse plausibility within the stated boundary.
7. If a block fails, export the required variables and parameters listed by the recommendation.
8. Run the next-level template for that block.
9. Repeat until the issue is narrowed to a subsystem, component, signal chain, parameter, map, unit conversion, or boundary.
10. Before a final localization claim, run closure checks or explicitly mark the claim partial, downgraded, blocked, stale, or skipped.

## Visualizing Hierarchical Audits

For non-trivial hierarchy explanations, use a compact diagram or table after the relevant audit path is stable enough to explain. The default visual should be a low-fidelity physical audit map, not a recovered external-model topology.

Choose the view by the relationship being explained:

- physical topology: block hierarchy, subsystem boundaries, interfaces, and physical or signal flow;
- residual localization: block tree plus failing residuals, normalized scores, top blocks, and pass/fail status;
- observed signal mapping: external signal names mapped into PhysicsGuard variables, with units and mapping confidence;
- assumption boundary: Assumption Cards attached to affected blocks, variables, parameters, or residual checks;
- refinement path: suspicious parent block, recommended child template, required variables, required parameters, and rationale;
- candidate blueprint: validated blocks, interfaces, units, assumptions, examples, and target-model generation boundary.

When more than one relationship type is present, label edge meanings such as `flows_to`, `maps_to`, `checked_by`, `bounds`, `refines_to`, or `requires_signal`, or split the explanation into a diagram plus a short table. A residual equation can appear as a node label or table row, but the visual should still make the subsystem boundary and next debugging action clear.

Diagrams are not validation evidence. Report validity still comes from the hierarchy JSON, FlowGuard checks, tests, CLI regressions, and release evidence.

## Observed-Value Hierarchy Mode

`physicsguard hierarchy evaluate AUDIT.yaml OBSERVED.yaml --pretty` loads a `HierarchicalAuditSpec` plus an `ObservedValuesSpec`, substitutes observed values directly into the residual system, and rolls residuals up by block. It does not solve a reference model and does not adjust observed values. The report metadata includes `mode: hierarchy_evaluate` and `solver_attempted: false`.

Observed values can optionally record first-class mapping evidence: `external_signal`, `mapping_confidence`, `mapping_status`, `review_required`, `conversion_factor`, `conversion_offset`, `conversion_note`, `mapped_at`, and `stale_when`. These fields produce a top-level `signal_mapping_ledger` in hierarchy reports. The ledger is an evidence and review index only; PhysicsGuard does not convert or rewrite observed values from it.

When mapping evidence is weak or residuals point to a repeated failure pattern, hierarchy reports also include `bug_family_followups`. These records suggest same-family checks such as signal mapping, gain/sign direction, unit conversion, and conservation-balance siblings so the audit does not stop at the first suspicious variable.

`physicsguard hierarchy compare AUDIT.yaml OBSERVED.yaml --pretty` solves the low-fidelity reference first, then evaluates observed values and includes `top_variable_deviations`. This is useful when the AI wants both residual-based suspicious blocks and a reference-vs-observed variable ranking.

This mode is meant for AI-guided external-model debugging: the AI or user maps external signals to PhysicsGuard variable names, and the report recommends the next small set of signals or parameters to inspect.

## Example: Fuel-Cell System

The fuel-cell examples under `examples/hierarchical/fuel_cell_system/` show:

- Level 0 whole-system hydrogen chemical power, stack power, auxiliary power, heat rejection, and efficiency.
- Level 1 stack, cathode air path, anode hydrogen path, coolant loop, HV system, and controls.
- Level 2 cathode air path and cooling-loop templates.
- Conflict cases that rank `fc_system` or `cathode_air_path` and recommend deeper templates.

## Example: Coolant Loop

The coolant-loop examples under `examples/hierarchical/coolant_loop/` show a coarse heat rejection balance and a Level 1 component breakdown with heat source, pump, radiator, bypass valve, and thermal mass blocks.

## Future Work

- Time-series evaluation: run residual checks over many time steps.
- Adapter layer: generate `SystemSpec` or `ObservedValuesSpec` from external tools.
- Design feasibility mode: estimate required flow, UA, power, efficiency, or other coarse quantities.
- Automatic refinement execution: not implemented; current reports only recommend next templates.
