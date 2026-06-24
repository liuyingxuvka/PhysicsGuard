# Changelog

## v0.10.1 - 2026-06-24

Evidence mesh release hardening.

- Added portable YAML header recognition for evidence mesh artifacts.
- Regenerated the pump-loop evidence mesh example header so committed example YAML files pass the project portability gate.

## v0.10.0 - 2026-06-24

FlowGuard-grade evidence mesh release.

- Added first-class evidence mesh schemas, review logic, YAML loading, public API export, and `physicsguard evidence mesh-check` CLI support.
- Added parent-child model mesh, model-code-test alignment, generated bad-case coverage, test mesh freshness, field lifecycle, and risk-ledger gates before broad claim readiness can pass.
- Extended project closure plans so required evidence meshes are consumed and their concrete blocking findings flow into closure reports.
- Added pump-loop evidence mesh examples, templates, docs, tests, FlowGuard route models, model-code ledger coverage, and release validation surfaces for the new claim chain.

## v0.9.1 - 2026-06-20

Windows fixture checkout hardening.

- Added `.gitattributes` so CSV fixtures keep LF line endings across Windows, macOS, and Linux checkouts.
- Kept data-file content hash validation byte-exact; no CRLF-normalizing fallback or compatibility path was added.

## v0.9.0 - 2026-06-20

DataBank extraction and PhysicsGuard database-engine removal.

- Removed the `physicsguard database ...` CLI command group without a bridge, fallback, or compatibility route.
- Removed database catalog/lifecycle core modules, schemas, templates, examples, docs, tests, and active FlowGuard model records from PhysicsGuard.
- Removed database-engine exports and loader helpers from the Python package API.
- Kept PhysicsGuard focused on physical provider evidence: test-file contracts, fields, units, parameter roles, signal mapping, model bindings, physical models, residual validation, model libraries, and project closure evidence.
- Database ledger, lifecycle, freshness, navigation, query, and cross-Guard closure now belong to the standalone DataBank package/skill.

## v0.8.0 - 2026-06-11

Explicit database lifecycle management.

- Added explicit local database initialization with policy, catalog, history, maintenance report, model-template index, README, and status handoff files.
- Added database project intake, dry-run admission, active/candidate/placeholder lifecycle states, archive/deprecate/supersede/reject operations, and append-only history events.
- Added `physicsguard database init`, `policy-check`, `template-index-check`, `intake-plan`, `admit`, `audit`, `archive`, and `render-handoff` CLI commands.
- Added database lifecycle templates, stronger catalog examples, docs, tests, FlowGuard governance, and dedicated Codex skill routes for database adoption, project intake, and maintenance.
- Updated existing PhysicsGuard skills so database build, project admission, validation updates, model-template reuse, archive, and AI handoff work route through explicit database lifecycle gates.

## v0.7.0 - 2026-06-11

Database catalog and cross-project AI map.

- Added database catalog schemas, checks, read-only refresh, gap reports, maps, and safe query filters across project evidence registries and model-library indexes.
- Added `physicsguard database check`, `scan`, `refresh`, `gap-check`, `map`, and `query` CLI commands for cross-project navigation without copying raw datasets.
- Added templates, a fixture database catalog example, documentation, tests, and FlowGuard governance.
- Updated existing PhysicsGuard skills so multi-project, historical-test, reusable-model discovery, and cross-project comparison questions start from the database catalog map and keep catalog gaps visible.
- Added project closure plans and `physicsguard project closure PLAN.yaml --pretty` so AI agents can aggregate project audit, evidence, contract, validation, model-library, and optional hierarchy closure evidence before broad final claims.
- Added project closure templates, pump-loop closure examples, tests, FlowGuard governance, and skill prompt gates so evidence maps remain navigation only and final project claims require current closure evidence.

## v0.6.0 - 2026-06-11

Project evidence registry and AI onboarding map.

- Added project evidence registries with project profiles, artifact records, engineering facts, binding records, binding expectations, context cards, evidence bundles, conflicts, and missing evidence records.
- Added `physicsguard evidence check`, `scan`, `gap-check`, `bundle-check`, and `map` commands so AI agents can find project files, project basics, model parts, test coverage, binding gaps, and explicit exemptions.
- Integrated evidence bundles with test-file contracts, model-dataset validation, and model-library reuse so blocking project evidence gaps prevent broad pass/reuse claims.
- Added templates, pump-loop examples, documentation, tests, FlowGuard governance, and a new `physicsguard-project-evidence-registry` Codex skill route.

## v0.5.0 - 2026-06-11

Model-dataset validation workflow.

- Added logical dataset records and symmetric relation indexes so large raw test files can stay in place while project metadata tracks file representations, same-run relationships, and redundant sensors.
- Added model-dataset validation plans and reports with direct no-fit residual checks, physical envelopes, redundant-sensor consistency, conservative bounded calibration, holdout validation, and confidence feedback.
- Added model-library indexes for reusable low-fidelity model assets backed by validation report evidence without storing raw datasets.
- Added `physicsguard dataset ...`, `physicsguard validation run`, and `physicsguard model-library check` CLI commands plus FlowGuard models, docs, templates, examples, tests, and Codex skill routes.

## v0.4.0 - 2026-06-10

Test file contract system.

- Added optional per-file testbench data contracts with generated `DataFileManifest`, model binding, parameter catalog, role matrix, evidence-backed mapping edges, coverage policy, project index, and contract diffing.
- Added `physicsguard testfile ...` and `physicsguard coverage check` CLI commands plus CI-friendly scripts for manifest extraction, contract checks, coverage checks, and installed skill sync checks.
- Added a dedicated `physicsguard-test-file-contract-review` Codex route and updated existing PhysicsGuard skills so concrete test data files require contract evidence while model-only workflows stay lightweight.
- Added FlowGuard models for both the test-file AI workflow and the development/release process, including gates for mapping evidence, model gaps, local install sync, and GitHub release readiness.

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
