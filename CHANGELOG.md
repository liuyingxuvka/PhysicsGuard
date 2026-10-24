# Changelog

## Unreleased

- Maintenance checks of PhysicsGuard's own model tree run on FlowGuard 0.70.12.
- hierarchy run, evaluate, compare and variants now print the audit tree with each block's verdict (failing residuals, unchecked blocks, refinement checks, next signals, fault-variant signatures and model miss); --json still prints the full report. hierarchy describe names benign variants and shows which block each assumption card applies to; its per-block count is now "declared needs missing".
- The skill starts from the model: describe the existing audit tree (or build a coarse one) before choosing a route, and read verdicts on the same tree.

## v0.15.22 - 2026-10-24 - One model tree for physics audits

- Each domain starter pack is one connected tree with fault and benign variants and a nominal snapshot. Separate level/conflict copies and their generator are removed. The heated-tank reference grows in the same file from coarse tank balances to finer blocks, with its original sparse signals retained.
- Use hierarchy run, evaluate and compare for tree and single-system files. hierarchy describe prints a readable tree; --observed counts mapped signals per block, --json keeps the full structure and --mermaid draws it. The old top-level run/evaluate/compare and hierarchy inspect commands are removed.
- Competing causes use fault_variants and hierarchy variants. Pairwise evidence and next signals distinguish causes, masked physical pairs remain visible, and --observed reports a model miss when no variant explains a failed audit. Handwritten task-model diagnosis is removed.
- Unbuilt refinement suggestions are planned and never loaded automatically. The unused refinement_template_ids block field is rejected; list next templates in refinement rules.
- External-model intake is removed. Optional source_model context belongs in snapshots or contracts; observed reports retain it and summarize mappings that need review.
- Validation reads contracted series and variable roles unless explicitly overridden. Mapping confidence uses high, medium, low or proposed. A missing input is reported once; dependent checks are marked not_run. Existing holdout, coverage and direct-validation gates remain enforced.
- Skills share one model-tree vocabulary and example headers describe audits. The old producer_receipt_id input is rejected in favor of producer_id. Maintenance uses FlowGuard 0.70.11.

## v0.15.21 - 2026-10-23

- Document the command for reading and drawing the audit model tree in the skill overview.

## v0.15.20 - 2026-10-23

- Omitted parameter strata no longer impose implicit early/middle/late requirements. Declared strata, sample coverage and native parameter-contribution checks remain active.
- Remove duplicate blocks from the deep and shallow pump validation plans while preserving their effective declarations.
- Correct the documented predictive producer field to `producer_id`; the legacy input alias remains accepted.

## v0.15.19 - 2026-10-23

### Changed

- Native interval, diagnosis, predictive rollout and validation adequacy outputs use result names and no output version field. Input validation remains in place; generated outputs are no longer passed back through output-only schemas.
- Rename the optional predictive producer identifier to `producer_id`. The older `producer_receipt_id` input remains accepted as an alias; outputs use the new name.

- Use one executable test-file contract: each field declares its role, unit, targets, confidence and evidence. Known unit pairs convert only during ingestion, with factor/offset, source and field@row retained.
- Add `testfile snapshot CONTRACT --row N` and `testfile series CONTRACT [--rows A:B]`; adjacent-row targets support single-step relations without a custom mapping script.
- Older multi-file contracts are no longer read. Rewrite them using the installed `references/templates/test_file_contract.yaml`, refresh the manifest with `testfile manifest`, then run `testfile contract-check`. Data and extractor content hashes remain authoritative.
- Remove `hierarchy plan`, `coverage check`, `dataset logical-check`, `dataset relation-check` and `testfile project-check`. Use `hierarchy run --json` for the full diagnostic and refinement report.
- Group consecutive failed series points into intervals with start/end time, worst block/residual and maximum normalized residual. Full JSON retains per-point details; summaries no longer repeat every failed point.
- Make additional adequacy floors optional. Omitted plans use manifest-derived point/time/gap facts; declared floors remain advisory. An adjacent-row contract has N-1 usable steps from N raw rows. Native mapping, scope, holdout and predictive gates remain in place.
- Let preflight and intake reviews accept `--audit` to check real block IDs, registered variables and unit compatibility.
- Add bounded unit-factor/offset hints for failed observed audits. Hints name the variable and tested conversion without changing observations or verdicts; internal batches skip hints they do not display.
- Ship an installed minimal validation-plan template and one short ordered debugging workflow; remove the duplicated protocol page.

