## PhysicsGuard Core Repository Rules

- This project is PhysicsGuard Core.
- Do not implement real physical component models unless explicitly requested.
- Use SI units internally.
- Residuals must be normalized before solving.
- Optimizer convergence is not the same as audit pass. Use `optimization_success` for numerical optimizer convergence and `audit_pass` for residual-threshold plausibility.
- All solver variables must have finite bounds, finite initial guesses inside bounds, and positive finite scales.
- Variable scales must be passed to the solver before solving.
- Diagnostics must be JSON-serializable and suitable for AI consumption.
- All core classes require tests.
- Use Python 3.11+, type hints, pydantic, numpy, scipy, pyyaml, pytest.
- Do not reverse engineer commercial simulation tools.
- Do not add external simulation-tool dependencies.
- DummyResidualModule is for framework tests only and has no physical meaning.
- Generic mathematical audit modules are framework validation utilities only; do not treat them as real physical modules.
- Real physical modules are allowed only when explicitly requested.
- Keep every physical module low-fidelity, documented, tested, and explicit about validity.
- Never add undocumented equations.
- Never imply equivalence with commercial solver internals.
- Do not let observed evaluation modify observed values.
- Do not confuse reference solve with observed audit.
- CSV and commercial-tool adapters remain future work.
- Observed values are assumed to be SI unless unit conversion is explicitly implemented later.
- Foundation modules may be added only when explicitly requested.
- Every physical module must document assumptions, limitations, units, residual equation, validity range, and diagnostic key.
- Prefer simple first-principles algebraic residuals.
- Do not add empirical correlations unless the source and validity range are documented.
- Do not add complex models without explicit request.
- Control and signal modules may be added only when explicitly requested.
- Piecewise diagnostic checks should default to post_check unless they are intended to define the solved reference model.
- Lookup-table modules must document extrapolation behavior.
- Rate-limiter modules must be single-step checks unless a real time-series evaluator is explicitly requested.
- Control, thermodynamic, humidity, rotating-machine, mechanical, and electrochemical helper modules may be added only when explicitly requested.
- Prefer simple first-principles algebraic residuals.
- Do not add empirical correlations unless the source and validity range are documented.
- Do not add saturation vapor pressure correlations unless explicitly requested.
- Do not add compressor maps, pump maps, fuel-cell polarization models, or heat-exchanger detailed maps without explicit request.
- Piecewise diagnostic checks should default to post_check unless they define the reference model.
- Every new module must document assumptions, limitations, SI units, residual equations, validity range, and diagnostic keys.
- Component-level modules may be added only when explicitly requested.
- Every component module must document residual equations, assumptions, limitations, SI units, validity range, and diagnostic keys.
- Map-based modules must document axis units, output units, and extrapolation behavior.
- Do not add compressor surge/choke models, detailed pump maps, full fuel-cell polarization physics, detailed electrolyzer models, combustion/emissions models, or thermal derating models unless explicitly requested.
- Prefer low-fidelity explicit residuals over complex empirical correlations.
- Engineering component modules may be added only when explicitly requested.
- Every engineering component module must document residual equations, assumptions, limitations, SI units, validity range, and diagnostic keys.
- Prefer simple first-principles algebraic residuals and single-step audit relations over hidden stateful solvers.
- Do not add detailed GT/Simulink/Modelica/Amesim-equivalent models.
- Do not add hidden unit conversion tables; conversion audit modules must use explicit user-provided factors and offsets.
- Map-based engineering modules must document axis units, output units, and extrapolation behavior.
- Piecewise diagnostic checks should default to post_check unless they define the solved reference model.
- Every new engineering component module must include tests and at least one example.
- Hierarchical audit features may be added only when explicitly requested.
- Hierarchical audit should support coarse-to-fine debugging with machine-readable reports.
- Hierarchical observed evaluation should substitute external values directly and must not move or solve observed values.
- Use `hierarchy evaluate` for AI-guided debugging of mapped external simulation snapshots; use `hierarchy compare` only when a solved low-fidelity reference is intentionally needed.
- Do not auto-refine or auto-execute next templates unless explicitly requested.
- Refinement rules should recommend next steps, not silently change the model.
- Block scores are diagnostic heuristics, not mathematical proof.
- Confidence scores are heuristic and must not be presented as statistical certainty.
- Do not use hierarchy features to imply commercial solver equivalence.
- Keep hierarchical reports JSON-serializable, machine-readable, and AI-consumable.
- PhysicsGuard is an AI debugging tool, not a universal automatic bug finder; AI agents may propose signal mappings and audit templates, but uncertain mappings must be recorded explicitly.
- AI agents may add narrowly scoped low-fidelity audit modules only when the relation is explicit, documented, tested, SI-based, and not a high-fidelity or commercial-tool model.
- Bug localization should proceed coarse-to-fine: visible symptom, coarse balance or relation, suspicious block, next required signals or parameters, then deeper template.
- All assumptions must be explicit Assumption Cards.
- Do not silently invent assumptions.
- Do not silently apply assumptions.
- Do not use assumptions as free optimization variables.
- Proposed assumptions must not be applied.
- Rejected assumptions must not be applied.
- High-impact assumptions must produce warnings.
- Every diagnostic report should expose assumptions.
- Do not build complex scenario or probabilistic assumption logic unless explicitly requested.
- Prefer transparency over cleverness.

