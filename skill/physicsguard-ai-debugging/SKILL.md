---
name: physicsguard-ai-debugging
description: Use PhysicsGuard for AI-guided low-fidelity audits of engineering simulation results, especially MATLAB/Simulink, GT-SUITE, Modelica-like, Python, or other physical simulation workflows where Codex needs to map exported signals into PhysicsGuard YAML, run coarse-to-fine residual checks, rank suspicious blocks, diagnose unit/sign/map/control/physics mismatches, and recommend the next variables or parameters to inspect. Use when the user asks to evaluate, debug, modify, sanity-check, fault-diagnose, or progressively localize bugs in physical simulation models without building a commercial-tool adapter or high-fidelity replacement.
---

# PhysicsGuard AI Debugging

## Purpose

Use PhysicsGuard as a transparent audit layer for complex engineering simulations. Do not try to reproduce a full Simulink, GT-SUITE, Modelica, FMI, Amesim, MATLAB, Python, or commercial model. Build low-fidelity residual checks, evaluate mapped external results, rank suspicious blocks, and ask for the next useful signals.

## Default Workflow

1. Clarify the visible failure: wrong final value, unstable response, impossible pressure/flow/power/heat/current/voltage, bad efficiency, or inconsistent control logic.
2. Build or choose the coarsest useful PhysicsGuard audit YAML.
3. Map external simulation signals into `ObservedValuesSpec`. AI may propose mappings, but uncertain mappings must be explicit in metadata or Assumption Cards.
4. Prefer direct observed evaluation:

   ```powershell
   python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml --pretty
   ```

5. Inspect `audit_pass`, `top_blocks`, `top_residuals`, `recommended_refinements`, `missing_required_variables`, and `missing_required_parameters`.
6. Request or export only the next small set of signals/parameters needed by the suspicious block.
7. Refine that block with a lower-level audit template.
8. Repeat until the problem is localized to a subsystem, component, signal chain, parameter, map, unit conversion, or boundary condition.

Use compare mode only when a solved low-fidelity reference is intentionally useful:

```powershell
python -m physicsguard.cli hierarchy compare AUDIT.yaml OBSERVED.yaml --pretty
```

## Hard Boundaries

- Do not add or imply a GT-SUITE, Simulink, MATLAB, Modelica, FMI, CSV, Amesim, or commercial-tool adapter unless explicitly requested.
- Do not reverse engineer commercial model internals.
- Do not add high-fidelity solvers, automatic repair, or natural-language report generation.
- Do not use assumptions as solver-tunable variables.
- Do not silently invent signal mappings, units, or parameters.
- Do not claim a plausible parameter is wrong without residual evidence or an explicit design envelope.

## When To Create A New PhysicsGuard Relation

Create or edit modules only when the existing library cannot express the needed low-fidelity check and the user has authorized code changes. Keep added checks explicit and simple:

- algebraic conservation or balance;
- single-step dynamic relation;
- unit conversion audit;
- map or axis consistency check;
- sign/gain/saturation/check logic;
- coarse electrochemical, thermal, fluid, drivetrain, or power relation.

Each new relation must use SI units internally, document assumptions and limitations, declare finite bounds/scales, register through `ModuleRegistry`, and include tests/examples.

## Common Debugging Directions

Load `references/bug-playbooks.md` when choosing the next hypothesis. It covers unit/scale errors, sign reversals, bad signal mapping, impossible parameter magnitudes, map-axis mistakes, control-state mismatches, and broken balances.

Load `references/protocol.md` when writing or reviewing a full AI debugging plan.