## v0.15.18 - 2026-10-23

- `hierarchy evaluate` derives supported intermediate values from measured signals, preserves observations, and separates producing relations from independent checks and unresolved inputs.
- Fully measured balances and fixed-parameter maps remain checked when an unrelated channel is missing; native helper and per-result dependencies keep those failures visible.
- Parent verdicts include child failures while preserving local scores; `refines` links coarse and detailed components and reports their checked consistency.
- Added `fault_variants` and `task-model variants` for alternate-device data, fault signatures, next-signal suggestions and diagnosis export, with unavailable cases and physically masked combinations reported explicitly.
- Added `modules list`, `modules describe` and `hierarchy describe`, including units, parameters, residual descriptions, model ownership and optional Mermaid diagrams.
- The installed skill includes a compact model-format page and paired model/measurement templates.
- Added connected `tree.yaml` models and measured-only reference snapshots for the coolant-loop, fuel-cell and building-HVAC starter packs; existing level and conflict files remain available.
- Removed the unused block field `expected_residual_keys`; existing YAML carrying it must remove it before schema validation.
- Repository maintenance requires FlowGuard v0.70.7 or newer; ordinary runtime use remains independent of FlowGuard.

## v0.15.17 - 2026-10-22

- CLI exit codes now distinguish a passed check (0), a check that did not pass (1), and a command that could not run (2); comparisons follow the observed audit result.
- Connections now express physical identity with a tight default residual scale and an optional positive finite tolerance, keeping reference solves from absorbing faults into loose connections.
- Mapping review conditions in `stale_when` no longer mark a mapping stale by themselves; set `mapping_status: stale` when reconfirmation is needed.
- Generated manifest source paths resolve relative to the output manifest, and assumption inspection accepts hierarchical audit files.
- Added a reproducible heated-tank CSV, coarse and coupled hierarchy examples, explicit heater-efficiency assumption, and measured-only snapshots.
- Restored the diagnostic route's coverage, prediction, task-local revision and documented-interface boundaries.
- Strengthened regression models and CLI assertions, removed the tracked executor log, and cleaned redundant blank lines.

## v0.15.16 - 2026-10-21

- Done: PG-01, PG-02, PG-03, PG-04, PG-05, PG-06, PG-07, PG-08, PG-09, PG-10, PG-11, PG-12, PG-13, PG-14, PG-15, PG-16, PG-17, PG-18, PG-19, PG-20, PG-21, PG-22, PG-23, PG-24, PG-25, PG-26, PG-27, PG-28, PG-29, PG-30, PG-31, PG-32, PG-33, PG-34, PG-35, PG-36, PG-37, PG-38, PG-39, PG-40, PG-41, PG-42, PG-43, PG-44, PG-45, PG-46, PG-47, PG-48, PG-49, PG-50, PG-51, PG-52, PG-53, PG-54, PG-55, PG-56, PG-57, PG-58, PG-59, PG-60, PG-61, PG-62, PG-63, PG-64, PG-65, PG-66, PG-67, PG-68, PG-69, PG-70, PG-71, PG-72, PG-73, PG-74, PG-75.
- Skipped: none.
- One `physicsguard` skill with a route table replaces the ten skill entries. The installer copies it into `--target`
  (rmtree + copytree), removes retired skill directories, and offers `--check` and `--dry-run`.
