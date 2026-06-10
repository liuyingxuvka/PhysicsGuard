---
name: physicsguard-ai-debugging
description: Use PhysicsGuard for AI-guided low-fidelity audits and model-building blueprints for engineering simulation workflows, especially MATLAB/Simulink, GT-SUITE, Modelica-like, Python, or other physical simulation systems. Use when Codex needs to map exported signals into PhysicsGuard YAML, run coarse-to-fine residual checks, rank suspicious blocks, diagnose unit/sign/map/control/physics mismatches, recommend the next variables or parameters to inspect, or progressively build a PhysicsGuard-validated candidate model that can later be translated into MATLAB/Simulink scripts or other official target-model interfaces. Do not use this as a commercial-tool adapter, reverse-engineering workflow, or high-fidelity solver replacement.
---

# PhysicsGuard AI Debugging

## Purpose

Use PhysicsGuard as a transparent audit and blueprint layer for complex engineering simulations. Do not try to reproduce a full Simulink, GT-SUITE, Modelica, FMI, Amesim, MATLAB, Python, or commercial model from hidden internals. Build low-fidelity residual checks, evaluate mapped external results, rank suspicious blocks, ask for the next useful signals, and when requested, use the validated low-fidelity hierarchy as a blueprint for generating a candidate target model through official scripting interfaces.

## Visual Audit Communication

For non-trivial PhysicsGuard debugging, audit explanation, refinement, or candidate-model blueprint work, default to showing one compact Mermaid diagram or table once the physical-audit path is stable enough to explain. First run a PhysicsGuard diagram intent gate:

- What relationship is being explained: physical topology, residual localization, observed signal mapping, assumption boundary, coarse-to-fine refinement, or candidate-model blueprint?
- What do the edges mean: mass/energy/heat/power/signal flow, `maps_to`, `checked_by`, `bounds`, `refines_to`, or `requires_signal`?
- Does the visual help the user see the suspicious block, evidence boundary, and next signal or parameter request?
- Could the visual be mistaken for a recovered high-fidelity or commercial-tool topology?

Choose from the PhysicsGuard visual toolbox:

- Physical topology map: system boundary, subsystems, components, interfaces, and physical or signal flows.
- Residual localization overlay: topology plus `top_blocks`, `top_residuals`, normalized residuals, `audit_pass` or `audit_fail`, and recommended next inspection.
- Observed signal mapping map: external signal names mapped into PhysicsGuard variables, with units, confidence, `review_required`, stale mapping notes, missing conversion evidence, and same-family follow-up checks where relevant.
- Assumption boundary overlay: active, proposed, and rejected Assumption Cards attached to affected variables, parameters, blocks, or residual checks.
- Coarse-to-fine refinement path: Level 0 or parent block to deeper template, required variables, required parameters, rationale, and stop/defer conditions.
- Candidate model blueprint: validated low-fidelity blocks, interfaces, units, assumptions, examples, and target-model generation boundary.

Do not flatten these modes into a generic flowchart. When a diagram mixes relationship types, label the edge semantics or pair the diagram with a small table. Formulae are useful as local residual labels or companion tables, but they should not replace the physical audit map unless the user's question is specifically about the equation.

Diagrams and tables explain the audit route; they are not validation evidence. Validation claims must come from PhysicsGuard CLI output, FlowGuard checks, pytest, example regressions, or release evidence. Skip diagrams for tiny status answers, direct command results, or simple low-stakes explanations where a visual adds no clarity.

## Workflow A: Audit External Results

1. Clarify the visible failure: wrong final value, unstable response, impossible pressure/flow/power/heat/current/voltage, bad efficiency, or inconsistent control logic.
2. If the work includes a concrete testbench/test-data file, first route through
   `physicsguard-test-file-contract-review`. Generate or inspect the file
   manifest, check the file-specific contract, and do not make broad AI analysis
   claims until the contract passes. If there is no concrete test data file,
   continue with the normal model-only or observed-snapshot route.
3. Check project adoption when working inside a repository:

   ```powershell
   python -m physicsguard.cli project audit --pretty
   ```

   If adoption is missing and setup is in scope, run `project adopt` or `project upgrade`. Project adoption is workflow evidence only.
4. Create or review a model-understanding preflight before residual interpretation:

   ```powershell
   python -m physicsguard.cli preflight review PREFLIGHT.yaml --pretty
   ```

   The preflight must name the visible symptom, external model source of truth, physical boundary, subsystem blocks, conserved quantities, expected SI units, assumptions, uncertain mappings, first audit level, and stop conditions.
5. Build or choose the coarsest useful PhysicsGuard audit YAML.
6. Map external simulation signals into `ObservedValuesSpec` and, for non-trivial external-model work, review an intake record:

   ```powershell
   python -m physicsguard.cli intake review INTAKE.yaml --pretty
   ```

   AI may propose mappings, but uncertain mappings must be explicit. For new observed snapshots, prefer per-variable fields such as `external_signal`, `mapping_confidence`, `mapping_status`, `review_required`, `conversion_factor`, `conversion_note`, `mapped_at`, and `stale_when`; older metadata or Assumption Cards are acceptable fallback evidence. Intake metadata records evidence only; it does not convert or mutate observed values.
