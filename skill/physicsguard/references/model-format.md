# PhysicsGuard Model Format

An audit is a low-fidelity set of explicit physical relations and a block tree; it does not reconstruct an external solver.
Start from `templates/audit_model.yaml` and `templates/observed_snapshot.yaml`.
The electrical example supplies all three measurements so its power relation remains an independent check. A relation used to produce a missing value cannot also validate that value.

## Discover the available relations

```sh
python -m physicsguard.cli modules list
python -m physicsguard.cli modules describe TankVolumeRateModule --pretty
python -m physicsguard.cli hierarchy describe AUDIT.yaml
python -m physicsguard.cli hierarchy describe AUDIT.yaml --json
python -m physicsguard.cli hierarchy describe AUDIT.yaml --observed OBSERVED.yaml
python -m physicsguard.cli hierarchy describe AUDIT.yaml --mermaid
python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml --json
```

`modules list` prints each registered type and its first documentation sentence.
`modules describe` returns variables (units, bounds, initial guesses, scales), required/optional parameter names, residual names/roles/diagnostic keys/descriptions, and validity metadata. Its marked synthetic parameters or external variables are introspection examples, not physical defaults, measurements or an audit pass.
`hierarchy describe` prints a readable tree with components, refinements, fault variants (benign ones named in the header), rules and assumption cards; `--observed` adds per-block mapped/review counts and `declared needs missing` (declared `required_variables` only) without solving or evaluating. Which inputs are really checkable only `evaluate` knows: `hierarchy run|evaluate|compare|variants` print the same tree with each block's verdict (`not checked: N inputs missing`).
`--json` keeps the full structure, native `supplied` parameters and `native_reads_with_defaults` access logs; `--mermaid` draws blocks and labeled connections. These are declarations, not validation evidence.

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
Under `hierarchy.refinement_rules`, select `block_id`, `score_threshold`, optional `trigger_diagnostic_keys` and `next_template_ids`; include `rationale` and the next required signals. Template ids refer to same-file blocks or files relative to the audit directory or its parent. Reports distinguish `block`, `file` and `planned`; a planned target is not built yet (the heated tank's `refine_envelope` is one) and becomes `block` or `file` once built; finding it never executes it. List next template ids only in `hierarchy.refinement_rules[].next_template_ids`; the retired block field is rejected. Inconsistent coarse/detail checks stay visible.

Component residuals belong to their owning block; connections between sibling blocks roll up to their nearest common ancestor, boundaries to the owning component. Unassigned residuals remain explicit.
`own_audit_pass` is local, `audit_pass` includes descendants, and `subtree_score` is the maximum own score in the subtree; local `score` still orders `top_blocks`.
`hierarchy.scoring.method` supports `max`, `rms`, `top_k_mean` (`top_k`) and `weighted_sum` (`diagnostic_key_weights`); role filters include active relations and exclude `post_check` by default.
`hierarchy.confidence` clips a heuristic base minus missing required-variable/parameter, no-residual and configured level penalties to its min/max; it is not probability.
Refinement rules may filter `trigger_roles`, `trigger_diagnostic_keys`, `confidence_min` and a `score_threshold` (default 1.0); recommendations retain next required variables/parameters and sort by descending priority, then trigger score.
`refinement_checks` compares checked coarse residuals with refining children: passing children plus a failed coarse check is inconsistent; a passing coarse check with a failed child is consistent. When coarse relations were consumed as producers or no scored coarse check is usable, `coarse_pass` and `consistent` are null with a reason.

## Observed snapshots and freshness

An observed file has `observation_name` and `variables` keyed by qualified names; optional `source_model` holds only model/tool/version/scenario/export-time context and never changes a verdict:

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

Without raw fields, `value` is already the SI value to check; conversion fields only record evidence.
Any recorded `conversion_factor`, `conversion_offset` or `conversion_note` (a factor of 1 and an offset of 0
included) is a conversion done outside the tool: the mapping ledger marks that row `conversion_unchecked`
(a warning; the run continues) unless the tool can check it against a reading in `external_signal`.
For every row, with or without raw fields, the tool looks for a reading, a number followed by a unit it
reads (`6 L/min`, `15 C`, or a transducer output such as `7.5 V`), anywhere in `external_signal`, converts
it to the model unit and compares it with the row's value. A reading of the model unit's quantity goes
through the unit table; on a row with `raw_value`, a reading of the raw unit's quantity is converted the
way `raw_value` was (so `raw_value: 6, raw_unit: L/s` through a density beside `6 L/min` disagrees):

- the reading is the whole `external_signal` (`6 kg/min`, `15 degC`): agreement counts as checked, and a
  value or recorded factor/offset that disagrees stops the run with
  `signal_reading_disagrees:<variable>` (exit 2), the same as a raw-value disagreement;
- the reading sits inside a longer text (`AI outlet temperature 33 C`): agreement counts as checked; a
  disagreement is marked `signal_reading_disagrees` and the run continues, because a label can name other
  numbers. Write the reading alone, or as `raw_value` and `raw_unit`, to have it enforced;
- a reading of another quantity that a property could link (`6 L/min` beside a kg/s value, or beside
  `raw_value: 6, raw_unit: kg/s`), or several readings in one text: marked `conversion_unchecked`.
  An agreeing reading leaves a transducer calibration unchecked.

A row that records nothing and names its signal only by a label (`AI heater power`) cannot be checked and is
not flagged. The ledger's `conversion_check` says why, in one sentence.

The tool reads a unit written with the table's symbols, joined by `/` or `*` (or `·`, `⋅`, or `.` between
two symbols) with `^n` powers, in the spellings it lists: `l`, `liter`, `litre` for `L`; `sec` for `s`;
`minute` for `min`; `hr` for `h`; `m3` for `m^3`; `per`, `a` or `an` between words for `/`; `LPM`, `rpm`;
`degC`, `°C`, `deg C` or `C` for Celsius; `degF`. A power may be written `min-1` or `min⁻¹`; a space joins two
symbols only when the second has a power (`L min^-1`; `L min` is not read); a unit in one pair of brackets
(`(L/min)`, `[L/min]`) is that unit. So `l/min`, `LPM`, `litres per minute`, `litres a minute`, `L min^-1`,
`L·min⁻¹`, `l.min-1`, `dm^3/min` and `kg/sec` are read as `L/min` and `kg/s`. A row whose value is in a unit the tool
reads but that is not the model's unit (`kW` for a W variable, `L/s` for a kg/s variable) stops the
evaluation with `observed_unit_not_model_unit:<variable>`: evaluation never converts.