- Removed SkillGuard-era proof machinery: route capsules, exact version gates, closure and adoption, the evidence
  registry, evidence mesh and model library, the blueprint layer and FMI, depth receipts and report-hash binding,
  task-model revision, the module-equation ledger and the self-DNA check.
- Removed the last self-proof hashes: the signal-mapping `ledger_fingerprint` (old ledgers that carry it still load)
  and the `input_fingerprint` / `request_fingerprint` echoed by `task-model interval-residual` / `diagnose`. A
  predictive rollout's `producer_receipt_id` is optional.
- The interval-diagnosability self-model also explores and replays an interval wholly outside acceptance
  (`robust_fail`), so breaking that branch of `evaluate_interval_residual` fails the model.
- The validation-plan template no longer asks for file SHA-256 values, and the predictive-rollout claim boundary
  mentions a producer receipt only when one is given.
- `hierarchy evaluate` skips only the residuals that need unobserved variables and lists those variables; an observed
  value without a unit is a mapping gap; hierarchy and validation commands print a compact summary (`--json` for the
  full report).
- Validation adequacy floors are warnings with a compact `depth_summary`; `task-model interval-residual` and
  `diagnose` exit 1 on `robust_fail` or inseparable hypotheses.
- The four self-models are FlowGuard contract models with code and test anchors, known-bad variants and replay on the
  real code; `flowguard release` passes with FlowGuard 0.70.6 and the new FlowGuard.
- Cross-repo pass: XR-04; skipped none. Details in the cross-repo action list.
- `hierarchy evaluate` with a partial snapshot also refuses residuals whose unobserved variables multiply each other or sit in a flat range check, instead of passing them from initial guesses.
- File comparisons in validation and in the skill installer compare bytes, so a rewrite with the same size and time stamp is detected.

## v0.15.15 - 2026-10-18

- Parse complete observed audit JSON in the closure helper; preserve native failures and gaps against caller overrides, and consume refinement results without an unused reference solve.
- Keep explicitly skipped required checks partial rather than granting a passed project claim scope; retain the existing skip API and native validation owners.
- Label optional execution-package diagnostics as declared shape only, with native execution not run and closure unlicensed. Preserve strict task and model-dataset validation receipts.
- Exercise real installation recovery failures and installed-byte/residual rejection; make ordinary native audit exceptions one blocked JSON at the public audit/readiness boundaries.
- Refresh current version-bound native fixtures and consumer runtime requirements, preserving historical observation dates, and use the official FlowGuard v0.70.6 consumer.

## v0.15.14 - 2026-10-18

- Let ordinary bounded native skills start without a supplied or declared blueprint, while retaining strict exact-current identity on selected blueprint paths.
- Separate initial blueprint inventory/drafts with explicit gaps from validated target-model generation eligibility, revision, and closure.
- Regenerate the ten consumer entries from their single route source, refresh live native fixture identities, and use the official FlowGuard v0.70.5 consumer.

## v0.15.13 - 2026-10-18

- Restore one blocked readiness JSON when package import raises an ordinary exception; preserve exact version and distribution-origin checks.
- Cover real malformed package imports in fresh processes and use the official FlowGuard v0.70.4 consumer.
- Record the unchanged baseline native import cycle as explicit architecture debt; retain all imports, domain owners and the remaining lint warnings.
- Refresh the current pump-loop fixture through native replays and exact artifact hashes, and renew the workflow-only project adoption record with its existing owner.

## v0.15.12 - 2026-10-17

- Retire SkillGuard author control and fixed baseline proof loops; preserve target-local current-purpose, candidate, oracle and failure-case binding.
- Generate and install the ten native consumers through ordinary transactional files and read-only sync.
- Keep ordinary tasks bounded, avoid duplicate validation output runs, load public APIs and CLI handlers on demand, and make ledger pytest execution explicit.
- Use the current FlowGuard map and fourteen real native domain models, retaining code/model/test bindings and honest not_run boundaries.
- Recompute current pump-loop native evidence and exact fixture hashes; repair source ownership for product files named test_*.py.
- Refresh stale runtime-port and framework-example byte bindings through the existing compiler, retaining unresolved roles and independent physical review requirements.

