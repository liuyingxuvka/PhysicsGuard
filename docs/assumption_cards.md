# Assumption Cards

AssumptionGuard Lite is the first assumption-management layer for PhysicsGuard. It keeps assumptions visible and controlled without building a rule engine, inference system, scenario sweeper, or probabilistic confidence model.

## Motivation

Low-fidelity audit models often need values that are missing from an external model export or current signal set. Those values might be temperatures, efficiencies, conductances, pressures, or context notes. If they are hidden, assumptions can mask real model errors. PhysicsGuard therefore requires explicit Assumption Cards.

Core rules:

- no implicit assumptions;
- every assumption is represented as a card;
- every card is included in diagnostic JSON;
- assumptions are not solver-tunable variables;
- proposed and rejected assumptions are visible but not applied;
- high-impact assumptions produce warnings;
- applied assumptions reduce a transparent `confidence_factor`.

## Assumption Card Fields

Common fields:

- `id`: stable nonempty id without whitespace.
- `target_type`: `variable`, `parameter`, or `context`.
- `target`: `component.variable`, `component.parameter`, or a nonempty context key.
- `value`: JSON-serializable scalar.
- `unit`: optional unit string.
- `reason`: required explanation.
- `source`: examples include `user_provided`, `engineering_default`, `missing_signal`, `missing_parameter`, `temporary_debug`, `ai_proposed`, and `scenario_value`.
- `impact`: `low`, `medium`, or `high`.
- `confidence_penalty`: optional nonnegative override.
- `review_required`: defaults to `true`.
- `status`: `active`, `proposed`, or `rejected`.
- `allow_override`: defaults to `false`.
- `notes`, `tags`, `metadata`: optional machine-readable context.

Default confidence penalties:

- low impact: `0.02`
- medium impact: `0.10`
- high impact: `0.25`

## Variable Assumptions

Active variable assumptions are fixed-value residuals:

```text
variable - assumed_value = 0
```

They use:

- `source: assumption`
- `role: assumption`
- `diagnostic_key: assumed_variable_value`

The role participates in the solver like a boundary residual, but the assumed value is not a free optimization variable.

If an explicit boundary already targets the same variable, the explicit boundary is preferred. The assumption is not applied unless `allow_override: true`, in which case the explicit boundary is skipped and a warning is reported.

## Parameter Assumptions

Active parameter assumptions apply before module construction. If the target component exists and the parameter is missing, the parameter is filled and the card reports:

```text
application: parameter_fill
```

If the parameter already exists, PhysicsGuard does not override it unless `allow_override: true`. Overrides report:

```text
application: parameter_override
```

and add warnings to both the card and the top-level diagnostics.

## Context Assumptions

Context assumptions do not modify solver inputs. They document context such as ambient test assumptions or operating mode notes and report:

```text
application: context_only
```

## Status Values

`active` assumptions may be applied.

`proposed` assumptions are visible but not applied:

```text
application: not_applied_proposed
```

`rejected` assumptions are visible but not applied:

```text
application: not_applied_rejected
```

If an assumption is questionable, mark it as `proposed` rather than `active`.

## Examples

Variable assumption:

```yaml
assumptions:
  - id: assume_coolant_inlet_temperature
    target_type: variable
    target: coolant.T_in_K
    value: 300.0
    unit: K
    reason: Coolant inlet temperature is not available in the current signal set.
    source: missing_signal
    impact: high
```

Parameter assumption:

```yaml
assumptions:
  - id: assume_conductor_G
    target_type: parameter
    target: conductor.G_W_K
    value: 50.0
    unit: W/K
    reason: Thermal conductance is not provided; use coarse audit estimate.
    source: engineering_default
    impact: low
```

Proposed assumption:

```yaml
assumptions:
  - id: propose_conductor_G
    target_type: parameter
    target: conductor.G_W_K
    value: 60.0
    reason: Possible default, but not confirmed.
    source: ai_proposed
    impact: high
    status: proposed
```

## Limitations

- No automatic assumption inference.
- No scenario sweeps.
- No probabilistic confidence.
- No human approval workflow yet.
- No dependency tracking to detect assumptions derived from the same result being validated.
- No automatic blocking for high-impact assumptions.

## Future Work

- Scenario assumptions: run low/nominal/high assumption sets.
- Operating envelopes: define valid operating ranges for templates.
- Assumption sensitivity: classify `robust_pass`, `robust_fail`, or `assumption_sensitive`.
- Human approval workflow: approve or reject AI-proposed assumptions.
- Assumption budget: limit count or impact of assumptions per block.
- Dependency tracking: detect assumptions derived from the same result they validate.
