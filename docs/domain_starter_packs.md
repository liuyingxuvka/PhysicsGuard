# Domain Starter Packs

PhysicsGuard domain coverage should grow through low-fidelity audit starter packs before detailed component models. A starter pack is a small set of runnable hierarchy templates, mapped-signal declarations, aggregate balances, refinement rules, and explicit assumptions for one engineering domain.

Starter packs are not solver replacements. They should help an AI agent locate suspicious signal mappings, missing terms, unit mistakes, broken balances, and unreasonable accounting before any detailed model is proposed.

## Start With A Connected Tree

For these three packs, read `tree.yaml` first and use its paired
`nominal_observed.yaml`. Each tree keeps the coarse root balance and its finer
subsystems in one file at one declared operating point. Connections bind shared
physical quantities; `refines` links a child to coarse components owned directly
by its parent. The older `level_*` and `conflict_*` files remain available as
separate examples and regression inputs; do not combine their independently
chosen operating points into a connected system.

| Pack | Start here | Paired snapshot |
| --- | --- | --- |
| Coolant loop | `examples/hierarchical/coolant_loop/tree.yaml` | `examples/hierarchical/coolant_loop/nominal_observed.yaml` |
| Fuel-cell system | `examples/hierarchical/fuel_cell_system/tree.yaml` | `examples/hierarchical/fuel_cell_system/nominal_observed.yaml` |
| Building HVAC | `examples/hierarchical/building_hvac/tree.yaml` | `examples/hierarchical/building_hvac/nominal_observed.yaml` |

Use these four entrypoints (replace `coolant_loop` with either other pack):

```sh
python -m physicsguard.cli hierarchy describe examples/hierarchical/coolant_loop/tree.yaml
python -m physicsguard.cli hierarchy run examples/hierarchical/coolant_loop/tree.yaml
python -m physicsguard.cli hierarchy evaluate examples/hierarchical/coolant_loop/tree.yaml examples/hierarchical/coolant_loop/nominal_observed.yaml
python -m physicsguard.cli task-model variants examples/hierarchical/coolant_loop/tree.yaml examples/hierarchical/coolant_loop/nominal_observed.yaml
```

`describe` inspects the declared topology without solving. `run` solves a
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
conflict directions; `small_shaft_power_shift` adds 1 W to the shaft-power reading
as a benign measurement perturbation. These are synthetic meter projections,
with proposed mappings that still need review for any real plant.

### Fuel-cell system: reaction energy, air and cooling

The fuel-cell tree connects root `fc_system` to the stack, cathode air path, anode
hydrogen path, coolant loop, high-voltage bus and controls. The air and cooling
branches each expose four Level 2 blocks. Explicit `refines` links target only
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
into this connected tree; the old files remain unchanged.

The paired snapshot selects 35 of 74 reference variables: reacted-energy and
power meters, stack voltage/current, air and hydrogen feed rates, compressor
pressure/temperature/shaft measurements, intercooler and humidity readings,
valve setting, and coolant temperatures, flow, pressures and heat meters.
Unmeasured reaction rates, repeated ports, efficiency states and intermediates
are omitted. The two faults are `hydrogen_power_underread` (the reacted-energy
channel) and `cathode_air_underfeed` (air feed); `net_power_rounding` adds a benign
1 W net-power perturbation. Keep any remaining `missing_required_variables` and
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
air-side fan-heat meter, while omitting duplicate coarse aliases, COP and district
bookkeeping aliases.
Direct child `refines` links target the root's zone, chiller and electrical
balances. Fan heat and the scope of steady positive-power accounting are explicit;
no building dynamics or chiller-performance map is recovered. The
`unmet_cooling_load` fault reduces measured coil cooling from 25 kW to 22 kW.
The benign `fan_auxiliary_plus_50W` changes fan power, feeder power and independently
metered fan heat together by 50 W so both electrical and heat accounting stay
closed; it is not an isolated faulty meter reading.

## Cross-Domain Pattern

Each starter pack should include:

- Level 0 system balance template: mass, species, power, heat, inventory, or cost-of-flow checks.
- Level 1 subsystem templates: major blocks with local balances and clear refinement recommendations.
- Mapped signal declarations for external values using `MappedSignalModule`.
- Clean and conflict examples when possible.
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

Included templates:

- `level_0_plant_balance.yaml`: whole-plant water, COD, nitrogen, oxygen, and electrical power balances.
- `conflict_level_0_cod_loss.yaml`: same Level 0 template with an intentionally missing COD sink.
- `level_1_biological_clarifier.yaml`: activated-sludge oxygen/COD accounting, clarifier TSS balance, sludge recycle split, and aeration power balance.

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
- clean and conflict examples are available;
- focused tests cover zero residual, nonzero residual, validation errors, metadata, and YAML usage.

