# Domain Starter Packs

PhysicsGuard domain coverage should grow through low-fidelity audit starter packs before detailed component models. A starter pack is a small set of runnable hierarchy templates, mapped-signal declarations, aggregate balances, refinement rules, and explicit assumptions for one engineering domain.

Starter packs are not solver replacements. They should help an AI agent locate suspicious signal mappings, missing terms, unit mistakes, broken balances, and unreasonable accounting before any detailed model is proposed.

## Start With A Connected Tree

A starter pack uses one `tree.yaml` and one paired `nominal_observed.yaml`, plus
only necessary data files. The root holds only real system-level relations;
when there are none the tree is a flat partition (the header says "flat
partition: no coarse level") and children carry no `refines`. For coarse to fine,
read `coolant_loop` and `heated_tank`: finer blocks live in the same file and
`refines` points only to coarse components owned by the immediate parent. Connections share the same physical quantities. Rules name
real blocks in that tree, faults and benign perturbations are `fault_variants`,
and every supplied snapshot signal keeps its SI unit, external name and source.
Each pack has at least two faults that fail different blocks (so `hierarchy
variants --pairs` has pairs to separate) and one benign measurement error sized to
0.1-0.5 of a checked residual's scale, which must stay neutral.
Every starter pack below uses this form; no separate level or conflict copies remain.

| Pack | Start here | Paired snapshot | coarse level |
| --- | --- | --- | --- |
| Coolant loop | `examples/hierarchical/coolant_loop/tree.yaml` | `examples/hierarchical/coolant_loop/nominal_observed.yaml` | real relations |
| Fuel-cell system | `examples/hierarchical/fuel_cell_system/tree.yaml` | `examples/hierarchical/fuel_cell_system/nominal_observed.yaml` | real relations |
| Building HVAC | `examples/hierarchical/building_hvac/tree.yaml` | `examples/hierarchical/building_hvac/nominal_observed.yaml` | real relations |

Use these four entrypoints (replace `coolant_loop` with either other pack):

```sh
python -m physicsguard.cli hierarchy describe examples/hierarchical/coolant_loop/tree.yaml
python -m physicsguard.cli hierarchy run examples/hierarchical/coolant_loop/tree.yaml
python -m physicsguard.cli hierarchy evaluate examples/hierarchical/coolant_loop/tree.yaml examples/hierarchical/coolant_loop/nominal_observed.yaml
python -m physicsguard.cli hierarchy variants examples/hierarchical/coolant_loop/tree.yaml examples/hierarchical/coolant_loop/nominal_observed.yaml
```

`describe` inspects the declared topology without solving; `run`, `evaluate` and
`variants` print the same tree with each block's verdict (add `--json` for the full
report). `run` solves a
low-fidelity reference; its generated working point is synthetic, not a measured
plant record. The paired snapshots retain a declared bench-like measurement
subset with SI units and mapping evidence, not the full solved vector. `evaluate`
uses those supplied values without moving them; derived intermediates remain
separate from independent checked residuals. These snapshots demonstrate a
bounded workflow, not empirical validation or commercial-solver equivalence.

Read each tree's `fault_variants`: named faults preserve the old conflict cases'
intended diagnostic direction, while a benign variant checks that a small allowed
perturbation stays neutral. Detection must come from actual own checked residuals
in the expected blocks, not from a filename, inherited failure or a producing
relation. A passing nominal audit alone does not establish fault discrimination.

### Coolant loop: one thermal and flow boundary

The connected coolant tree uses a synthetic 10 kW duty and 1 kg/s total coolant
flow, with a 310 K stack inlet and 320 K outlet. A half-flow radiator branch and
hot bypass recombine at a three-way mixer; flow, temperatures and thermal duties
are shared across the coarse balance and the stack, pump, radiator, inventory and
valve blocks. The stack, radiator and inventory children refine the root's own
`thermal_balance`. Constant fluid properties, prescribed pump efficiency and
valve split, and omission of pump heating are explicit assumptions. This is not a
hydraulic-network or heat-exchanger-map simulation. The paired snapshot selects
13 of the reference solution's 27 variables: separate input/rejected heat meters,
main flow, coolant/air temperatures, pump pressures and shaft power, and inventory
temperatures. Coarse heat-rejection and radiator-duty faults retain the two old
conflict directions; `small_shaft_power_shift` adds 4.73 W to the shaft-power reading
as a benign measurement perturbation. These are synthetic meter projections,
with proposed mappings that still need review for any real plant.