For a hand-written snapshot, give both finite `raw_value` and nonblank `raw_unit`, plus the target `unit`,
and omit `value` rather than hand-calculating it. The loader converts once at ingestion, for snapshots and
series points alike; it never converts from `external_signal`:

- two units of one quantity (degC and K, kW and W, kg/min and kg/s, l/min and m^3/s): the table converts;
  a recorded factor or offset must agree with it exactly;
- two different quantities (L/min to kg/s): declare the property that links them once under
  `properties` and name it on the row with `conversion_property`. The tool multiplies or divides by it,
  whichever turns one quantity into the other, and refuses a pair the property cannot link. A row
  without `conversion_property` is refused with `unit_not_convertible:<variable>`, even when it records
  a factor: a cross-quantity factor written by hand is not checked and not used;
- a unit the tool cannot read (`lit/min`, `kmol/h`, `gallons/min`): refused with
  `unit_not_convertible:<variable>: the tool cannot read the unit ...`, because a recorded factor for it
  could not be checked; write the unit as the table does;
- a transducer output (`V`, `mV`, `A`, `mA`, `ohm`) mapped to a physical quantity: its calibration
  `conversion_factor`/`conversion_offset` is applied and the row is marked `conversion_unchecked`, since no
  table can know a sensor's calibration.

```yaml
properties:
  water_density: {value: 1.0, unit: kg/L, source: "given in the question"}
variables:
  heater.m_dot_kg_s: {raw_value: 6, raw_unit: L/min, unit: kg/s, conversion_property: water_density}
```

