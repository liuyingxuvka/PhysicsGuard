# PhysicsGuard Physical Module Spec Template

Every future physical module must be documented before implementation. Keep equations explicit and low-fidelity unless the user requests otherwise.

## Module Name

Name:

## Purpose

What this audit module checks:

What it does not attempt to model:

## Physical Domain

Domain:

## Variables

| Variable | SI Unit | Meaning | Default Lower Bound | Default Upper Bound | Default Initial Guess | Default Scale |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

## Parameters

| Parameter | SI Unit | Required | Default | Bounds | Meaning |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

## SI Units

All variables, parameters, residuals, and examples must use SI units internally.

## Residual Equations

List each residual explicitly:

```text
residual_name = left_hand_side - right_hand_side
```

Do not add undocumented equations.

## Residual Scales

| Residual | Default Scale | Rationale |
| --- | --- | --- |
|  |  |  |

## Variable Bounds

Explain why the default bounds are finite, conservative, and suitable for audit usage.

## Initial Guess Strategy

Explain how default initial guesses are chosen and how users should override them.

## Assumptions

- 

## Validity Range

- 

## Known Limitations

- 

## Diagnostic Keys

| Diagnostic Key | Residual | Meaning |
| --- | --- | --- |
|  |  |  |

## Likely Causes For Large Residuals

- 

## Unit Tests Required

- Zero residual at a known consistent point.
- Nonzero residual sign and magnitude sanity check.
- Invalid parameter validation.
- Variable override behavior when the module declares variables.
- YAML example solve.
- Diagnostic key and residual role checks.

## Example YAML Usage

```yaml
system_name: example_system
components:
  - id: component
    type: ModuleName
    parameters: {}
boundaries: []
```

## Foundation Module Example Patterns

Thermal conductor:

```yaml
components:
  - id: cond
    type: ThermalConductorModule
    parameters:
      G_W_K: 50.0
boundaries:
  - variable: cond.T_a_K
    value: 320.0
  - variable: cond.T_b_K
    value: 300.0
```

Fluid pressure drop:

```yaml
components:
  - id: restriction
    type: IncompressiblePressureDropModule
    parameters:
      K: 2.0
      rho_kg_m3: 1000.0
      area_m2: 0.01
```

Electrical power:

```yaml
components:
  - id: elec
    type: ElectricalPowerModule
    parameters: {}
boundaries:
  - variable: elec.V_V
    value: 400.0
  - variable: elec.current_A
    value: 10.0
```

Electrochemical stack power:

```yaml
components:
  - id: stack
    type: ElectrochemicalStackPowerModule
    parameters:
      n_cells: 400.0
```

Control error:

```yaml
components:
  - id: err
    type: ControlErrorModule
    parameters: {}
boundaries:
  - variable: err.setpoint
    value: 10.0
  - variable: err.measurement
    value: 7.0
```

Humidity helper:

```yaml
components:
  - id: rh
    type: RelativeHumidityFromPartialPressureModule
    parameters: {}
boundaries:
  - variable: rh.p_vapor_Pa
    value: 1000.0
  - variable: rh.p_saturation_Pa
    value: 2000.0
```

Heat exchanger helper:

```yaml
components:
  - id: hx
    type: HeatExchangerEffectivenessModule
    parameters:
      cp_hot_J_kgK: 1000.0
      cp_cold_J_kgK: 1000.0
      effectiveness: 0.5
```

Rotating-machine helper:

```yaml
components:
  - id: aff
    type: RotatingMachineAffinityModule
    parameters:
      nominal_speed_rad_s: 100.0
      nominal_m_dot_kg_s: 1.0
      nominal_delta_p_Pa: 100000.0
      nominal_P_shaft_W: 1000.0
```

Electrochemical helper:

```yaml
components:
  - id: air
    type: AirOxygenMolarFlowModule
    parameters:
      oxygen_mole_fraction: 0.21
      molar_mass_air_kg_mol: 0.0289652
```

Component-level audit module:

```yaml
components:
  - id: motor
    type: ElectricMotorSimpleModule
    parameters:
      residual_scale_power_W: 1000.0
boundaries:
  - variable: motor.voltage_V
    value: 400.0
  - variable: motor.current_A
    value: 10.0
  - variable: motor.torque_Nm
    value: 30.0
  - variable: motor.omega_rad_s
    value: 100.0
```

Component-level modules must state whether they are algebraic power balances, map consistency checks, one-step control checks, thermal balances, or electrochemical balance checks. Map-based component modules must document axis units, output units, and `extrapolation` behavior.

## Engineering Component Batch Example Patterns

Fluid network component:

```yaml
components:
  - id: pipe
    type: PipeSegmentSimpleModule
    parameters:
      rho_kg_m3: 1000.0
      diameter_m: 0.05
      length_m: 2.0
      friction_factor: 0.02
      K_minor: 1.0
```

Thermal management component:

```yaml
components:
  - id: cold
    type: ColdPlateSimpleModule
    parameters:
      UA_W_K: 500.0
      cp_coolant_J_kgK: 4180.0
```

Electrochemical BOP component:

```yaml
components:
  - id: cathode
    type: FuelCellCathodeAirSupplyModule
    parameters:
      n_cells: 400.0
      oxygen_mole_fraction: 0.21
      molar_mass_air_kg_mol: 0.0289652
```

Battery/HV component:

```yaml
components:
  - id: soc
    type: BatterySOCStepModule
    parameters:
      capacity_C: 360000.0
      dt_s: 1.0
      sign_convention: discharge_positive
```

Drivetrain/vehicle component:

```yaml
components:
  - id: vehicle
    type: VehicleLongitudinalDynamicsStepModule
    parameters:
      mass_kg: 1500.0
      dt_s: 1.0
```

Engine/aftertreatment component:

```yaml
components:
  - id: afr
    type: EngineAirFuelRatioModule
    parameters:
      denominator_min_abs: 1.0e-12
```

Control/sensor/actuator component:

```yaml
components:
  - id: convert
    type: UnitConversionAuditModule
    parameters:
      factor: 100000.0
      offset: 0.0
      source_unit: bar
      target_unit: Pa
```

For these engineering components, document whether residuals are active solver equations or diagnostic-only `post_check` residuals. Post-check residuals must be visible in diagnostics but must never pull a solved reference state.

## Aggregate / Hierarchical Audit Example Pattern

Aggregate modules are coarse residual modules for hierarchical Level 0 or Level 1 checks. They should be used to roll up existing variables into block-level balances, not to replace component-level modules.

```yaml
components:
  - id: system_power_balance
    type: AggregatePowerBalanceModule
    parameters:
      source_power_variables: [fuel.P_chemical_W]
      load_power_variables: [stack.P_stack_W, aux.P_aux_W]
      loss_power_variables: [thermal.Q_rejected_W]
      residual_scale_W: 1000.0
hierarchy:
  blocks:
    - id: whole_system
      level: 0
      components: [system_power_balance]
      expected_residual_keys: [aggregate_power_balance_mismatch]
```

Hierarchical audit documentation should state block ownership, residual assignment expectations, scoring method, confidence penalties, refinement rules, and template ids. Recommended refinements are suggestions only and must not execute automatically.