Do not add detailed models, hidden unit conversion tables, empirical correlations, or commercial-tool-equivalent behavior as part of a starter pack.

## Expanded Coverage Packs

The expanded packs are intentionally generated from a small maintainer script:

```text
scripts/generate_expanded_starter_packs.py
```

Each generated pack includes a clean Level 0 template, one conflict Level 0 template, and a Level 1 subsystem split. These are starter packs, not detailed component libraries. They should be used to test signal mapping, units, accounting boundaries, and first-pass physical plausibility before adding domain-specific modules.

| Pack | Path | Included templates | First useful checks |
| --- | --- | --- | --- |
| Cross-domain audit primitives | `examples/hierarchical/cross_domain_audit_primitives/` | `level_0_cross_domain_primitives.yaml`, `conflict_level_0_bad_temperature_offset.yaml`, `level_1_units_sensors_boundary_time.yaml` | unit conversion, sensor scale/offset, boundary loss, sample delay |
| Oil/gas pipeline and storage | `examples/hierarchical/oil_gas_pipeline_storage/` | `level_0_oil_gas_balance.yaml`, `conflict_level_0_unmetered_pipeline_leak.yaml`, `level_1_pipeline_compression_storage.yaml` | pipeline mass closure, compression power, tank inventory |
| Water supply network | `examples/hierarchical/water_supply_network/` | `level_0_water_supply_balance.yaml`, `conflict_level_0_unmetered_leakage.yaml`, `level_1_source_pump_distribution_storage.yaml` | source flow, pump power, leakage, reservoir storage |
| Manufacturing thermal process | `examples/hierarchical/manufacturing_thermal_process/` | `level_0_manufacturing_thermal_balance.yaml`, `conflict_level_0_missing_exhaust_loss.yaml`, `level_1_furnace_line_material_balance.yaml` | furnace heat, line power, material flow, exhaust loss |
| Mining and metallurgy | `examples/hierarchical/mining_metallurgy/` | `level_0_mining_metallurgy_balance.yaml`, `conflict_level_0_missing_tailings.yaml`, `level_1_ore_mill_slurry_balance.yaml` | ore split, milling power, slurry water, tailings accounting |
| Combustion boiler and furnace | `examples/hierarchical/combustion_boiler_furnace/` | `level_0_combustion_boiler_balance.yaml`, `conflict_level_0_missing_stack_loss.yaml`, `level_1_fuel_air_heat_draft_balance.yaml` | fuel/air/flue mass, useful heat, stack loss, draft fan power |
| Geothermal underground wells | `examples/hierarchical/geothermal_underground_wells/` | `level_0_geothermal_well_balance.yaml`, `conflict_level_0_missing_brine_loss.yaml`, `level_1_production_reinjection_heat_balance.yaml` | brine production/reinjection, heat extraction, pump power |
| Cold-chain logistics | `examples/hierarchical/cold_chain_logistics/` | `level_0_cold_chain_logistics_balance.yaml`, `conflict_level_0_missing_door_gain.yaml`, `level_1_warehouse_truck_fleet_balance.yaml` | warehouse/truck heat loads, refrigeration power, fleet charging |
| Robotics and mechatronics | `examples/hierarchical/robotics_mechatronics/` | `level_0_robotics_mechatronics_balance.yaml`, `conflict_level_0_missing_drive_loss.yaml`, `level_1_power_joint_thermal_actuator_balance.yaml` | DC bus accounting, joint losses, drive heat, actuator supply |
| Aerospace and satellite thermal | `examples/hierarchical/aerospace_satellite_thermal/` | `level_0_satellite_power_thermal_balance.yaml`, `conflict_level_0_missing_radiator_heat.yaml`, `level_1_satellite_power_thermal_storage_balance.yaml` | spacecraft power, battery SOC, radiator heat, propellant mass |
| Medical and bioprocess equipment | `examples/hierarchical/medical_bioprocess_equipment/` | `level_0_medical_bioprocess_equipment_balance.yaml`, `conflict_level_0_missing_ventilator_leak.yaml`, `level_1_ventilator_dialysis_sterilizer_incubator.yaml` | ventilator flow, dialysis mass, sterilizer heat, incubator thermal load |

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

Included templates:

- `level_0_microgrid_balance.yaml`: coarse PV, wind, grid import, load, battery charging, export, and curtailment accounting.
- `conflict_level_0_unserved_load.yaml`: same Level 0 template with an intentionally unserved load term.
- `level_1_renewable_storage_dispatch.yaml`: PV irradiance-area envelope, PV efficiency and inverter balance, wind available-power balance, battery charging/SOC relation, and microgrid dispatch balance.

