# Changelog

## v0.2.1 - 2026-05-18

Skill workflow header update.

- Updated the `physicsguard-ai-debugging` Codex skill to require a short one-layer comment header on newly created PhysicsGuard YAML audits, hierarchy templates, observed snapshots, and candidate-model blueprints.
- Documented that the header should stay comment-only unless a task already needs schema metadata for another reason.
- Updated README skill guidance to mention the new header behavior.

## v0.2.0 - 2026-05-12

Expanded low-fidelity starter-pack coverage.

- Added `MappedSignalModule` for externally mapped audit variables.
- Added starter-pack guidance plus runnable hierarchy templates for wastewater treatment, renewable microgrids, building HVAC, distribution power/DER, process industry, stormwater/sewer/drainage, industrial utilities, data centers/electronics cooling, mobility extensions, and agriculture/food/bioprocess.
- Added expanded coverage templates for cross-domain audit primitives, oil/gas pipeline and storage, water supply networks, manufacturing thermal processes, mining/metallurgy, combustion boiler/furnace, geothermal wells, cold-chain logistics, robotics/mechatronics, aerospace/satellite thermal, and medical/bioprocess equipment.
- Added generated clean Level 0, conflict Level 0, and Level 1 starter-pack templates with regression tests.
- Clarified that starter packs remain low-fidelity audit templates and do not implement high-fidelity physical models or commercial-tool-equivalent solvers.

## v0.1.3 - 2026-05-06

Repository naming update.

- Renamed the public GitHub repository from `physicsguard-core` to `PhysicsGuard`.
- Updated README skill-install guidance to use the new repository URL.

## v0.1.2 - 2026-05-06

README presentation update.

- Replaced the generated diagram-style README hero with a text-to-image concept hero.
- Simplified skill installation guidance: users can give the GitHub repository URL to their AI agent and ask it to install `skill/physicsguard-ai-debugging`.

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
