# PhysicsGuard Model Format

An audit is a low-fidelity set of explicit physical relations and a block tree; it does not reconstruct an external solver.
Start from `templates/audit_model.yaml` and `templates/observed_snapshot.yaml`.
The electrical example supplies all three measurements so its power relation remains an independent check. A relation used to produce a missing value cannot also validate that value.

## Discover the available relations

```sh
python -m physicsguard.cli modules list
python -m physicsguard.cli modules describe TankVolumeRateModule --pretty
python -m physicsguard.cli hierarchy describe AUDIT.yaml --pretty
python -m physicsguard.cli hierarchy describe AUDIT.yaml --mermaid
python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml --json
```

`modules list` prints each registered type and its first documentation sentence.
`modules describe` returns variables (units, bounds, initial guesses, scales), required/optional parameter names, residual names/roles/diagnostic keys/descriptions, and validity metadata. Its marked synthetic parameters or external variables are introspection examples, not physical defaults, measurements or an audit pass.
`hierarchy describe` shows blocks, parents, children, `refines`, components,
actual `supplied` parameters and `native_reads_with_defaults` (access logs, not required/optional classification),
connections, refinement rules and fault variants without solving. `--mermaid`
draws the declared blocks and labeled connections; it is not validation evidence.

## System, components and parameters

The larger `examples/hierarchical/heated_tank/heated_tank.yaml` has a `tank` root with hydraulics and thermal subsystems.
A single-system file is read as a tree with one root block.
An audit has `audit_name`, `system` and `hierarchy`. In `system`, declare `system_name` and components with unique `id`, registered `type` and `parameters`:

```yaml
components:
  - id: vol
    type: TankVolumeRateModule
    parameters: {dt_s: 10.0, residual_scale_m3: 0.0005}
```

Its variables are `volume_previous_m3`, `volume_current_m3`, `V_dot_in_m3_s` and `V_dot_out_m3_s`.
Names are qualified as `vol.volume_current_m3`; values and parameters use SI units. Reference parameters ending in `_variables` take YAML lists of qualified names, for example `source_power_variables: [supply.P_W]`.
Use `modules describe` to choose the actual type's parameters and validity range.
Residual scales normalize mismatch; they are not knobs to hide a failed check.
Solver variables require finite bounds and initial guesses, and positive scales.

## Connections and boundaries

Inside `system`, a connection means identity of the same physical quantity:

```yaml
connections:
  - from_variable: lvl_cur.volume_m3
    to_variable: vol.volume_current_m3
    scale: 0.0005
boundaries:
  - variable: vol.V_dot_out_m3_s
    value: 0.001
    unit: m^3/s
```

Omit `scale` for the tight identity default (one millionth of the larger endpoint
variable scale), or supply a positive finite tolerance justified by the model.
If quantities can physically differ, use an explicit relation, not a loose identity.
A boundary is a declared constraint, not an additional independent measurement.

## Explicit assumptions

Cards are a list under `system.assumptions`, for example the tank's nameplate card:

```yaml
assumptions:
  - id: heater_nameplate_efficiency
    target_type: variable
    target: heater_eff.efficiency
    value: 0.98
    unit: '1'
    reason: Nameplate efficiency used in this operating envelope.
    source: equipment nameplate
    impact: medium
    status: active
    review_required: true
```

Use `target_type: parameter` for a qualified component parameter, or `context` for an explicit contextual card. Only active cards apply; proposed/rejected cards do
not. Do not silently invent assumptions, override measurements or tune cards to pass.
Compact reports expose each card's `id`, `status` and `applied`; use `assumptions inspect AUDIT.yaml` for full cards. Confidence remains heuristic.

## Blocks and model growth

`hierarchy.blocks` groups components: `tank` at level 0, then `thermal`, with finer heater, throughflow and envelope blocks.
Start with a coarse balance; add one finer subsystem only when evidence needs it.
For a refinement, declare both coarse and detailed components, then link the child:

```yaml
blocks:
  - {id: tank, level: 0, components: [coarse_balance]}
  - id: thermal
    level: 1
    parent_id: tank
    components: [detail_balance]
    refines: [coarse_balance]
```

`refines` must name the parent's own components. It is not implied by parentage.
Block ids are unique and contain no whitespace; parents must exist, cycles are rejected, levels are nonnegative and component ownership is unique. Blocks can declare `name`, `tags`, JSON `metadata`, and required/optional variables and parameters.
Under `hierarchy.refinement_rules`, select `block_id`, `score_threshold`, optional `trigger_diagnostic_keys` and `next_template_ids`; include `rationale` and the next required signals. Template ids refer to same-file blocks or files relative to the audit directory or its parent. Reports distinguish `block`, `file` and `missing`; finding a file never executes it. Inconsistent coarse/detail checks stay visible.