## v0.15.11 - 2026-08-12

- Refresh the native model, code, test, and evidence bindings after the
  current PhysicsGuard maintenance pass.
- Keep the repository directory as the DNA authority and preserve the
  provider-neutral target blueprint path without adding a standalone bundle
  or a routine reconstruction step.
- Publish the repaired pump-loop fixture bindings and the current FlowGuard
  0.68.14 authority under this patch identity.

## v0.15.9 - 2026-08-12

- Keep the native physical-model directory as the DNA authority, including
  models, bindings, tests, and current evidence; no self-DNA export route is
  added.
- Preserve target-owned physical blueprint projections for external objects
  while keeping them separate from the suite's own DNA.
- Refresh the ten maintained skill contracts and patch identities.

## v0.15.8 - 2026-08-11

- Keep the native physical-model directory as the DNA authority; bundle/export
  remains unavailable as an ordinary route.
- Refresh all ten maintained skill contracts, model/code/test bindings, and
  regression identities for the current FlowGuard provider and patch version.
- Preserve lightweight use while keeping every current model and validation
  binding directly inspectable in the repository.

## v0.15.7 - 2026-08-11

- Retire standalone physical-DNA transport so the native project directory is
  the sole DNA authority, with provider-neutral object observations and
  explicit bindings retained in place.

## v0.15.6 - 2026-08-10
- Synchronize the ten maintained PhysicsGuard skill projections with the
  provider-neutral FlowGuard software-DNA boundary.
- Refresh PhysicsGuard self-DNA, object-DNA qualification, code/test bindings,
  model mesh, and regression identities for the patch release.

## v0.15.5 - 2026-08-10
- Keep the ten maintained skill projections aligned with the patch release.
- Add category-aware software-scope treatment for the supporting-framework
  `DummyResidualModule` without making physical claims.
- Refresh current model, code, test, and evidence identities for the 0.15.5
  DNA snapshot; historical receipts remain immutable.

## v0.15.4 - 2026-08-10

- Refresh the PhysicsGuard package, model-regression identities, and self-DNA version bindings.
- Regenerate the maintained-skill projections from the current package identity.
- Preserve explicit native-physics ownership and visible evidence gaps.

## v0.15.3 - 2026-08-09

- Complete the PhysicsGuard family self-DNA spine with current model, code,
  test, physical-blueprint, and installation bindings.

## v0.15.2 - 2026-08-08

- Synchronized the current PhysicsGuard package, model-regression identities, and maintained-skill contracts for the patch release.
- Added the hierarchical model-mesh and model/test-alignment governance models to the current regression spine.

## v0.15.1 - 2026-08-01

- Make all ten maintained PhysicsGuard skills narrow independent entrypoints;
  keep `physicsguard-ai-debugging` only for genuinely mixed or unclear work.
- Add machine-checkable route capsules and an executable prompt-load graph so
  ordinary route selection loads only the selected compact entry and capsule.
- Move complete native purpose/depth and validated-template-pack rules behind
  conditional target-local references without weakening six-family depth,
  prediction-before-observation, `model_miss`, independent holdout, predictive
  rollout, or exact closure boundaries.
- Refresh route-specific UI metadata, FlowGuard known-bad coverage, and all ten
  generated author contracts for the contracted prompt surface.

## v0.15.0 - 2026-07-31

- Make task-local model deepening strict and receipt-driven: every non-trivial
  plan now binds its purpose, independent coverage universe, assumptions,
  unknowns, predecessor, and target-owned native depth receipt.
- Derive six gap families and their resolved, persisted, and introduced
  transitions from current native receipts instead of accepting AI-written
  gap or progress claims.
