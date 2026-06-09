# Changelog

## v0.3.3 - 2026-06-08

AI workflow governance upgrade.

- Added PhysicsGuard project adoption/audit helpers and CLI commands so AI agents can identify the repository, package version, workflow schema, local skill routes, and adoption log before debugging.
- Added model-understanding preflight and external-model intake templates, review commands, documentation, and tests for physical boundary, signal mapping, unit evidence, assumptions, and stop conditions.
- Added a module/equation ledger plus checker so AI agents can navigate low-fidelity module families, documented equations, SI-unit expectations, tests, examples, and stale-evidence triggers.
- Strengthened closure checks, FlowGuard workflow evidence, route-oriented local skill prompts, and installed-skill sync requirements before broad PhysicsGuard localization claims.

## v0.3.2 - 2026-06-07

Guard closure maintenance upgrade.

- Added a PhysicsGuard closure helper that runs hierarchy evaluation and
  planning checks when audit and observed signal files are available.
- Updated the PhysicsGuard skill so residual, signal-mapping, assumption,
  boundary, and follow-up gaps produce explicit next actions before AI agents
  can claim a debugging pass is complete.
- Added OpenSpec and FlowGuard self-model evidence for the closure-report
  maintenance path.

## v0.3.1 - 2026-05-31

Signal mapping ledger and bug-family follow-ups.

- Added first-class observed signal mapping fields for external signal names, confidence, review status, explicit conversion evidence, mapped time, and stale conditions.
- Added hierarchy report `signal_mapping_ledger` output so mapped external values point back to PhysicsGuard variables, expected units, observed units, confidence, review issues, and recommended actions.
- Added deterministic `bug_family_followups` so one failed residual can route same-family checks such as signal mapping, gain/sign direction, unit conversion, and conservation-balance siblings.
- Updated hierarchy planning and CLI JSON output to surface mapping ledgers and follow-ups without changing or converting observed values.

## v0.3.0 - 2026-05-22

Visual audit communication update.

- Added a PhysicsGuard-specific diagram intent gate for non-trivial AI debugging, residual localization, signal mapping, assumption, refinement, and candidate-model blueprint conversations.
- Documented the PhysicsGuard visual toolbox: physical topology maps, residual localization overlays, observed-signal mapping views, assumption boundary overlays, coarse-to-fine refinement paths, and candidate-model blueprints.
- Clarified that visual diagrams explain the low-fidelity audit path but do not replace PhysicsGuard CLI reports, FlowGuard checks, pytest, example regressions, or release evidence.
- Synced the installed local Codex skill guidance with the repository skill source.

## v0.2.3 - 2026-05-22

Model-code traceability update.

- Added a FlowGuard model-code ledger that maps core lifecycle model blocks to source symbols, tests, examples, boundaries, stale-evidence conditions, and validation commands.
- Added a ledger validation script plus tests so future AI agents can detect stale model-to-code references before making model-backed changes.
- Documented the traceability workflow and release-time evidence expectations for model-backed PhysicsGuard maintenance.

## v0.2.2 - 2026-05-21

Portable model-file provenance update.

- Added portable YAML comment headers to committed PhysicsGuard audit examples, hierarchy templates, and observed snapshots.
- Added a reusable header maintenance script plus tests to keep future committed example YAML files self-describing and parseable.
- Updated skill, docs, README, package URLs, and generated starter-pack output so future YAML artifacts point back to the PhysicsGuard GitHub repository and preserve the low-fidelity SI-unit safety boundary.

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