7. Prefer direct observed evaluation:

   ```powershell
   python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml --pretty
   ```

8. Inspect `audit_pass`, `top_blocks`, `top_residuals`, `recommended_refinements`, `signal_mapping_ledger`, `bug_family_followups`, `missing_required_variables`, and `missing_required_parameters`.
9. Use a residual localization overlay, signal-mapping table, same-family follow-up list, or refinement-path view when it helps explain why a block is suspicious and which data is needed next.
10. Request or export only the next small set of signals/parameters needed by the suspicious block.
11. Refine that block with a lower-level audit template.
12. Repeat until the problem is localized to a subsystem, component, signal chain, parameter, map, unit conversion, or boundary condition. If `bug_family_followups` names gain/sign, unit-conversion, signal-mapping, or balance siblings, inspect the sibling family before declaring the first failed residual fully localized.

Use compare mode only when a solved low-fidelity reference is intentionally useful:

```powershell
python -m physicsguard.cli hierarchy compare AUDIT.yaml OBSERVED.yaml --pretty
```

Before claiming the audit is localized or complete, run the closure helper when
available. A partial, blocked, downgraded, stale, skipped, or mapping-review
closure must downgrade the final claim:

```powershell
python %USERPROFILE%\\.codex\\skills\physicsguard-ai-debugging\scripts\physicsguard_closure_check.py --ledger <physicsguard-closure-ledger.json> --audit AUDIT.yaml --observed OBSERVED.yaml --json
```

The helper reads `audit_pass`, `top_blocks`, `top_residuals`,
`recommended_refinements`, `signal_mapping_ledger`,
`bug_family_followups`, `missing_required_variables`, and
`missing_required_parameters`. It also treats review-required mapping issue
codes, stale evidence, and skipped checks as closure evidence. If it returns
`partial`, `blocked`, or `downgraded`, continue with the named next action:
request the next required signals or parameters, review uncertain signal
mappings, refine the suspicious block one level, inspect same-family
unit/sign/map/balance follow-ups, rerun after observed snapshots change, run or
scope skipped checks, or downgrade the localization claim.

## Workflow B: Build A Candidate Model From A PhysicsGuard Blueprint

Use this when the user wants AI to construct a new model, not merely inspect an existing result.

1. Start at the lowest useful fidelity: aggregate balances, simple component relations, and explicit interfaces.
2. Define the target fidelity for each block before refining it.
3. Build and validate each block in PhysicsGuard first.
4. Use a candidate blueprint view when it helps show validated blocks, interfaces, units, assumptions, examples, and target-model boundaries.
5. Generate a candidate target-model implementation only after the block passes its PhysicsGuard checks.
6. For MATLAB/Simulink, prefer MATLAB script generation through documented APIs such as `new_system`, `add_block`, `set_param`, and `add_line`.
7. Run the generated candidate model, map its outputs back into PhysicsGuard, and compare residuals.
8. Refine one block at a time until the assembled candidate model is good enough for the user's purpose.

Treat generated target models as candidate engineering models, not recovered copies of an existing commercial model. Load `references/model-generation.md` before writing a full model-generation plan or MATLAB/Simulink script.

## Required Header For New PhysicsGuard YAML

When creating a new PhysicsGuard audit YAML, hierarchy template, observed snapshot, or candidate-model blueprint, put this one-layer comment header at the top of the file before the YAML content. Make the `Purpose` line specific to the file so the YAML stays understandable on a machine that does not have this skill installed:

```yaml
# PhysicsGuard audit/model blueprint
# Purpose: Low-fidelity residual audit for <short model purpose>.
# Repository: https://github.com/liuyingxuvka/PhysicsGuard
# Use with: python -m physicsguard.cli <run|hierarchy run|hierarchy evaluate> ...
# Boundary: Low-fidelity SI-unit residual audit or blueprint only; not a high-fidelity solver, commercial-tool adapter, or reverse-engineered model.
```

Keep the header as comments only. Do not add provenance metadata solely for this header unless the YAML schema or the user's task already needs metadata for another reason.

## Hard Boundaries

- Do not add or imply a GT-SUITE, Simulink, MATLAB, Modelica, FMI, CSV, Amesim, or commercial-tool adapter unless explicitly requested.
- Do not reverse engineer commercial model internals.
- Do not claim the generated target model is equivalent to a commercial or high-fidelity model.
- Do not add high-fidelity solvers, automatic repair, or natural-language report generation.
- Do not use assumptions as solver-tunable variables.
- Do not silently invent signal mappings, units, or parameters.
- Do not mark test-file fields as covered without mapping evidence. Unknown
  field meaning or unknown model binding must stay review-required, planned as a
  model extension, or fail the contract.
- Do not treat `signal_mapping_ledger` as a conversion engine. It records evidence and review state; observed values are still used exactly as supplied.
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
