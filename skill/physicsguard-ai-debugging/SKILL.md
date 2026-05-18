---
name: physicsguard-ai-debugging
description: Use PhysicsGuard for AI-guided low-fidelity audits and model-building blueprints for engineering simulation workflows, especially MATLAB/Simulink, GT-SUITE, Modelica-like, Python, or other physical simulation systems. Use when Codex needs to map exported signals into PhysicsGuard YAML, run coarse-to-fine residual checks, rank suspicious blocks, diagnose unit/sign/map/control/physics mismatches, recommend the next variables or parameters to inspect, or progressively build a PhysicsGuard-validated candidate model that can later be translated into MATLAB/Simulink scripts or other official target-model interfaces. Do not use this as a commercial-tool adapter, reverse-engineering workflow, or high-fidelity solver replacement.
---

# PhysicsGuard AI Debugging

## Purpose

Use PhysicsGuard as a transparent audit and blueprint layer for complex engineering simulations. Do not try to reproduce a full Simulink, GT-SUITE, Modelica, FMI, Amesim, MATLAB, Python, or commercial model from hidden internals. Build low-fidelity residual checks, evaluate mapped external results, rank suspicious blocks, ask for the next useful signals, and when requested, use the validated low-fidelity hierarchy as a blueprint for generating a candidate target model through official scripting interfaces.

## Workflow A: Audit External Results

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

## Workflow B: Build A Candidate Model From A PhysicsGuard Blueprint

Use this when the user wants AI to construct a new model, not merely inspect an existing result.

1. Start at the lowest useful fidelity: aggregate balances, simple component relations, and explicit interfaces.
2. Define the target fidelity for each block before refining it.
3. Build and validate each block in PhysicsGuard first.
4. Generate a candidate target-model implementation only after the block passes its PhysicsGuard checks.
5. For MATLAB/Simulink, prefer MATLAB script generation through documented APIs such as `new_system`, `add_block`, `set_param`, and `add_line`.
6. Run the generated candidate model, map its outputs back into PhysicsGuard, and compare residuals.
7. Refine one block at a time until the assembled candidate model is good enough for the user's purpose.

Treat generated target models as candidate engineering models, not recovered copies of an existing commercial model. Load `references/model-generation.md` before writing a full model-generation plan or MATLAB/Simulink script.

## Required Header For New PhysicsGuard YAML

When creating a new PhysicsGuard audit YAML, hierarchy template, observed snapshot, or candidate-model blueprint, put this one-layer comment header at the top of the file before the YAML content:

```yaml
# PhysicsGuard audit/model blueprint
# This file is a low-fidelity residual audit or candidate-model blueprint for AI-guided engineering debugging.
# Use it with the PhysicsGuard Codex skill for the full workflow:
# https://github.com/liuyingxuvka/PhysicsGuard
# Keep SI units, explicit assumptions, documented residuals, and clear signal mappings.
# Do not treat this file as a high-fidelity solver, commercial-tool adapter, or reverse-engineered model.
```

Keep the header as comments only. Do not add provenance metadata solely for this header unless the YAML schema or the user's task already needs metadata for another reason.

## Hard Boundaries

- Do not add or imply a GT-SUITE, Simulink, MATLAB, Modelica, FMI, CSV, Amesim, or commercial-tool adapter unless explicitly requested.
- Do not reverse engineer commercial model internals.
- Do not claim the generated target model is equivalent to a commercial or high-fidelity model.
- Do not add high-fidelity solvers, automatic repair, or natural-language report generation.
- Do not use assumptions as solver-tunable variables.
- Do not silently invent signal mappings, units, or parameters.
- Do not claim a plausible parameter is wrong without residual evidence or an explicit design envelope.
- For GT-SUITE, Modelica, Amesim, FMI, or other external tools, use only official, user-provided, or documented interfaces; otherwise stop at the PhysicsGuard blueprint and explain what interface is missing.

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

Load `references/model-generation.md` when turning a PhysicsGuard hierarchy into a candidate MATLAB/Simulink or other target-model implementation plan.