### Fuel-cell system: reaction energy, air and cooling

The fuel-cell tree connects root `fc_system` to the stack, cathode air path, anode
hydrogen path, coolant loop, high-voltage bus and controls. The air and cooling
branches each expose four Level 2 blocks. Explicit `refines` links name only
coarse components owned by the immediate parent; auxiliary blocks are not
artificially marked as refinements. Shared energy, electrical, molar-flow and
coolant quantities are joined by identity connections.

The synthetic reference uses 50 kW of reacted-hydrogen equivalent energy,
23 kW net electrical output, 5 kW auxiliary consumption and 22 kW stack heat.
An explicit 1.25 V LHV-equivalent assumption defines the reaction-energy basis;
the larger hydrogen inlet feed at stoichiometry 1.5 is not all reacted fuel.
The boundary declares dry-air cathode accounting, prescribed humidification,
a simple exhaust-valve density and auxiliary dissipation outside the coolant
thermal balance. It does not model membrane transport, detailed electrochemistry
or gas pressure dynamics. The old self-canceling water-flow proxy is not copied
into this connected tree; the separate legacy files are removed.

The paired snapshot selects 35 of 74 reference variables: reacted-energy and
power meters, stack voltage/current, air and hydrogen feed rates, compressor
pressure/temperature/shaft measurements, intercooler and humidity readings,
valve setting, and coolant temperatures, flow, pressures and heat meters.
Unmeasured reaction rates, repeated ports, efficiency states and intermediates
are omitted. The two faults are `hydrogen_power_underread` (the reacted-energy
channel) and `cathode_air_underfeed` (air feed); `net_power_rounding` adds a benign
300 W net-power perturbation (0.3 of the 1 kW balance scale). Keep any remaining `missing_required_variables` and
`unchecked_residuals` visible: nominal `audit_pass` does not mean every relation
was evaluable or that proposed meter mappings have been verified on a real plant.

### Building HVAC: shared plant and campus metering

The HVAC tree joins the coarse plant balance to zone loads, the chilled-water
loop, chiller/condenser, air handler, plant electrical and district-interface
blocks. Its synthetic point accounts for 25 kW of zone load, 1 kW of distribution
heat gain, 26 kW of evaporator cooling, 8 kW of chiller input and 34 kW of condenser
rejection. The district interface meters that same campus chilled-water link;
it is not a second cooling source. The paired snapshot retains heat-flow and
electrical meters (15 of 32 reference variables), including an independent
air-side fan-heat meter, while omitting the root-level coarse signals, COP and district
bookkeeping aliases.
Direct child `refines` links name the root's zone, chiller and electrical
balances. Fan heat and the scope of steady positive-power accounting are explicit;
no building dynamics or chiller-performance map is recovered. The
`unmet_cooling_load` fault reduces measured coil cooling from 25 kW to 22 kW.
The benign `fan_auxiliary_plus_50W` changes fan power, feeder power and independently
metered fan heat together by 50 W so both electrical and heat accounting stay
closed; it is not an isolated faulty meter reading.
`chilled_water_distribution_gain_within_tolerance` offsets one heat meter by 30 W
(0.3 of its residual scale) and must stay neutral; `chilled_water_pump_power_sensor_gain`
is a second fault on the plant electrical balance.

## Cross-Domain Pattern

Each starter pack should include:

- Coarse root balances in `tree.yaml`: mass, species, power, heat, inventory, or cost-of-flow checks.
- Finer subsystem blocks in the same tree, with local balances, parent-owned `refines` links and real block recommendations.
- Mapped signal declarations for external values using `MappedSignalModule`.
- A measured-signal nominal subset and declared fault/benign variants rather than copied conflict files.
- Required next signals and parameters for refinement.
- Assumptions, limitations, SI units, and diagnostic keys in metadata or module docs.