These templates intentionally do not implement a full PV performance model, wind turbine aerodynamics, AC power-flow, or dispatch optimization. They check whether mapped signals close at a snapshot before asking for finer signals such as module temperature, inverter DC voltage/current, battery energy previous/current, or import/export metering conventions.

## Building HVAC And District Energy Starter Pack

The third starter pack is under:

```text
examples/hierarchical/building_hvac/
```

Included templates:

- `level_0_building_plant_balance.yaml`: coarse cooling-load, chiller heat-rejection, COP, and HVAC electrical power accounting.
- `conflict_level_0_unmet_cooling_load.yaml`: same Level 0 template with an intentionally unmet zone cooling load.
- `level_1_hvac_plant_loop.yaml`: zone load, chilled-water loop, chiller/condenser, air-handler, plant electrical, and district chilled-water interface balances.

These templates intentionally do not implement EnergyPlus-style building simulation, chiller or cooling-tower performance maps, detailed air-loop psychrometrics, hydronic network hydraulics, or district-energy network simulation. They check whether mapped snapshot signals close before asking for finer signals such as zone air states, chilled-water temperatures, condenser-water temperatures, COP basis, auxiliary power grouping, or district metering conventions.

## Distribution Power And DER Starter Pack

The fourth starter pack is under:

```text
examples/hierarchical/distribution_power_der/
```

Included templates:

- `level_0_feeder_balance.yaml`: coarse feeder active-power, reactive-power, load power-factor, and voltage-range checks.
- `conflict_level_0_missing_line_loss.yaml`: same Level 0 template with an intentionally under-reported active line-loss term.
- `level_1_feeder_der_power_quality.yaml`: substation transformer, two feeder sections, DER interface, aggregate P/Q balance, power-factor, and voltage-range checks.

These templates intentionally do not implement AC load flow, phase-unbalanced distribution simulation, impedance-based voltage drop, protection coordination, or detailed inverter controls. They check whether mapped snapshot signals close before asking for finer signals such as per-section power flow, per-phase P/Q/S, voltage bases, section current, line impedance, inverter reactive-power convention, or DER import/export metering basis.

## Process Industry Unit Operations Starter Pack

The fifth starter pack is under:

```text
examples/hierarchical/process_industry/
```

Included templates:

- `level_0_unit_operations_balance.yaml`: coarse plant mass, species conversion, heat-duty, and utility-power accounting.
- `conflict_level_0_missing_cooling_duty.yaml`: same Level 0 template with an intentionally under-reported cooling duty.
- `level_1_reactor_separator_utility.yaml`: reactor conversion, separator split, heat-exchange utility, and pump/compressor/valve sanity checks.

These templates intentionally do not implement reaction kinetics, detailed separator phase equilibrium, process property packages, heat-exchanger rating, pump/compressor maps, valve characteristics, or full process-flow simulation. They check whether mapped snapshot signals close before asking for finer signals such as stream compositions, conversion basis, split basis, heat-duty sign convention, temperature states, pressure states, and utility-meter grouping.

## Stormwater, Sewer, And Drainage Starter Pack

The sixth starter pack is under:

```text
examples/hierarchical/stormwater_sewer_drainage/
```

Included templates:

- `level_0_network_balance.yaml`: coarse rainfall-runoff, sanitary base flow, upstream inflow, treatment outflow, overflow, infiltration, storage accumulation, pollutant-load, and pump-power accounting.
- `conflict_level_0_unreported_overflow.yaml`: same Level 0 template with an intentionally unreported controlled-overflow term.
- `level_1_catchment_conveyance_storage_pump.yaml`: catchment runoff and inlet capture, sewer conveyance and overflow, detention storage, pump-station power/range checks, and pollutant-load accounting.

These templates intentionally do not implement a SWMM replacement, rainfall-runoff response model, Saint-Venant hydraulic routing, pump curves, detention routing, sediment transport, or water-quality kinetics. They check whether mapped snapshot signals close before asking for finer signals such as runoff partition, inlet capture, overflow boundary, storage sign convention, pump meter grouping, wet-well level basis, or pollutant load basis.

## Industrial Utilities Starter Pack

The seventh starter pack is under:

```text
examples/hierarchical/industrial_utilities/
```

Included templates:

- `level_0_utility_hub_balance.yaml`: coarse steam-header, condensate return, compressed-air, refrigeration/chilled-water, cooling-water, and utility-electrical accounting.
- `conflict_level_0_missing_air_leak.yaml`: same Level 0 template with an intentionally missing compressed-air leak term.
- `level_1_steam_air_refrigeration_cooling_water.yaml`: steam/condensate, compressed air, refrigeration/chilled-water, cooling-water, and utility-power blocks with local balances and range post-checks.

