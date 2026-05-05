# Changelog

## v0.1.1 - 2026-05-06

Documentation and skill workflow update.

- Added a PhysicsGuard-to-candidate-model workflow to the `physicsguard-ai-debugging` Codex skill.
- Documented how AI can use a validated PhysicsGuard hierarchy as a blueprint for MATLAB/Simulink script-generated candidate models.
- Clarified that generated target models are candidate implementations, not reverse-engineered commercial models or high-fidelity equivalents.
- Updated README positioning for AI-guided audits plus progressive model-building blueprints.

## v0.1.0 - 2026-05-06

Initial public release of PhysicsGuard Core and the `physicsguard-ai-debugging` Codex skill.

- Added YAML `SystemSpec`, residual builder, bounded solver, JSON diagnostics, observed-value evaluation, and reference comparison.
- Added hierarchical/progressive audits with block scoring, confidence heuristics, refinement recommendations, inspect/plan/run commands, and direct observed-value hierarchy evaluation.
- Added AssumptionGuard Lite with explicit assumption cards and visible assumption diagnostics.
- Added low-fidelity audit module libraries for control, thermal, fluid, electrochemical, battery/HV, drivetrain, engine, maps, and aggregate balances.
- Added a local-installable Codex skill for AI-guided PhysicsGuard debugging.
- Added examples and tests for clean and conflict audit cases.
