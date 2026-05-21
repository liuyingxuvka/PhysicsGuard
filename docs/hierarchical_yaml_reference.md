# Hierarchical YAML Reference

Hierarchical audit YAML wraps a normal PhysicsGuard `SystemSpec` with a `hierarchy` section.

```yaml
# PhysicsGuard hierarchical audit/model blueprint
# Purpose: Coarse whole-system fuel-cell audit.
# Repository: https://github.com/liuyingxuvka/PhysicsGuard
# Use with: python -m physicsguard.cli hierarchy run this_file.yaml --pretty
# Boundary: Low-fidelity SI-unit residual audit or blueprint only; not a high-fidelity solver, commercial-tool adapter, or reverse-engineered model.
audit_name: fuel_cell_system_level_0
description: Coarse whole-system fuel-cell audit
system:
  system_name: fuel_cell_system_level_0
  components:
    - id: power_balance
      type: AggregatePowerBalanceModule
      parameters:
        source_power_variables: [fuel.P_chemical_W]
        load_power_variables: [stack.P_stack_W, aux.P_aux_W]
        residual_scale_W: 1000.0
  boundaries: []
  solver:
    method: least_squares
    max_iterations: 60
    audit_threshold: 1.0
hierarchy:
  blocks:
    - id: fc_system
      name: Fuel-cell system
      level: 0
      components: [power_balance]
      required_variables: [fuel.P_chemical_W, stack.P_stack_W]
      expected_residual_keys: [aggregate_power_balance_mismatch]
      refinement_template_ids:
        - fuel_cell_system/level_1_major_subsystems
  refinement_rules:
    - id: refine_fc_system_on_power
      block_id: fc_system
      trigger_diagnostic_keys: [aggregate_power_balance_mismatch]
      score_threshold: 1.0
      next_template_ids:
        - fuel_cell_system/level_1_major_subsystems
      next_required_variables: [stack.P_stack_W, aux.P_aux_W]
      rationale: Power balance mismatch should be decomposed by subsystem.
      priority: 10
  scoring:
    method: max
  confidence:
    base_confidence: 1.0
```

## HierarchicalAuditSpec

Top-level fields:

- `audit_name`: required nonempty name.
- `description`: optional text.
- `system`: normal `SystemSpec`.
- `hierarchy`: `HierarchySpec`.
- `metadata`: optional JSON-serializable object.

## HierarchySpec

Fields:

- `blocks`: one or more `AuditBlockSpec` entries.
- `refinement_rules`: optional `RefinementRuleSpec` entries.
- `scoring`: optional `BlockScoringSpec`.
- `confidence`: optional `ConfidenceScoringSpec`.

Validation:

- block ids must be unique;
- parent ids must reference existing blocks;
- cycles are rejected;
- levels must be nonnegative;
- components are expected to be uniquely owned by one block;
- refinement rules with `block_id` must reference an existing block.

## AuditBlockSpec

Common fields:

- `id`: required, no whitespace.
- `name`: optional display name.
- `level`: nonnegative integer.
- `parent_id`: optional parent block id.
- `components`: component ids from the wrapped `SystemSpec`.
- `tags`: optional normalized labels.
- `required_variables`: variables needed for confidence.
- `optional_variables`: useful extra variables.
- `required_parameters`: parameters needed for confidence.
- `optional_parameters`: useful extra parameters.
- `expected_residual_keys`: diagnostic keys expected for this block.
- `refinement_template_ids`: deeper templates that may inspect this block.
- `metadata`: optional JSON object.

Variable references should normally use `component.variable` format.

## RefinementRuleSpec

Fields:

- `id`: required rule id.
- `block_id`: optional block id; omitted means rule can apply to any block.
- `trigger_diagnostic_keys`: optional diagnostic key filter.
- `trigger_roles`: optional residual-role filter.
- `score_threshold`: default `1.0`.
- `confidence_min`: optional minimum confidence.
- `next_template_ids`: template ids to recommend.
- `next_required_variables`: variables needed for the next level.
- `next_required_parameters`: parameters needed for the next level.
- `rationale`: optional machine-readable rationale string.
- `priority`: larger priority sorts earlier when score ties are similar.

A rule applies when block id, score, confidence, diagnostic-key, and role filters match. The rule recommends next templates only; it does not execute them.

## BlockScoringSpec

Fields:

- `method`: `max`, `rms`, `top_k_mean`, or `weighted_sum`.
- `top_k`: positive integer for `top_k_mean`.
- `include_roles`: defaults to `equation`, `connection`, `boundary`, and `soft_check`.
- `exclude_roles`: defaults to `post_check`.
- `diagnostic_key_weights`: optional weights for `weighted_sum`.

Default scoring is based on active audit residuals. `post_check` residuals remain visible but do not dominate scores unless explicitly included.

## ConfidenceScoringSpec

Fields:

- `base_confidence`: default `1.0`.
- `missing_required_variable_penalty`: default `0.15`.
- `missing_required_parameter_penalty`: default `0.10`.
- `unassigned_residual_penalty`: default `0.05`.
- `default_parameter_penalty`: default `0.10`.
- `coarse_level_penalty_per_level_above_zero`: default `0.0`.
- `min_confidence`: default `0.0`.
- `max_confidence`: default `1.0`.

Confidence is a heuristic for data sufficiency and residual evidence. It is not statistical confidence.

## CLI

```powershell
python -m physicsguard.cli hierarchy run examples/hierarchical/fuel_cell_system/level_0_system_balance.yaml --pretty
python -m physicsguard.cli hierarchy inspect examples/hierarchical/fuel_cell_system/level_0_system_balance.yaml --pretty
python -m physicsguard.cli hierarchy plan examples/hierarchical/fuel_cell_system/conflict_level_0_h2_power.yaml --pretty
python -m physicsguard.cli hierarchy evaluate examples/hierarchical/observed_debugging/pitch_feedback_level_0.yaml examples/hierarchical/observed_debugging/pitch_feedback_observed_fault.yaml --pretty
python -m physicsguard.cli hierarchy compare examples/hierarchical/observed_debugging/pitch_feedback_level_0.yaml examples/hierarchical/observed_debugging/pitch_feedback_observed_fault.yaml --pretty
```

`hierarchy run` emits the full solve-based hierarchical report. `hierarchy inspect` validates and summarizes the block tree without solving. `hierarchy plan` runs the solve-based audit and emits only top blocks, recommended refinements, missing variables, missing parameters, and warnings. `hierarchy evaluate` substitutes observed external values without solving and rolls residuals up by block. `hierarchy compare` solves a low-fidelity reference, evaluates observed values, and returns both block diagnostics and variable deviations.

Observed values use the existing `ObservedValuesSpec` format:

```yaml
observation_name: pitch_feedback_observed_fault
variables:
  controller_q_gain.x:
    value: 2.0
    unit: rad/s
  controller_q_gain.y:
    value: -1.6312
    unit: controller command contribution
metadata:
  mapping_note: external signals were mapped by AI or user review
```
