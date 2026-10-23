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
- `refines`: optional coarse component ids owned directly by this block's parent.
- `required_variables` and `required_parameters`: data needed for confident diagnosis.
- `refinement_template_ids`: known deeper templates that can inspect this block.

`BlockIndex` validates the hierarchy, maps components to blocks, and assigns residual diagnostics to blocks. Component residuals go to the owning block. Connection residuals between child blocks under the same parent roll up to that parent when possible. Boundary residuals use the owning component in the boundary variable.

## Residual Roll-Up

Each block receives:

- active audit residuals such as `equation`, `connection`, `boundary`, and configured `soft_check` residuals;
- diagnostic-only `post_check` residuals;
- missing required variables and parameters;
- recommended refinements triggered by block score and residual keys.

Unassigned residuals are reported explicitly. This keeps the report machine-readable and helps improve the block hierarchy over time.

A block's `own_audit_pass` preserves the local verdict from its own assigned residuals. Its `audit_pass` also includes every descendant: a failing child makes its ancestors fail. `subtree_score` is the maximum of the block's own `score` and all descendant scores. The existing score algorithm and `top_blocks` ordering still use each block's own `score`, so a failing detailed block remains visible rather than being displaced by copies of its score on every ancestor. The report's overall `audit_pass` retains its existing meaning.

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

A child can declare `refines: [coarse_component_id]` to link its detailed audit to a coarse relation owned directly by its parent. The schema rejects ids belonging only to a sibling or another descendant, and names the invalid component. This link does not move component ownership or change scores.

The report's `refinement_checks` contains one row for each refined parent: `parent`, `coarse_components`, `child_blocks`, `coarse_pass`, `children_pass` and `consistent`, plus `reason` when comparison is unavailable. It compares the coarse components' own checked residuals with the refining child results, preserving the configured scoring-role filters and default post-check exclusion. When all children pass but a checked coarse relation fails, `consistent` is false and the report warns `refinement_inconsistent: <parent>`; inspect the coarse relation or its parameters. A passing coarse relation with a failing detail is consistent: the finer check found a fault that the coarse check could not see. If every coarse relation was used to derive values, or no usable scored coarse check exists, `coarse_pass` and `consistent` are null with a reason rather than a claim of agreement.

Each recommendation retains all `next_template_ids` and adds a `template_status` mapping from each id to `block`, `file` or `missing`. A same-file block id resolves as `block`; otherwise the CLI checks the audit file's directory and its parent for the id, with or without `.yaml`. A found file resolves as `file`; a missing id adds `refinement_template_missing: <id>`. Library callers can supply the audit directory through `base_dir`. Resolution reports availability only: it neither validates a found template's result nor executes it. `hierarchy inspect` also shows each block's `refines` links.

## Recommended Workflow

1. Complete or review the model-understanding preflight before writing the first hierarchy.
2. Run a Level 0 whole-system hierarchical audit. For external model results, prefer `hierarchy evaluate` so observed values are not moved by a solver.
3. If the source is a concrete testbench data file, run the file's
   the single-file `TestFileContract` check before treating all file
   columns as audit evidence.
4. Review the external-model intake and signal mappings before treating residuals as fault-localization evidence.
5. Inspect `audit_pass`, `top_blocks`, `top_residuals`, `signal_mapping_ledger`, `bug_family_followups`, and `recommended_refinements`.
6. If the Level 0 score is acceptable and no refinement, mapping issue or missing input is open, stop or accept coarse plausibility within the stated boundary.
7. If a block fails, export the required variables and parameters listed by the recommendation.
8. Run the next-level template for that block.
9. Repeat until the issue is narrowed to a subsystem, component, signal chain, parameter, map, unit conversion, or boundary.
10. Before a final localization claim, list every open refinement, mapping issue and missing input, or mark the claim partial.

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

`physicsguard hierarchy evaluate AUDIT.yaml OBSERVED.yaml --pretty` loads a `HierarchicalAuditSpec` plus an `ObservedValuesSpec`, preserves the supplied observations, derives supported intermediate values, and rolls the remaining checked residuals up by block. It does not run `BoundedSolver.solve` or adjust observed values. The report metadata includes `mode: hierarchy_evaluate` and `solver_attempted: false`.