- Treat observations that contradict every declared hypothesis as a
  `model_miss`, and require regression, independent holdout, and predictive
  receipts to bind to the exact same candidate before closure.
- Refresh all ten maintained PhysicsGuard skill prompts and author contracts
  so the installed routes use the same strict task-local model lifecycle.

## v0.13.0 - 2026-07-30

- Preserve bounded observation and residual uncertainty as intervals with
  `robust_pass`, `robust_fail`, `indeterminate`, and `not_run` statuses.
- Add task-local fault signatures, pairwise detectability/isolability evidence,
  viable and rejected hypothesis inventories, unresolved pairs, and
  deterministic next-signal ranking.
- Keep diagnosability subordinate to the existing task-local
  competing-hypothesis route; it never creates a parallel audit owner or
  claims the true physical fault.
- Refresh all ten maintained skill runtime contracts to PhysicsGuard v0.13.0
  and register the new FlowGuard behavior boundary.

## v0.11.3 - 2026-07-22

- Adopt SkillGuard 0.4 bounded evidence lifecycle while preserving 74 target-owned checks across ten maintained skills.
- Remove duplicated embedded runtime, depth, and verifier copies in favor of the single installed `physicsguard` package.
- Keep legacy evidence roots fail-closed when no current lifecycle head proves safe collection.

## v0.11.2 - 2026-07-19

SkillGuard author-contract and release-identity refresh.

- Refreshed all ten private author-side SkillGuard contracts under the current
  affected-only validation and provenance ownership model.
- Synchronized package, embedded consumer runtime, templates, examples,
  project adoption identity, and installed skill projections at version
  0.11.2.
- Preserved the existing low-fidelity physics boundary and one current runtime
  path with no compatibility reader, alias, or fallback authority.

## v0.11.1 - 2026-07-18

Task-local model revision and clean consumer-runtime release.

- Added independent, task-local competing-hypothesis planning, observation
  ranking, frozen expectation comparison, and reversible candidate revision
  disposition without changing PhysicsGuard's core thresholds.
- Moved the consumer PhysicsGuard runtime out of author-only `.skillguard`
  control state and kept all ten installed skill projections directly usable.
- Upgraded the repository to FlowGuard 0.58.1 governance and retained one
  current runtime path with no compatibility reader or fallback authority.
- Removed the duplicate top-level `solve` command and the old
  `ResidualBuilder.residual_records` method; `run` and
  `diagnostic_residual_records` are now the only current entrypoints.
- Synchronized package, examples, templates, installed skills, Git tag, and
  GitHub Release at version 0.11.1.

## v0.11.0 - 2026-07-15

Purpose-declared physical audit modeling release.

- Required each candidate low-fidelity audit model to state the concrete
  physical inconsistency, invalid relation, unit/range breach, or unsupported
  mapping it is intended to block for the current task before construction.
- Added purpose, boundary, observable, counterexample, and licensed-claim
  evidence across the PhysicsGuard hierarchy, dataset validation, signal
  mapping, project evidence, model-library, blueprint, and audit-closure
  routes.
- Preserved PhysicsGuard's low-fidelity and SI-based boundary: passing an audit
  does not prove commercial-solver equivalence, physical truth, or full-system
  validity outside the declared range.
- Replaced former SkillGuard records with target-owned declared checks under
  generic SkillGuard execution supervision and fixed enforced closure.
- Updated package schemas, templates, examples, tests, OpenSpec records,
  FlowGuard evidence, and all ten maintained PhysicsGuard skills.

## v0.10.2 - 2026-06-27

- Added SkillGuard runtime-contract governance for the installed PhysicsGuard Codex skill materials.
- Synchronized installed skill copies with the canonical local source repository and local git evidence.
- Recorded release-scope validation so route selection, evidence gates, quality floors, and closure boundaries remain visible before completion claims.

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
