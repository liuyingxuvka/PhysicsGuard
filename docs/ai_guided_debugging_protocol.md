# AI-Guided PhysicsGuard Debugging Protocol

PhysicsGuard is a tool for AI-assisted engineering debugging. It is not expected to understand every external model automatically, and it does not need to contain every possible physical module ahead of time. The intended workflow is iterative: an AI agent proposes a low-fidelity audit, maps available external signals into PhysicsGuard variables, evaluates residuals, and asks for the next small set of signals or parameters that would narrow the problem.

## Core Loop

1. Start with the user-visible failure: wrong final value, impossible pressure, excessive heat, bad power, unstable response, or similar.
2. Build a Level 0 audit with coarse balances or simple signal relations.
3. Map external signals into `ObservedValuesSpec`. Signal mapping can be AI-proposed, but uncertain mappings must be recorded in metadata or Assumption Cards.
4. Run `physicsguard hierarchy evaluate AUDIT.yaml OBSERVED.yaml --pretty`.
5. Inspect `audit_pass`, `top_blocks`, `top_residuals`, and `recommended_refinements`.
6. Request or export only the next variables and parameters named by `recommended_refinements`.
7. Create or choose the next-level audit template for the suspicious block.
8. Repeat until the issue is localized to a subsystem, component, signal chain, map, unit conversion, parameter, or boundary condition.

Use `physicsguard hierarchy compare AUDIT.yaml OBSERVED.yaml --pretty` when a solved low-fidelity reference is useful for ranking variable deviations. Use direct `hierarchy evaluate` when the external result itself is the evidence and PhysicsGuard must not move values.

## What The AI May Do

- Propose signal mappings from external model names to PhysicsGuard variables.
- Mark uncertain mappings explicitly.
- Build small low-fidelity audit YAML files for the current debugging question.
- Add a new low-fidelity explicit residual module when the existing library does not contain the required relation and the user has authorized code changes.
- Recommend the next signals or parameters to inspect.
- Compare competing hypotheses by running separate audit templates.

## What The AI Must Not Do

- Do not silently invent assumptions.
- Do not use assumptions as solver-tunable variables.
- Do not use solved boundary conditions as a substitute for observed external results.
- Do not claim a subtly plausible parameter is wrong unless residual evidence or user-provided targets make it suspicious.
- Do not imply equivalence with GT-SUITE, Simulink, Simscape, Modelica, Amesim, FMI, PyBaMM, OpenFCST, or commercial model internals.
- Do not auto-repair or rewrite the external model.

## Practical Signal-Mapping Rule

For unknown external models, exact signal names are rarely known in advance. The AI should make a best-effort mapping, but every mapping should remain reviewable:

```yaml
metadata:
  signal_mapping:
    controller_q_gain.x:
      external_signal: f14/Controller/Gain2_input
      confidence: medium
      review_required: true
```

When a mapping is uncertain enough to affect the diagnosis, use an Assumption Card or mark the mapping in metadata. Hidden mappings are not acceptable.

## When To Add New Audit Models

Add a new audit relation only when it is simple, explicit, low-fidelity, and directly useful for the current debugging step. A good added relation looks like:

- algebraic balance;
- single-step dynamic check;
- map consistency check;
- unit conversion audit;
- sign/gain/saturation check;
- coarse conservation relation.

Do not add detailed physics, external adapters, or commercial-tool behavior.

## Interpreting Results

`top_blocks` is the AI's next search direction, not proof. `confidence` is a data-sufficiency heuristic, not probability. `recommended_refinements` should drive the next signal request or next audit template. A high residual with low confidence usually means the AI should ask for more signals before accusing a specific parameter.