Connections propagate a known value to an unknown endpoint within its bounds. They never overwrite a measured endpoint or an already derived value. When measured endpoints disagree, a connection that was not consumed by propagation remains a real mismatch check. With competing connections, declaration order determines the first derived value; the conflicting measurement is preserved. Propagating one measurement around a cycle does not create a new independent observation.

Each supported native residual has its own structural value and control dependencies; an unrelated read in another residual does not make both relations unavailable. This keeps zero-product and flat-branch dependencies visible without numerical dependency probes or a module-wide read union. Unsupported custom or dynamic sources remain unresolved. They can be checked numerically when every registered value is actually known, but missing values cannot be licensed from an initial guess or an empty dependency claim. A genuine parameter-only post-check remains a parameter check.

Derivation repeatedly considers `equation`, `connection`, `boundary` and `assumption` relations with exactly one unknown, in component declaration order. It searches the variable's finite bounds for an isolated scalar root. Detected multiple roots, flat-zero regions, undefined samples and unresolved sources are not accepted. This finite search is not a proof of global uniqueness for an arbitrary nonlinear function. `soft_check` and `post_check` relations never derive values. A relation consumed to produce a value is excluded from checked residuals, block scores and `top_residuals`; no remaining check means evaluation is refused with `no residual can be evaluated without them`.

The full report separates:

- `derived_variables`: each derived value and its producing residual or connection;
- `checked_residuals`: the remaining relations evaluated with known inputs;
- `unchecked_residuals`: the unavailable relations and their missing variables.

Blocks also carry these names and gaps. The compact summary lists derived variable names plus `checked_residual_count` and `unchecked_residual_count`. `missing_required_variables` names values still unavailable after derivation. The library's default `skip_unobserved=False` rejects those remaining values after trying derivation; `hierarchy evaluate` uses `skip_unobserved=True` and reports the skipped relations. Neither policy permits an evaluation with no check. Residual-series validation likewise accepts a required variable that was observed or derived, while preserving missing-input, coverage and adequacy checks for the rest.

Put measurement-to-internal relations before relations intended to check the result. In the heated-tank coupled reference, `heater_el` precedes `heater_cmd`, so measured voltage and current supply power and the command remains a check. In the coarse reference, `inflow_mass` precedes `through`, and `heat` comes after the heat-outflow relations, so thermal balance remains a check rather than supplying its own outflow. The step-30 measured snapshots pass; at step 70 the coarse model points to `thermal`, while the coupled model exposes the heater-command mismatch with thermal balance within threshold. These are bounded low-fidelity checks, not independent validation of every derived relation.

Observed values can optionally record first-class mapping evidence: `external_signal`, `mapping_confidence`, `mapping_status`, `review_required`, `conversion_factor`, `conversion_offset`, `conversion_note`, `mapped_at`, and `stale_when`. These fields produce a top-level `signal_mapping_ledger` in hierarchy reports. The ledger is an evidence and review index only; PhysicsGuard does not convert or rewrite observed values from it. `stale_when` records when a mapping needs reconfirmation; when a listed condition occurs, set `mapping_status` to `stale`.

For large test data files, prefer `TestFileContract` mapping edges before
creating observed snapshots. The contract checks every file field, while the
observed snapshot usually contains only the variables selected for one audit.

When mapping evidence is weak or residuals point to a repeated failure pattern, hierarchy reports also include `bug_family_followups`. These records suggest same-family checks such as signal mapping, gain/sign direction, unit conversion, and conservation-balance siblings so the audit does not stop at the first suspicious variable.

`physicsguard hierarchy compare AUDIT.yaml OBSERVED.yaml --pretty` solves the low-fidelity reference first, then evaluates observed values and includes `top_variable_deviations`. This is useful when the AI wants both residual-based suspicious blocks and a reference-vs-observed variable ranking.

`hierarchy run` and `hierarchy compare` keep their existing reference-solve behavior; comparison still requires the complete registered observed snapshot. Intermediate derivation is the observed-evaluation path, not a change to either reference mode.

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

## Command Exit Codes

Exit codes are `0` for a passed check, `1` for a check that ran and did not pass,
and `2` when the command could not run (including invalid input or missing required
files/variables). Audit commands use `audit_pass`; comparison uses the observed
`observed_audit_pass`, not reference-solver convergence. Successful structural
inspection and manifest/contract inspection or diff commands return `0`.
The JSON report and compact/full output formats do not change with this convention.
