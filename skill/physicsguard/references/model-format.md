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
`modules describe` returns variables (units, bounds, initial guesses, scales),
required/optional parameter names, residual names/roles/diagnostic keys/descriptions,
and validity metadata. Its marked synthetic parameters or external variables are
introspection examples, not physical defaults, measurements or an audit pass.
`hierarchy describe` shows blocks, parents, children, `refines`, components,
actual `supplied` parameters and `native_reads_with_defaults` (access logs, not required/optional classification),
connections, refinement rules and fault variants without solving. `--mermaid`
draws the declared blocks and labeled connections; it is not validation evidence.

## System, components and parameters

The larger `examples/hierarchical/heated_tank/heated_tank.yaml` has a `tank` root with hydraulics and thermal subsystems.
An audit has `audit_name`, `system` and `hierarchy`. In `system`, declare
`system_name` and components with unique `id`, registered `type` and `parameters`:

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
Under `hierarchy.refinement_rules`, select `block_id`, `score_threshold`, optional
`trigger_diagnostic_keys` and `next_template_ids`; include `rationale` and the next
required signals. Template ids refer to same-file blocks or files relative to the
audit directory or its parent. Reports distinguish `block`, `file` and `missing`;
finding a file never executes it. Inconsistent coarse/detail checks stay visible.

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

Connections propagate known values without overwriting measurements. Supported
per-residual value/control dependencies permit bounded one-unknown derivation
for equation/connection/boundary/assumption relations. Ambiguous, flat or
unsupported cases remain unknown; this is not general nonlinear uniqueness.
Put measurement-to-internal components first: in the tank, electrical power before
command comparison, inflow conversion before throughflow, and thermal balance last.
Read `derived_variables`, `checked_residuals` and `unchecked_residuals`; producers never count as checks. No independent check means refusal.

Once the coarse and refined checks are useful, add top-level `fault_variants`:
use unique `id`, required `kind: fault` or `benign`, qualified `parameters` overrides
and/or `changes` entries naming `variable` and exactly one of `scale`, `offset`,
`set`, `flip_sign: true`. `rederive` removes listed measurements before deriving
them under the device; `expect_blocks` names required own failures. Audit with the nominal
model: `task-model variants AUDIT.yaml NOMINAL.yaml --pairs --json`.
Keep the model and snapshot unchanged. Read own checked-block signs, missing expected failures, indistinguishable groups and unmeasured `next_signal`.
A matching signature is bounded discrimination, not proof of the physical cause.
Use contracts and disjoint validation evidence for model/data claims; a snapshot alone licenses neither time prediction nor high-fidelity truth.