Use existing aggregate modules whenever the relation can be expressed as a balance over mapped variables. Add a new physical module only when the relation is explicit, low-fidelity, documented, tested, and reusable across examples.

## Priority Map

| Priority | Starter pack | First useful checks | Avoid at first |
| --- | --- | --- | --- |
| 0 | Cross-domain audit primitives | explicit unit conversion, sensor scale/offset, boundary-loss accounting, sample alignment | Hidden unit tables or automatic assumptions |
| 1 | Water and wastewater treatment | COD/N/TSS/DO accounting, sludge recycle, clarifier solids, aeration energy | Full ASM kinetics or calibration |
| 2 | Renewable energy, storage, and microgrids | PV/wind power envelopes, battery SOC, generation-load-storage balance | Full dispatch optimization |
| 3 | Building HVAC and district energy | heat load, chiller/heat-pump COP, plant loop balances, pump/fan power | Full EnergyPlus-style building simulation |
| 4 | Distribution power and DER | P/Q/S, power factor, feeder balance, line losses, voltage range | Full load-flow replacement |
| 5 | Process industry unit operations | reactor conversion, separator split, heat exchanger, pump/compressor/valve sanity | Detailed property packages |
| 6 | Stormwater, sewer, and drainage | rainfall-runoff volume, storage/outflow, pump station balance, pollutant load | Full SWMM replacement |
| 7 | Industrial utilities | steam, condensate, compressed air, refrigeration, cooling water | Plant-wide optimizer |
| 8 | Data centers and electronics cooling | IT power-to-heat, PUE, rack/room/cooling-loop balances | CFD or detailed airflow |
| 9 | Mobility extensions | rail, marine, aviation, off-road hydraulics, charging infrastructure | High-fidelity vehicle simulators |
| 10 | Agriculture, food, and bioprocess | greenhouse heat/water/CO2, irrigation, fermentation, drying, cold chain | Detailed biological growth models |
| 11 | Oil/gas pipeline and storage | pipeline mass balance, compression power, tank inventory | Multiphase pipeline simulation |
| 12 | Water supply networks | source, pump, distribution leakage, storage inventory | EPANET-grade hydraulic replacement |
| 13 | Manufacturing thermal process lines | furnace heat, line power, material mass, exhaust loss | Detailed plant scheduling or CFD |
| 14 | Mining and metallurgy | ore mass, milling power, slurry water, concentrate/tailings balance | Grinding kinetics or flotation chemistry |
| 15 | Combustion boiler and furnace | fuel/air/flue gas, heat release, draft fan power | Combustion kinetics or emissions chemistry |
| 16 | Geothermal underground wells | brine production/reinjection, heat extraction, pump power | Reservoir simulation |
| 17 | Cold-chain logistics | warehouse/truck refrigeration heat and fleet energy | Detailed route or refrigeration-cycle simulation |
| 18 | Robotics and mechatronics | DC bus, joint power/loss, actuator air or fluid supply, thermal rejection | Multibody dynamics or servo-drive maps |
| 19 | Aerospace and satellite thermal | spacecraft power, radiator heat, battery SOC, propellant mass | Orbital thermal finite-element models |
| 20 | Medical and bioprocess equipment | ventilator flow, dialysis mass, sterilizer heat, incubator heat | Patient physiology or detailed biokinetics |

## Water And Wastewater Starter Pack

The first starter pack is under:

```text
examples/hierarchical/wastewater_treatment/
```

`tree.yaml` holds blocks `wastewater_plant`, `biological_reactor`, `secondary_clarifier`, `sludge_recycle`, `aeration_energy`. Fault variants: `global_cod_loss`, `reactor_cod_loss`; benign variants: `unit_flow_rounding`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

These templates intentionally do not implement ASM1, ASM2d, or ASM3 kinetics. They expose an ASM-style audit boundary by asking for consistent COD, nitrogen, oxygen, sludge, and flow mappings. If the Level 0 or Level 1 balances fail, the recommended refinement is to request more mapped signals before adding any biochemical kinetics.

## MappedSignalModule