Component residuals belong to their owning block; connections between sibling blocks roll up to their nearest common ancestor, boundaries to the owning component. Unassigned residuals remain explicit.
`own_audit_pass` is local, `audit_pass` includes descendants, and `subtree_score` is the maximum own score in the subtree; local `score` still orders `top_blocks`.
`hierarchy.scoring.method` supports `max`, `rms`, `top_k_mean` (`top_k`) and `weighted_sum` (`diagnostic_key_weights`); role filters include active relations and exclude `post_check` by default.
`hierarchy.confidence` clips a heuristic base minus missing required-variable/parameter, no-residual and configured level penalties to its min/max; it is not probability.
Refinement rules may filter `trigger_roles`, `trigger_diagnostic_keys`, `confidence_min` and a `score_threshold` (default 1.0); recommendations retain next required variables/parameters and sort by descending priority, then trigger score.
`refinement_checks` compares checked coarse residuals with refining children: passing children plus a failed coarse check is inconsistent; a passing coarse check with a failed child is consistent. When coarse relations were consumed as producers or no scored coarse check is usable, `coarse_pass` and `consistent` are null with a reason.

## Observed snapshots and freshness

An observed file has `observation_name` and `variables` keyed by qualified names:

```yaml
variables:
  vol.V_dot_in_m3_s:
    value: 0.001
    unit: m^3/s
    external_signal: bench/inlet_flow
    mapping_confidence: high
    mapping_status: clean
    conversion_factor: 0.001
    conversion_offset: 0.0
    conversion_note: Exporter already converted litres/s to m^3/s.
    stale_when: [flow sensor replaced]
```

`value` is already the SI value to check. Conversion fields record evidence and never transform it. Record mapping uncertainty and `review_required` honestly.
`stale_when` declares reconfirmation conditions; when one occurs, set `mapping_status: stale`. Do not present old mappings as current evidence.

## Derivation order and fault variants

Connections propagate known values within variable bounds without overwriting measurements or already derived values; propagating around a cycle creates no independent observation. Supported per-residual value/control dependencies permit bounded one-unknown derivation for equation/connection/boundary/assumption relations. Ambiguous, flat or unsupported cases remain unknown; this is not general nonlinear uniqueness.
Put measurement-to-internal components first: in the tank, electrical power before command comparison, inflow conversion before throughflow, and thermal balance last.
Read `derived_variables`, `checked_residuals` and `unchecked_residuals`; producers never count as checks. No independent check means refusal.

Once the coarse and refined checks are useful, add top-level `fault_variants`: use unique `id`, required `kind: fault` or `benign`, qualified `parameters` overrides and/or `changes` entries naming `variable` and exactly one of `scale`, `offset`, `set`, `flip_sign: true`. `rederive` removes listed measurements before deriving them under the device; `expect_blocks` names required own failures. Audit with the nominal model: `hierarchy variants AUDIT.yaml NOMINAL.yaml --pairs --json`.
Keep the model and snapshot unchanged. Read own checked-block signs, missing expected failures, indistinguishable groups and unmeasured `next_signal`.
Observed-value changes and rederive names must be registered measurements present in the nominal snapshot, and numeric edits must be finite. A parameter override may replace a legal module default absent from YAML; the native constructor still validates its value.
The device is a copy: remove requested measurements, derive them with its changed parameters, then check the generated data with the unchanged nominal model; this is neither reference optimization nor time-forward rollout.
Each signature uses the sign of a block's largest directly checked residual when that block has an own failure, retaining a genuine own failure even when the block has children. Producing or unchecked relations cannot supply fault evidence.
Unavailable generated measurements keep `status: not_evaluable`, a reason, null signature/audit status and false check flags; other rows remain visible and the case cannot match observed data. Full JSON retains counterfactual `generated_values`, `device_values` and `rederived_variables`; the compact view omits the value maps.
Nonempty proper-subset pair failures are physically masked and listed in `masked_pairs`; an empty or outside-expected signature fails. `pairwise` and ranked `next_signal` expose remaining discrimination.
With `--observed`, a failing audit with no matching fault signature reports `model_miss`; healthy observed data is not a model miss.
A matching signature is bounded discrimination, not proof of the physical cause.
Strict library evaluation rejects still-missing variables after derivation; the CLI lists and skips them, but neither accepts zero independent checks. `hierarchy compare` still requires the complete registered observed snapshot and solves a reference, as does `hierarchy run`.
Use contracts and disjoint validation evidence for model/data claims; a snapshot alone licenses neither time prediction nor high-fidelity truth.
