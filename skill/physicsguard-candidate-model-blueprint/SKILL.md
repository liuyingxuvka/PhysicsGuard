---
name: physicsguard-candidate-model-blueprint
description: Use when turning a validated PhysicsGuard hierarchy into a candidate model blueprint for MATLAB/Simulink or another official target-model interface without claiming recovered commercial-model equivalence.
---

# PhysicsGuard Candidate Model Blueprint

Use this route when the user asks to build a candidate model from PhysicsGuard evidence.

## Workflow

1. Start from a passed model-understanding preflight.
2. Use validated low-fidelity hierarchy blocks, interfaces, units, assumptions, and examples.
3. Generate candidate model artifacts only through official APIs, documented exchange formats, or user-owned editable templates.
4. Run the candidate model and map outputs back into PhysicsGuard observed values.
5. Use residuals and closure to decide whether the blueprint is good enough or needs refinement.

A candidate model is a new engineering artifact, not a recovered commercial-model copy.