If `value` or a `conversion_factor` is also present on a computed row, it must agree with the
tool's conversion within `RAW_VALUE_REL_TOL = 5e-5` relative tolerance. This admits the rounded factor
0.016667 for 6 L/min and rejects a 60-fold error; the tool's own factor is the one applied.
A disagreement refuses the run with exit 2 and `observed_value_disagrees_with_conversion:<variable>`;
a pair that cannot be converted uses `unit_not_convertible:<variable>`. Incomplete pairs remain input
validation errors. Conversion results must be finite. A declared property needs a finite positive
value and a unit from the table; a density above that of the densest material (osmium, 22.59 g/cm^3) is
refused with `implausible_property`, so a 60 kg/L water density stops the run. A wrong but possible
property (2 kg/L for water) is still the AI's number, visible in the snapshot and the ledger.

The mapping ledger adds `raw_conversion`, for example `6 L/min x 0.0166667 (water_density 1 kg/L) -> 0.1 kg/s`.
It records the accepted original input conversion; intentional counterfactual variants retain that
provenance alongside their counterfactual source, rather than claiming a new measured conversion.
Evaluation never converts. A series file (and `testfile series` output) may carry raw rows and a
series-level `properties`; `load_observed_series` converts each point with the same rules. Direct Python
construction needs numeric SI rows without raw fields, or rows returned by the loader; unresolved raw rows
are refused before use.
Record mapping uncertainty and `review_required` honestly.
`stale_when` declares reconfirmation conditions; when one occurs, set `mapping_status: stale`. Do not present old mappings as current evidence.

## Local resolution of observed checks

`hierarchy evaluate` and `hierarchy compare` report `resolution`: a local first-order
estimate at the observed working point, using the same residual builder without a
reference solve. For each observed variable owned by a checked block, take the smallest
`audit_threshold / abs(d(normalized residual) / d(variable))` among that block's independent
checked residuals. Derived values are recomputed for each perturbation; producing relations
are not reused as independent checks. This is a full threshold-sized error, not remaining
headroom after the current residual. It is not a global detection guarantee for nonlinear physics.
For example, the shower half-flow case reports about 8 K even though its current normalized
mixing residual is already 0.5625; an explicit tighter scale reports about 0.2 K at full flow.

The JSON entry is `{value, unit, residual, default_scale}`; values use the variable's own
registry unit and name the winning checked residual. A null entry prints `<variable> unchecked`:
no usable finite local sensitivity was established for that block. It does not replace the
block's existing audit verdict. A true `default_scale` marks `(default scale)` because at least
one contributing module scale input was omitted; false means those scale inputs were supplied.
If the scale source cannot be established, the numeric estimate remains, with `default_scale: null`
and `(scale source unavailable)`. This explicit unknown also covers custom or compound scale
implementations that the native scale-source check cannot classify; it never becomes a false
claim that the variable itself was unchecked.

The tree prints one line per checked block in tree order, after `hint:` and before `mapping:`,
using two significant digits. A checked block without its own observed variables says
`resolution: <block> no observed variables`. Resolution never changes the audit threshold,
module defaults, observations or verdict. Choose scales as tolerable errors in each residual's
unit and read this estimate before calling a numerical answer checked.

A relation refuses a value outside its domain by raising `DomainRefusal` (from
`physicsguard.modules`, a kind of `ValueError`); every native range check does, and so do the
bounds checks of a variable declaration. The hint search, the scale-source replay and the resolution
samples skip exactly that refusal: a refused trial gives no hint, no scale claim or no sample. Any
other error inside them, a `KeyError`, a `ZeroDivisionError` or a plain `ValueError` from custom code
included, stops the command with exit 2 and its text. The bounded root search below also treats a
division by zero or an overflow at one of its sample points as no unique root. A custom module that
refuses values raises `DomainRefusal`.

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
To start in a domain, copy the nearest tree from the PhysicsGuard repository: `coolant_loop`, `fuel_cell_system`, `wastewater_treatment`, `building_hvac`, `data_center_electronics_cooling`, `distribution_power_der`, `pid_actuator_loop`, `process_industry`, `renewable_microgrid`, `stormwater_sewer_drainage`.
