# PhysicsGuard Model Generation Protocol

Use this protocol when the user wants AI to build a new candidate engineering model from a PhysicsGuard blueprint.

## Core idea

PhysicsGuard is the low-fidelity source of truth for interfaces, units, assumptions, and conservation checks. The generated target model is a candidate implementation of that blueprint, not a reverse-engineered copy of any existing commercial model.

## Recommended loop

1. Define the target system and the minimum useful fidelity.
2. Split the system into blocks with explicit inputs, outputs, parameters, and units.
3. Build the coarsest PhysicsGuard hierarchy first.
4. Validate the hierarchy with clean examples, conflict examples, or observed data.
5. Refine only blocks whose target fidelity requires more detail.
6. For each block, generate the target-model implementation after the PhysicsGuard block passes.
7. Run the target model and export or capture the same signals.
8. Evaluate those signals back through PhysicsGuard.
9. Iterate until residuals, interfaces, and block behavior are acceptable.

## MATLAB/Simulink generation guidance

When MATLAB/Simulink is the target, prefer script-generated models:

- create models and subsystems with documented MATLAB/Simulink APIs;
- use `new_system`, `open_system`, `add_block`, `set_param`, and `add_line` where appropriate;
- keep generated models separate from built-in examples or user originals;
- generate one subsystem at a time before assembling the whole model;
- add scopes, logs, or output blocks for the signals PhysicsGuard needs to recheck;
- keep signal names traceable to PhysicsGuard variables when practical.

## Other target tools

For GT-SUITE, Modelica, Amesim, FMI, or similar tools, proceed only through official APIs, user-provided templates, documented exchange formats, or explicit user-owned files. Do not reverse engineer proprietary file formats or imply solver equivalence.

## Required artifacts

A full model-generation pass should produce:

- a PhysicsGuard hierarchy YAML;
- explicit assumptions and units;
- a target-model generation plan;
- generated scripts or target-model files when the interface is available;
- an observed-results mapping back to PhysicsGuard;
- a residual report showing whether the generated model still matches the blueprint.

New PhysicsGuard YAML files created during this pass should start with the standard PhysicsGuard comment header from the skill instructions, so later agents immediately see the intended use, full skill entry point, SI-unit expectation, and non-equivalence boundary.

## Stop conditions

Stop and ask for user input when:

- the requested target-model fidelity is unclear;
- a required official tool interface is missing;
- signal names or units cannot be mapped with reasonable confidence;
- the generated target model fails for tool-specific reasons that are not visible from PhysicsGuard diagnostics.