<!-- BEGIN FLOWGUARD PROJECT RULES -->

<!-- flowguard-rule:project.scope -->

## FlowGuard Project Rules

For non-trivial work, select the smallest current FlowGuard public owner; clear satellites are direct peers and unclear ordinary behavior/state work uses `flowguard`.

<!-- flowguard-rule:project.repository -->

FlowGuard repository:
https://github.com/liuyingxuvka/FlowGuard

<!-- flowguard-rule:skill_suite.agent_surface -->

FlowGuard agent skill suite: Primary agent surface: the current clean consumer projection at `$CODEX_HOME/skills/flowguard/SKILL.md`; the project does not copy the FlowGuard suite into its local tree, and the Python package/CLI is not the AI-agent skill installation surface.

<!-- flowguard-rule:project.record_locations -->

Project record: `.flowguard/project.toml`; machine log: `.flowguard/adoption_log.jsonl`; human log: `docs/flowguard_adoption_log.md`.

<!-- flowguard-rule:project.rendered_versions -->

Current adoption record: FlowGuard check-engine version: `0.68.11`; FlowGuard schema version: `1.0`.

<!-- flowguard-rule:project.preflight_version_gate -->

Before non-trivial work run `python -m flowguard project-audit --root .`; if the installed engine is newer, run full `project-upgrade` scanning and affected revalidation, and if older connect the current engine.

<!-- flowguard-rule:runtime.latest_schema_first -->

Use latest-schema-first direct replacement; obsolete fields, aliases, wrappers, and alternate success paths have no normal-runtime fallback.

<!-- flowguard-rule:model_system.authority -->

Only the sole content-addressed `observed_implementation` head is current; targets, experiments, discovery, and green candidates do not own current behavior.

<!-- flowguard-rule:model_system.revision_transaction -->

Change model authority only through one accepted `ModelRevisionSet`; keep the revision-local delta distinct from its complete `CurrentEffectiveIntentView`, bind every current model owner exactly, persist evidence before the pointer, and restore/compensate effects before rollback.

<!-- flowguard-rule:lifecycle.default_replacement -->

Default replacement means dispose the old path: every replaced field, alias, wrapper, or alternate success needs an explicit delete/block/migrate/delegate/repair/replace/scope disposition.

<!-- flowguard-rule:behavior.commitment_ledger -->

Broad behavior claims require an independent BehaviorCommitmentLedger inventory, one plane and primary owner per admitted promise, and Primary Path Authority for path-sensitive rows.

<!-- flowguard-rule:behavior.plane_partitioning -->

Commitments stay in `product_runtime`, `agent_operation`, or `development_process`; select a bounded same-plane owner closure and keep related planes as typed context only.

<!-- flowguard-rule:behavior.commitment_ledger_modes -->

Declare ledger mode first; only bootstrap/backfill may discover broadly, while add/change/remove/miss stays on the affected commitment closure.

<!-- flowguard-rule:lifecycle.field_mesh -->