`MappedSignalModule` declares one externally mapped variable and adds no residual equation. It is useful when a hierarchy template needs variables from an external simulator, spreadsheet, plant historian, or hand-prepared snapshot.

Use it for values such as:

- `influent_flow.value`
- `cod_in.value`
- `clarifier_tss_effluent.value`
- `grid_power.value`

The module does not assert that the value is correct or physically meaningful. It only gives aggregate and component audit modules a typed, bounded, SI-unit variable to reference.

## Criteria For Adding A Real Module

Promote a repeated template relation into a module only when:

- the residual equation is explicit and documented;
- SI units and residual scale are clear;
- bounds and initial guesses are finite;
- assumptions and validity range are documented;
- module examples include a clean case and a contradictory-boundary `conflict_*.yaml` fixture for its tests (an audit tree's known-bad cases are its `fault_variants`);
- focused tests cover zero residual, nonzero residual, validation errors, metadata, and YAML usage.

Do not add detailed models, hidden unit conversion tables, empirical correlations, or commercial-tool-equivalent behavior as part of a starter pack.

## Expanded Coverage Packs

Starter trees are maintained directly; the one-time generator and copied level/conflict files are removed. Each pack has one connected tree, a nominal snapshot and declared fault/benign variants. These are starter packs, not detailed component libraries. They should be used to test signal mapping, units, accounting boundaries, and first-pass physical plausibility before adding domain-specific modules.

| Pack | Path | Included templates | First useful checks | coarse level |
| --- | --- | --- | --- | --- |
| Cross-domain audit primitives | `examples/hierarchical/cross_domain_audit_primitives/` | `tree.yaml`, `tree.yaml`, `tree.yaml` | unit conversion, sensor scale/offset, boundary loss, sample delay | none |
| Oil/gas pipeline and storage | `examples/hierarchical/oil_gas_pipeline_storage/` | `tree.yaml`, `tree.yaml`, `tree.yaml` | pipeline mass closure, compression power, tank inventory | none |
| Water supply network | `examples/hierarchical/water_supply_network/` | `tree.yaml`, `tree.yaml`, `tree.yaml` | source flow, pump power, leakage, reservoir storage | none |
| Manufacturing thermal process | `examples/hierarchical/manufacturing_thermal_process/` | `tree.yaml`, `tree.yaml`, `tree.yaml` | furnace heat, line power, material flow, exhaust loss | none |
| Mining and metallurgy | `examples/hierarchical/mining_metallurgy/` | `tree.yaml`, `tree.yaml`, `tree.yaml` | ore split, milling power, slurry water, tailings accounting | none |
| Combustion boiler and furnace | `examples/hierarchical/combustion_boiler_furnace/` | `tree.yaml`, `tree.yaml`, `tree.yaml` | fuel/air/flue mass, useful heat, stack loss, draft fan power | none |
| Geothermal underground wells | `examples/hierarchical/geothermal_underground_wells/` | `tree.yaml`, `tree.yaml`, `tree.yaml` | brine production/reinjection, heat extraction, pump power | none |
| Cold-chain logistics | `examples/hierarchical/cold_chain_logistics/` | `tree.yaml`, `tree.yaml`, `tree.yaml` | warehouse/truck heat loads, refrigeration power, fleet charging | none |
| Robotics and mechatronics | `examples/hierarchical/robotics_mechatronics/` | `tree.yaml`, `tree.yaml`, `tree.yaml` | DC bus accounting, joint losses, drive heat, actuator supply | none |
| Aerospace and satellite thermal | `examples/hierarchical/aerospace_satellite_thermal/` | `tree.yaml`, `tree.yaml`, `tree.yaml` | spacecraft power, battery SOC, radiator heat, propellant mass | none |
| Medical and bioprocess equipment | `examples/hierarchical/medical_bioprocess_equipment/` | `tree.yaml`, `tree.yaml`, `tree.yaml` | ventilator flow, dialysis mass, sterilizer heat, incubator thermal load | none |

## Flagship Level 2 Entrypoints

Level 2 templates should be added only after the Level 0 and Level 1 starter packs prove that the mapped signals, sign conventions, and accounting boundaries are stable. Good next candidates are:

- Wastewater treatment: ASM-style boundary checks around COD, nitrogen, oxygen, sludge recycle, and clarifier solids, without implementing ASM kinetics by default.
- Renewable microgrid: PV, wind, inverter, battery, load, curtailment, and import/export subblocks before any dispatch optimization.
- Building HVAC, industrial utilities, and data centers: chiller, pump, fan, refrigeration, coolant-loop, and rack/room thermal subblocks before equipment maps.
- Process, oil/gas, and manufacturing: reactor/separator/utility, pipeline/compression/storage, furnace/line/material subblocks before property packages or plant schedulers.
- Water, drainage, geothermal, mining, and cold chain: network or inventory splits before hydraulic, reservoir, grinding, or route simulation.
- Robotics, aerospace, and medical equipment: power-chain, actuator, thermal, storage, and flow subblocks before multibody dynamics, orbital thermal FEA, or patient physiology.

## Renewable Microgrid Starter Pack

The second starter pack is under:

```text
examples/hierarchical/renewable_microgrid/
```

`tree.yaml` holds blocks `renewable_microgrid`, `pv_system`, `wind_system`, `battery_storage`, `grid_interconnect`, `load_dispatch`. Fault variants: `unserved_load`, `battery_capacity_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

These templates intentionally do not implement a full PV performance model, wind turbine aerodynamics, AC power-flow, or dispatch optimization. They check whether mapped signals close at a snapshot before asking for finer signals such as module temperature, inverter DC voltage/current, battery energy previous/current, or import/export metering conventions.

## Building HVAC And District Energy Starter Pack

The third starter pack is under:

```text
examples/hierarchical/building_hvac/
```

`tree.yaml` holds blocks `building_hvac`, `zone_loads`, `chilled_water_loop`, `chiller_condenser`, `air_handler`, `plant_electrical`, `district_energy_interface`. Fault variants: `unmet_cooling_load`, `chilled_water_pump_power_sensor_gain`; benign variants: `fan_auxiliary_plus_50W`, `chilled_water_distribution_gain_within_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

These templates intentionally do not implement EnergyPlus-style building simulation, chiller or cooling-tower performance maps, detailed air-loop psychrometrics, hydronic network hydraulics, or district-energy network simulation. They check whether mapped snapshot signals close before asking for finer signals such as zone air states, chilled-water temperatures, condenser-water temperatures, COP basis, auxiliary power grouping, or district metering conventions.

## Distribution Power And DER Starter Pack

The fourth starter pack is under:

```text
examples/hierarchical/distribution_power_der/
```

`tree.yaml` holds blocks `distribution_power_der`, `substation_transformer`, `feeder_section_a`, `feeder_section_b`, `der_interface`, `power_quality_voltage`. Fault variants: `missing_line_loss`, `battery_discharge_active_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

These templates intentionally do not implement AC load flow, phase-unbalanced distribution simulation, impedance-based voltage drop, protection coordination, or detailed inverter controls. They check whether mapped snapshot signals close before asking for finer signals such as per-section power flow, per-phase P/Q/S, voltage bases, section current, line impedance, inverter reactive-power convention, or DER import/export metering basis.

## Process Industry Unit Operations Starter Pack

The fifth starter pack is under:

```text
examples/hierarchical/process_industry/
```

`tree.yaml` holds blocks `process_industry`, `reactor_conversion`, `separator_split`, `heat_exchange_utility`, `rotating_equipment`. Fault variants: `missing_cooling_duty`, `agitator_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

These templates intentionally do not implement reaction kinetics, detailed separator phase equilibrium, process property packages, heat-exchanger rating, pump/compressor maps, valve characteristics, or full process-flow simulation. They check whether mapped snapshot signals close before asking for finer signals such as stream compositions, conversion basis, split basis, heat-duty sign convention, temperature states, pressure states, and utility-meter grouping.

## Stormwater, Sewer, And Drainage Starter Pack

The sixth starter pack is under:

```text
examples/hierarchical/stormwater_sewer_drainage/
```

`tree.yaml` holds blocks `stormwater_sewer_drainage`, `catchment_runoff`, `sewer_conveyance`, `detention_storage`, `pump_station`, `pollutant_load`. Fault variants: `unreported_overflow`, `catchment_surface_storage_rate_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

These templates intentionally do not implement a SWMM replacement, rainfall-runoff response model, Saint-Venant hydraulic routing, pump curves, detention routing, sediment transport, or water-quality kinetics. They check whether mapped snapshot signals close before asking for finer signals such as runoff partition, inlet capture, overflow boundary, storage sign convention, pump meter grouping, wet-well level basis, or pollutant load basis.

## Industrial Utilities Starter Pack

The seventh starter pack is under:

```text
examples/hierarchical/industrial_utilities/
```

`tree.yaml` holds blocks `industrial_utilities`, `steam_condensate`, `compressed_air`, `refrigeration_chilled_water`, `cooling_water`, `utility_power`. Fault variants: `missing_air_leak`, `boiler_auxiliary_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

These templates intentionally do not implement plant-wide utility optimization, boiler maps, compressor maps, chiller maps, cooling-tower performance, steam-network hydraulics, or compressed-air network hydraulics. They check whether mapped snapshot signals close before asking for finer signals such as steam metering boundary, condensate return basis, air leak boundary, chiller power grouping, cooling-water heat-rejection boundary, or makeup/blowdown basis.

## Data Center And Electronics Cooling Starter Pack

The eighth implemented starter pack is under:

```text
examples/hierarchical/data_center_electronics_cooling/
```

`tree.yaml` holds blocks `data_center_electronics_cooling`, `it_load_rack_heat`, `facility_power_chain`, `room_air_cooling`, `coolant_loop`, `cooling_plant_efficiency`. Fault variants: `underreported_cooling_capacity`, `coolant_heat_pickup_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

These templates intentionally do not implement CFD, airflow-network simulation, chip/package thermal models, UPS/PDU equipment models, chiller/CDU/economizer maps, or detailed cooling-control optimization. They check whether mapped snapshot signals close before asking for finer signals such as IT power meter boundary, PUE meter grouping, room heat-gain boundary, cooling power grouping, coolant heat boundary, or temperature basis.

## Mobility Extensions Starter Pack

The ninth implemented starter pack is under:

```text
examples/hierarchical/mobility_extensions/
```

`tree.yaml` holds blocks `mobility_extensions`, `charging_infrastructure`, `rail_traction`, `marine_propulsion`, `aviation_power`, `offroad_hydraulics`. Fault variants: `missing_charger_loss`, `aircraft_auxiliary_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

These templates intentionally do not implement vehicle dynamics, route optimization, rail-network load flow, ship resistance, flight dynamics, propulsion maps, battery electrochemistry, charger curves, or hydraulic valve/pump maps. They check whether mapped snapshot signals close before asking for finer signals such as charger meter boundary, rail meter grouping, marine/aviation power basis, hydraulic power boundary, SOC basis, speed basis, or hydraulic pressure basis.

## Agriculture, Food, And Bioprocess Starter Pack

The tenth implemented starter pack is under:

```text
examples/hierarchical/agriculture_food_bioprocess/
```

`tree.yaml` holds blocks `agriculture_food_bioprocess`, `irrigation_crop_water`, `greenhouse_climate`, `greenhouse_co2`, `fermentation_bioreactor`, `drying_process`, `cold_chain_storage`. Fault variants: `missing_irrigation_drainage`, `co2_plant_uptake_molar_flow_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

These templates intentionally do not implement crop-growth models, photosynthesis kinetics, microbial kinetics, drying-rate models, refrigeration maps, detailed food-process simulation, or greenhouse climate-control optimization. They check whether mapped snapshot signals close before asking for finer signals such as greenhouse heat boundary, CO2 balance basis, irrigation drainage boundary, fermentation mass/yield basis, dryer water/exhaust basis, or cold-chain heat-gain boundary.

## Heated-Tank Reference Example

`examples/hierarchical/heated_tank/` contains a synthetic non-SI CSV, a coarse
volume/energy audit and a six-block coupled hierarchy with an explicit heater
nameplate-efficiency assumption. `sim_tank.py` exposes `main(argv=None)` and regenerates the CSV only when called; importing it does not generate data;
`python -m physicsguard.cli testfile snapshot tank_run_contract.yaml --row 70 --out measured_k70.yaml` writes the mapped SI snapshot. Evaluate the same `heated_tank.yaml` tree with either the full snapshot or the nine-channel `sparse_measured_k70.yaml`; sparse command power remains a low-confidence heat-input proxy. The tree owns coarse tank energy and volume relations and refines them inside the same file. Its explicit nameplate signal constraint repeats the declared efficiency assumption, adds no measurement or independent physical evidence, and lets downstream heat closure remain an independent check. Reference initial guesses describe a physically consistent nominal state; observed snapshots retain their measured values.
The heater current halves at 600 s while its command stays unchanged; inflow changes
at 900 s. This is a low-fidelity diagnostic reference. Measurements contain no
hand-computed connected endpoints or intermediate heat flows.

For the full heated-tank time series, run `testfile series tank_run_contract.yaml
--out tank_series.yaml`, then `validation run validation_plan.yaml` from the
example directory. The compact report identifies the heater failure interval
starting at 600 seconds, without listing sixty repeated point failures.

## Current Starter Tree Catalog

### Aerospace Satellite Thermal

`examples/hierarchical/aerospace_satellite_thermal/`: `tree.yaml` holds blocks `aerospace_satellite_thermal`, `satellite_power_accounting`, `satellite_thermal_accounting`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Agriculture Food Bioprocess

`examples/hierarchical/agriculture_food_bioprocess/`: `tree.yaml` holds blocks `agriculture_food_bioprocess`, `irrigation_crop_water`, `greenhouse_climate`, `greenhouse_co2`, `fermentation_bioreactor`, `drying_process`, `cold_chain_storage`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Building Hvac

`examples/hierarchical/building_hvac/`: `tree.yaml` holds blocks `building_hvac`, `zone_loads`, `chilled_water_loop`, `chiller_condenser`, `air_handler`, `plant_electrical`, `district_energy_interface`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Cold Chain Logistics

`examples/hierarchical/cold_chain_logistics/`: `tree.yaml` holds blocks `cold_chain_logistics`, `warehouse_thermal_accounting`, `truck_cooling_accounting`, `fleet_power_accounting`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Combustion Boiler Furnace

`examples/hierarchical/combustion_boiler_furnace/`: `tree.yaml` holds blocks `combustion_boiler_furnace`, `boiler_heat_accounting`, `air_flue_mass_accounting`, `draft_fan_power`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Coolant Loop

`examples/hierarchical/coolant_loop/`: `tree.yaml` holds blocks `coolant_loop`, `stack_heat_interface`, `pump`, `radiator`, `thermal_mass`, `bypass_or_valve`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Cross Domain Audit Primitives

`examples/hierarchical/cross_domain_audit_primitives/`: `tree.yaml` holds blocks `cross_domain_audit_primitives`, `explicit_unit_conversion`, `sensor_calibration`, `boundary_loss_accounting`, `time_alignment`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Data Center Electronics Cooling

`examples/hierarchical/data_center_electronics_cooling/`: `tree.yaml` holds blocks `data_center_electronics_cooling`, `it_load_rack_heat`, `facility_power_chain`, `room_air_cooling`, `coolant_loop`, `cooling_plant_efficiency`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Distribution Power Der

`examples/hierarchical/distribution_power_der/`: `tree.yaml` holds blocks `distribution_power_der`, `substation_transformer`, `feeder_section_a`, `feeder_section_b`, `der_interface`, `power_quality_voltage`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Fuel Cell System

`examples/hierarchical/fuel_cell_system/`: `tree.yaml` holds blocks `fc_system`, `stack`, `cathode_air_path`, `anode_hydrogen_path`, `coolant_loop`, `hv_system`, `controls`, `compressor`, `intercooler`, `humidifier`, `exhaust_valve`, `coolant_pump`, `radiator`, `thermal_mass`, `bypass_or_valve`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Geothermal Underground Wells

`examples/hierarchical/geothermal_underground_wells/`: `tree.yaml` holds blocks `geothermal_underground_wells`, `well_mass_accounting`, `geothermal_heat_accounting`, `reinjection_pump_power`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Industrial Utilities

`examples/hierarchical/industrial_utilities/`: `tree.yaml` holds blocks `industrial_utilities`, `steam_condensate`, `compressed_air`, `refrigeration_chilled_water`, `cooling_water`, `utility_power`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Manufacturing Thermal Process

`examples/hierarchical/manufacturing_thermal_process/`: `tree.yaml` holds blocks `manufacturing_thermal_process`, `furnace_heat_accounting`, `production_line_power`, `material_yield_accounting`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Medical Bioprocess Equipment

`examples/hierarchical/medical_bioprocess_equipment/`: `tree.yaml` holds blocks `medical_bioprocess_equipment`, `ventilator_flow_accounting`, `dialysis_fluid_accounting`, `sterilizer_incubator_thermal`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Mining Metallurgy

`examples/hierarchical/mining_metallurgy/`: `tree.yaml` holds blocks `mining_metallurgy`, `ore_mass_accounting`, `mill_power_accounting`, `slurry_water_accounting`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Mobility Extensions

`examples/hierarchical/mobility_extensions/`: `tree.yaml` holds blocks `mobility_extensions`, `charging_infrastructure`, `rail_traction`, `marine_propulsion`, `aviation_power`, `offroad_hydraulics`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Oil Gas Pipeline Storage

`examples/hierarchical/oil_gas_pipeline_storage/`: `tree.yaml` holds blocks `oil_gas_pipeline_storage`, `pipeline_compression`, `pipeline_mass_accounting`, `terminal_storage_transfer`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Pid Actuator Loop

`examples/hierarchical/pid_actuator_loop/`: `tree.yaml` holds blocks `control_loop`, `controller`, `actuator`, `sensor`, `command_position`, `feedback_position`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Process Industry

`examples/hierarchical/process_industry/`: `tree.yaml` holds blocks `process_industry`, `reactor_conversion`, `separator_split`, `heat_exchange_utility`, `rotating_equipment`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Renewable Microgrid

`examples/hierarchical/renewable_microgrid/`: `tree.yaml` holds blocks `renewable_microgrid`, `pv_system`, `wind_system`, `battery_storage`, `grid_interconnect`, `load_dispatch`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Robotics Mechatronics

`examples/hierarchical/robotics_mechatronics/`: `tree.yaml` holds blocks `robotics_mechatronics`, `robot_power_chain`, `joint_thermal_accounting`, `pneumatic_actuator_accounting`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Stormwater Sewer Drainage

`examples/hierarchical/stormwater_sewer_drainage/`: `tree.yaml` holds blocks `stormwater_sewer_drainage`, `catchment_runoff`, `sewer_conveyance`, `detention_storage`, `pump_station`, `pollutant_load`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Wastewater Treatment

`examples/hierarchical/wastewater_treatment/`: `tree.yaml` holds blocks `wastewater_plant`, `biological_reactor`, `secondary_clarifier`, `sludge_recycle`, `aeration_energy`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

### Water Supply Network

`examples/hierarchical/water_supply_network/`: `tree.yaml` holds blocks `water_supply_network`, `distribution_water_accounting`, `pump_station_power`. Fault variants: `missing_radiator_heat`, `avionics_power_sensor_gain`; benign variants: `within_original_tolerance`. Its paired `nominal_observed.yaml` contains the supplied SI signals.

The utilities tree uses its original fine operating point: supplied air is 5 kg/s,
production plus instrument demand is 4.375 kg/s, and leakage is 0.625 kg/s.
The separate older coarse point (4.5 demand / 0.5 leakage) is not mixed into it.
Stormwater keeps gross catchment runoff at 280 and conveyance at 240; explicit
storage accounting distinguishes them. Its detention boundary is independently
60 = 50 + 5 + 5 and is refined only by its own matching quantities.
The wastewater tree retains independent global budgets and separately scoped
reactor/clarifier/recycle/blower records. Child links check same-unit parent
books; passing unit checks do not validate a reconciled whole-plant point.
PID signals distinguish pre-step command/measurement from post-step actuator
and feedback positions; no instantaneous plant dynamics are invented.
