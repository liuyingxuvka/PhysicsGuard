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

This project uses FlowGuard for non-trivial maintenance, feature work, bug
fixes, refactors, tests, release work, project upgrades, and evidence-sensitive
process changes.

<!-- flowguard-rule:project.repository -->

FlowGuard repository:
https://github.com/liuyingxuvka/FlowGuard

<!-- flowguard-rule:skill_suite.agent_surface -->

FlowGuard agent skill suite:
- Primary agent surface: the current clean consumer projection under
  `$CODEX_HOME/skills/`; default entry is
  `$CODEX_HOME/skills/flowguard/SKILL.md`.
- A project reads this block plus selected sibling guidance; it does not copy the FlowGuard suite into its local tree.
- The Python package/CLI is executable check support, not the AI-agent skill installation surface.

<!-- flowguard-rule:project.record_locations -->

Project FlowGuard record:
- Manifest: `.flowguard/project.toml`
- Machine log: `.flowguard/adoption_log.jsonl`
- Human log: `docs/flowguard_adoption_log.md`

<!-- flowguard-rule:project.rendered_versions -->

Current adoption record:
- FlowGuard check-engine version: `0.65.1`
- FlowGuard schema version: `1.0`

<!-- flowguard-rule:project.preflight_version_gate -->

Before non-trivial work, verify the real engine/schema/version and run
`python -m flowguard project-audit --root .`. Compare it with `.flowguard/project.toml`.
If installed is newer, run `project-upgrade` with artifact/model/test upgrade scanning
and revalidate affected evidence; if installed is older, connect the current
engine before claiming confidence.

<!-- flowguard-rule:runtime.latest_schema_first -->

FlowGuard runtime guidance is latest-schema-first: old artifacts may be
detected and upgraded at project/tool boundaries, but normal route logic should
not keep long-lived old branches for obsolete fields, aliases, or wrappers.

<!-- flowguard-rule:model_system.authority -->

Only the content-addressed `observed_implementation` snapshot selected by
the sole project head is current. Targets/experiments stay isolated; discovery
or green candidate checks grant no authority. Missing/invalid authority or
required coverage blocks broad confidence.

<!-- flowguard-rule:model_system.revision_transaction -->

Replace model authority only through one accepted `ModelRevisionSet` bound
to the exact base, candidate, affected closure, changes, and current owner
evidence. Persist records before the pointer. Rollback restores/compensates real
effects and revalidates the old snapshot; irreversible effects use forward repair.

<!-- flowguard-rule:lifecycle.default_replacement -->

Default replacement means dispose the old path, old field, alias, wrapper, or
alternate success path. Delete, block, migrate, delegate, repair, replace, or
scope it out with a concrete reason; do not leave it as a second successful
route.

<!-- flowguard-rule:behavior.commitment_ledger -->

Broad behavior claims use BehaviorCommitmentLedger: independently inventory
admitted external promises, give each source one modeled/delegated/scoped
disposition, one plane/actor and one primary model owner, and send
`path_sensitive=true` rows to Primary Path Authority. Helpers are not
automatically commitments.

<!-- flowguard-rule:behavior.plane_partitioning -->

Classify each commitment as `product_runtime`, `agent_operation`, or
`development_process`. A lightweight existing-model/commitment lookup selects
a bounded same-plane owner closure; typed related-plane context never transfers
ownership. Model Miss creates a gap only when that plane has no matching promise.

<!-- flowguard-rule:behavior.commitment_ledger_modes -->

Declare ledger mode before coverage work. Only `bootstrap_ledger` and
`coverage_gap_backfill` use broad history discovery; add/change/remove/miss
work stays on the affected commitment, owner, cases, and evidence closure.

<!-- flowguard-rule:lifecycle.field_mesh -->

Field-bearing work uses FieldLifecycleMesh. High-level models keep
behavior-bearing fields; leaf inventory accounts every field's owner,
readers/writers, projection, lifecycle, evidence, and old-field disposition.

<!-- flowguard-rule:evidence.ui_and_payload -->

UI runnable claims and file/work-package claims need current UI click-through
or artifact-payload evidence gates before broad done/release confidence.

<!-- flowguard-rule:behavior.primary_path_authority -->

Path-sensitive commitments need one Primary Path Authority, visible primary
failure, no automatic alternate success, and current exhaustion/test/risk evidence.

<!-- flowguard-rule:behavior.exact_intent_reuse -->

One exact user purpose has one intent, active commitment, and primary path.
Equivalent UI/API/CLI/adapter/wrapper surfaces delegate; they do not become
independent success implementations.

<!-- flowguard-rule:ui.product_language -->

UI Flow Structure owns product-wide language and complete rendered-surface
coverage. Full UI claims inventory every control, display, transition, overlay,
recovery path, and blindspot with stable identity, evidence, and disposition.

<!-- flowguard-rule:ui.content_admission -->

Classify UI content once as `user_visible`, `user_on_demand`, or `internal`.
On-demand needs reveal/return; internal diagnostics and routing stay hidden.

<!-- flowguard-rule:process.development_process_flow -->

Plans, staged/multi-skill work, sync, release, publish, and final process
claims enter `flowguard-development-process-flow`. It owns order/freshness,
preserves peer writes, delegates semantics, uses affected revalidation, and
reserves one full gate for frozen source. Conditional strategy selection runs
only for its declared triggers; progress is never completion evidence.

<!-- flowguard-rule:process.work_context_read_only -->

External specs/plans enter only through explicit project-bounded read-only
WorkContexts. Providers keep ownership; FlowGuard preserves identities,
fingerprints, and lanes, rejects fallback/write/execution authority, and admits
behavior sources only through explicit mappings. Zero providers is valid.

<!-- flowguard-rule:process.post_change_scan -->

After non-trivial work, let DevelopmentProcessFlow consume post-change scan signals:
changed artifacts, skips, stale evidence, open obligations, and split/reduction
pressure. Route each gap to its existing specialist owner.

<!-- flowguard-rule:claim.no_fake_adoption -->

Do not create a fake local FlowGuard replacement. Do not claim full FlowGuard
completion from an AGENTS/manifest/log update alone; executable model checks,
tests, replay, and closure evidence still need to be current for the claim.
Before model build/change, freeze this instance's task-specific failures and
boundary, then bind candidate plus native good/bad-per-failure/oracle/current
evidence. Reusable types are not fixed-purpose; no mode/fallback exists; only
FlowGuard-declared checks support completion claims.

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