Field-bearing work uses FieldLifecycleMesh and accounts owner, readers/writers, projection, lifecycle evidence, and old-field disposition.

<!-- flowguard-rule:evidence.ui_and_payload -->

UI runnable claims and file/work-package claims need current real-surface or payload evidence before broad confidence.

<!-- flowguard-rule:behavior.primary_path_authority -->

Commitments with `path_sensitive=true` need one Primary Path Authority, visible primary failure, no alternate automatic success, and current exhaustion/test/risk evidence.

<!-- flowguard-rule:behavior.exact_intent_reuse -->

One exact purpose has one intent, commitment, and primary path; equivalent UI/API/CLI/adapter/wrapper surfaces delegate rather than own independent success.

<!-- flowguard-rule:ui.product_language -->

UI Flow Structure owns product language and complete rendered control/display/transition/overlay/recovery/blindspot coverage for full UI claims.

<!-- flowguard-rule:ui.content_admission -->

Classify UI content once as `user_visible`, `user_on_demand`, or `internal`; on-demand needs reveal/return and internal diagnostics stay hidden.

<!-- flowguard-rule:process.development_process_flow -->

Plans, staged/multi-skill work, sync, release, publish, and final process claims use `flowguard-development-process-flow`: start with lightweight existing-model/commitment lookup, preserve peers, revalidate affected owners, and reserve one full gate for frozen source.

<!-- flowguard-rule:process.work_context_read_only -->

External specs/plans are optional project-bounded read-only WorkContexts; providers retain identity, lane, execution, validation, and lifecycle authority.

<!-- flowguard-rule:process.post_change_scan -->

DevelopmentProcessFlow consumes post-change scan signals—changed, skipped, stale, open, split, or reduction—and routes each to its existing specialist.

<!-- flowguard-rule:claim.no_fake_adoption -->

Do not create a fake local FlowGuard replacement. AGENTS/manifest/log changes are not proof: freeze task-specific failures and boundary, bind native good/bad-per-failure/oracle/current evidence, and let only declared checks support completion.

<!-- END FLOWGUARD PROJECT RULES -->


<!-- BEGIN MANAGED SKILLGUARD AUTHOR RULES -->
## SkillGuard author maintenance

This repository is an explicit skill-authoring workspace. Use SkillGuard only while maintaining, validating, graduating, or releasing the managed source skills below.

Canonical SkillGuard repository: https://github.com/liuyingxuvka/SkillGuard

Managed skills:
- `skill/physicsguard-ai-debugging` — native owner=`physicsguard.ai-debugging`, maintenance unit=`unit:physicsguard-family`, route evidence=`skill/physicsguard-ai-debugging/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `skill/physicsguard-audit-closure` — native owner=`physicsguard.audit-closure`, maintenance unit=`unit:physicsguard-family`, route evidence=`skill/physicsguard-audit-closure/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `skill/physicsguard-candidate-model-blueprint` — native owner=`physicsguard.candidate-model-blueprint`, maintenance unit=`unit:physicsguard-family`, route evidence=`skill/physicsguard-candidate-model-blueprint/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `skill/physicsguard-model-dataset-validation` — native owner=`physicsguard-model-dataset-validation`, maintenance unit=`unit:physicsguard-family`, route evidence=`skill/physicsguard-model-dataset-validation/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `skill/physicsguard-model-library` — native owner=`physicsguard.model-library`, maintenance unit=`unit:physicsguard-family`, route evidence=`skill/physicsguard-model-library/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `skill/physicsguard-model-understanding-preflight` — native owner=`physicsguard.model-understanding-preflight`, maintenance unit=`unit:physicsguard-family`, route evidence=`skill/physicsguard-model-understanding-preflight/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `skill/physicsguard-project-adoption` — native owner=`physicsguard.project-adoption`, maintenance unit=`unit:physicsguard-family`, route evidence=`skill/physicsguard-project-adoption/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `skill/physicsguard-project-evidence-registry` — native owner=`physicsguard.project-evidence-registry`, maintenance unit=`unit:physicsguard-family`, route evidence=`skill/physicsguard-project-evidence-registry/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `skill/physicsguard-signal-mapping-review` — native owner=`physicsguard.signal-mapping-review`, maintenance unit=`unit:physicsguard-family`, route evidence=`skill/physicsguard-signal-mapping-review/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `skill/physicsguard-test-file-contract-review` — native owner=`physicsguard.test-file-contract-review`, maintenance unit=`unit:physicsguard-family`, route evidence=`skill/physicsguard-test-file-contract-review/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.