These templates intentionally do not implement plant-wide utility optimization, boiler maps, compressor maps, chiller maps, cooling-tower performance, steam-network hydraulics, or compressed-air network hydraulics. They check whether mapped snapshot signals close before asking for finer signals such as steam metering boundary, condensate return basis, air leak boundary, chiller power grouping, cooling-water heat-rejection boundary, or makeup/blowdown basis.

## Data Center And Electronics Cooling Starter Pack

The eighth implemented starter pack is under:

```text
examples/hierarchical/data_center_electronics_cooling/
```

Included templates:

- `level_0_data_center_cooling_balance.yaml`: coarse IT power-to-heat, facility power, PUE, room cooling heat balance, cooling COP, and supply-air temperature accounting.
- `conflict_level_0_underreported_cooling_capacity.yaml`: same Level 0 template with intentionally underreported cooling capacity.
- `level_1_it_room_cooling_power_chain.yaml`: IT/rack heat, facility power chain, room air cooling, coolant loop, and cooling-plant efficiency blocks with local balances and range post-checks.

These templates intentionally do not implement CFD, airflow-network simulation, chip/package thermal models, UPS/PDU equipment models, chiller/CDU/economizer maps, or detailed cooling-control optimization. They check whether mapped snapshot signals close before asking for finer signals such as IT power meter boundary, PUE meter grouping, room heat-gain boundary, cooling power grouping, coolant heat boundary, or temperature basis.

## Mobility Extensions Starter Pack

The ninth implemented starter pack is under:

```text
examples/hierarchical/mobility_extensions/
```

Included templates:

- `level_0_mobility_energy_balance.yaml`: coarse charging infrastructure, rail traction, marine propulsion, aviation power, and off-road hydraulic power accounting.
- `conflict_level_0_missing_charger_loss.yaml`: same Level 0 template with an intentionally omitted charger-loss term.
- `level_1_charging_rail_marine_aviation_offroad.yaml`: charging, rail traction, marine propulsion, aviation power, and off-road hydraulics blocks with local balances, ratio checks, and range post-checks.

These templates intentionally do not implement vehicle dynamics, route optimization, rail-network load flow, ship resistance, flight dynamics, propulsion maps, battery electrochemistry, charger curves, or hydraulic valve/pump maps. They check whether mapped snapshot signals close before asking for finer signals such as charger meter boundary, rail meter grouping, marine/aviation power basis, hydraulic power boundary, SOC basis, speed basis, or hydraulic pressure basis.

## Agriculture, Food, And Bioprocess Starter Pack

The tenth implemented starter pack is under:

```text
examples/hierarchical/agriculture_food_bioprocess/
```

Included templates:

- `level_0_agri_food_bioprocess_balance.yaml`: coarse greenhouse heat/CO2, irrigation water, fermentation mass, drying heat/water, and cold-chain accounting.
- `conflict_level_0_missing_irrigation_drainage.yaml`: same Level 0 template with an intentionally omitted irrigation drainage return term.
- `level_1_greenhouse_irrigation_fermentation_drying_cold_chain.yaml`: irrigation/crop-water, greenhouse heat, greenhouse CO2, fermentation, drying, and cold-chain blocks with local balances, ratio checks, and range post-checks.

These templates intentionally do not implement crop-growth models, photosynthesis kinetics, microbial kinetics, drying-rate models, refrigeration maps, detailed food-process simulation, or greenhouse climate-control optimization. They check whether mapped snapshot signals close before asking for finer signals such as greenhouse heat boundary, CO2 balance basis, irrigation drainage boundary, fermentation mass/yield basis, dryer water/exhaust basis, or cold-chain heat-gain boundary.

## Heated-Tank Reference Example

`examples/hierarchical/heated_tank/` contains a synthetic non-SI CSV, a coarse
volume/energy audit and a six-block coupled hierarchy with an explicit heater
nameplate-efficiency assumption. `sim_tank.py` regenerates the CSV;
`python -m physicsguard.cli testfile snapshot tank_run_contract.yaml --row 70 --out measured_k70.yaml` writes the mapped SI snapshot; use `first_step_contract.yaml` for the coarse model.
The heater current halves at 600 s while its command stays unchanged; inflow changes
at 900 s. This is a low-fidelity diagnostic reference. Measurements contain no
hand-computed connected endpoints or intermediate heat flows.

For the full heated-tank time series, run `testfile series tank_run_contract.yaml
--out tank_series.yaml`, then `validation run validation_plan.yaml` from the
example directory. The compact report identifies the heater failure interval
starting at 600 seconds, without listing sixty repeated point failures.