Required maintenance handoff:

1. Read the target skill's `SKILL.md` and its native route/check contracts before editing.
2. Use SkillGuard to inventory, run every target-declared check, reconcile exact receipts, and close non-trivial skill changes.
3. Preserve the target's sole current native route and exact declared checks; SkillGuard never supplies a target-domain route.
4. Never let SkillGuard replace target-owned domain judgment, simulation, search, modeling, actions, or checks.
5. Do not claim complete use from contract presence alone; require a current declared-check execution receipt.
6. Never copy this block, the author manifest, contracts, receipts, router state, or Portfolio state into a graduated consumer skill or an ordinary business project.
7. If SkillGuard is unavailable or this block/manifest is missing, stale, duplicated, or invalid, report only author maintenance as blocked; ordinary consumer use remains independent.

Validation execution ownership:

- policy_id: `skillguard.validation_execution_ownership.current`
- Creating, updating, directly rewriting, installing/synchronizing, or releasing an explicitly registered maintained skill source requires SkillGuard author-side supervision; no migration or compatibility route exists.
- Covered skill maintenance uses direct current replacement. Do not add a compatibility reader, fallback, migration or upgrade command, converter, alias, renewal path, dual manifest, or parallel authority. An ordinary software historical reader is allowed only when an explicit requirement names the old document/data/interface and FlowGuard records its bounded owner and claim boundary.
- Ordinary use of an installed consumer skill for its domain work does not start SkillGuard maintenance or validation and must not require SkillGuard files, imports, commands, receipts, or router state.
- SkillGuard supervises the author-side frozen owner plan, receipts, affected-only revalidation, clean consumer projection, and closure; the target skill retains its domain actions, judgment, and native-check authority.
- Before validating one maintenance unit, freeze its unit id, member ids, exact semantic checks, evidence subjects, covered obligations/domains, dependency order, private receipt root, and exactly one execution owner per check; missing, duplicate, foreign-unit, or cyclic ownership blocks execution.
- Reuse one immutable terminal-success producer receipt only inside the same maintenance unit when unit, member, explicitly declared owner, request, inputs, dependencies, toolchain, and environment are all exact. Each semantic check keeps its own subject, domain, obligations, and projection identity. A different unit must execute and own its own evidence even when command text and inputs look identical.
- Consumer distributions contain no SkillGuard receipt reference or execution-owner projection. They run their target-owned checks directly when their own workflow requires them.
- Compile the complete maintained inventory into exact content components before validation. A change invalidates only owners and projections that explicitly consume its changed component; an unmapped or ambiguous file blocks instead of falling back to run-all.
- Treat maintained test, code, contract, configuration, toolchain, and policy changes as freshness inputs only through those exact component edges. Reports, receipts, progress logs, checkboxes, and other runtime outputs are evidence outputs and must not refresh source authority or trigger their own validation.
- Installation consumes only the frozen `projection:installation`; source-only tests, fixtures, models, and notes do not make an installation stale. A read-only installation currentness check never launches smoke or another validation owner.
- Treat `--resume` as an execution command that may run missing owners; it is never a read-only receipt audit, and a receipt consumer must not invoke it.
- Start exactly one final full validation for the maintenance unit only after its source, toolchain, and impact-plan identities are frozen, under one explicit execution owner. Other maintenance units and consumers do not consume that parent receipt.
- After any launcher timeout, cancellation, or interruption, confirm the entire descendant process tree count is zero before accepting evidence or starting another owner; `cleanup-unconfirmed` results are invalid and non-reusable.
- Never use a Windows Scheduled Task, background resume, or unattended retry script to run full validation or resume a mutable worktree.

Author audit command: `python <installed-skillguard>/scripts/skillguard.py maintainer-audit --root .`

This managed block is a routing and maintenance contract. It is not runtime, test, release, or future-behavior proof.
<!-- END MANAGED SKILLGUARD AUTHOR RULES -->
