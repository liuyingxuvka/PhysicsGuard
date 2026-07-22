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
2. If the user asks about multiple projects, historical tests, database-level
   search, reusable model discovery across projects, or cross-project
   comparison, do not answer from this PhysicsGuard route alone. PhysicsGuard
   can inspect one project's physical evidence, contracts, validation, model
   library records, and closure boundary, but it does not own database ledger
   intake, lifecycle, freshness, query, or navigation.
3. If the work includes a concrete testbench/test-data file, first route through
   `physicsguard-test-file-contract-review`. Generate or inspect the file
   manifest, check the file-specific contract, and do not make broad AI analysis
   claims until the contract passes. If there is no concrete test data file,
   continue with the normal model-only or observed-snapshot route.
5. For project-level work with multiple files, source documents, physical
   parameters, validation bundles, reusable models, or AI handoff needs, route
   through `physicsguard-project-evidence-registry`. Run `evidence map` early so
   the AI can see the project profile, file map, model parts, test coverage,
   binding expectations, explicit exemptions, and open gaps. Do not hide missing
   project name, run period, location, physical-parameter binding, or test-field
   binding gaps.
6. When a passing test-file contract will be used to validate a model against
   that dataset, route through `physicsguard-model-dataset-validation` before
   broad model-data consistency claims. Run direct no-fit residual checks,
   physical envelope checks, redundant-sensor checks, optional conservative
   bounded calibration, holdout validation, and confidence feedback. When the
   claim spans time or scenarios, require exact dataset/mapping identities,
   a bounded observed series, declared scenarios/perturbations, pointwise
   residuals and envelopes, and passing native depth and adequacy receipts.
   The adequacy gate must derive the available universe from current hashed
   project artifacts and check temporal spread, per-signal depth, critical
   signals/parameters, subsystem or declared family quotas, and exclusions.
   Every available parameter must be source-classified as static or
   time-varying; a time-varying parameter must pass its own growing native,
   project, and convergence time-depth floors and prove that its observed
   values reach executable model residuals (or carry a bounded verified-
   non-sensitive disposition), while a static parameter needs current binding
   evidence.
   Do not treat a few scalar points, a few convenient signals, or optimizer
   convergence as temporal/system understanding. A `pointwise` model may
   support bounded consistency only; prediction requires a declared
   `stateful_dynamic` model and a passing disjoint future-holdout rollout.
7. Check project adoption when working inside a repository:

   ```powershell
   python -m physicsguard.cli project audit --pretty
   ```

   If adoption is missing and setup is in scope, run `project adopt` or `project upgrade`. Project adoption is workflow evidence only.
8. Create or review a model-understanding preflight before residual interpretation:

   ```powershell
   python -m physicsguard.cli preflight review PREFLIGHT.yaml --pretty
   ```

   The preflight must name the visible symptom, external model source of truth, physical boundary, subsystem blocks, conserved quantities, expected SI units, assumptions, uncertain mappings, first audit level, and stop conditions.
9. Build or choose the coarsest useful PhysicsGuard audit YAML.
10. Map external simulation signals into `ObservedValuesSpec` and, for non-trivial external-model work, review an intake record:

   ```powershell
   python -m physicsguard.cli intake review INTAKE.yaml --pretty
   ```

   AI may propose mappings, but uncertain mappings must be explicit. For new observed snapshots, prefer per-variable fields such as `external_signal`, `mapping_confidence`, `mapping_status`, `review_required`, `conversion_factor`, `conversion_note`, `mapped_at`, and `stale_when`; older metadata or Assumption Cards must be labeled as lower-confidence evidence. Intake metadata records evidence only; it does not convert or mutate observed values.
11. Prefer direct observed evaluation:

   ```powershell
   python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml --pretty
   ```

12. Inspect `audit_pass`, `top_blocks`, `top_residuals`, `recommended_refinements`, `signal_mapping_ledger`, `bug_family_followups`, `missing_required_variables`, and `missing_required_parameters`.
13. For a non-trivial diagnosis, create a task-local competing-hypothesis plan before requesting new observations. Keep at least two live hypotheses unless the current evidence makes only one physically meaningful, and freeze each hypothesis's signal, residual, and timing expectations plus its weakening condition:

   ```powershell
   python -m physicsguard.cli task-model plan HYPOTHESIS_PLAN.yaml --pretty
   ```

   Rank the next observation from both residual relevance and the declared
   difference between hypothesis outcomes. Do not choose only the largest
   residual when a lower-residual signal distinguishes the live explanations.
14. Acquire the selected observation only after the plan is frozen, then compare
   it without rewriting the old prediction:

   ```powershell
   python -m physicsguard.cli task-model observe HYPOTHESIS_PLAN.yaml OBSERVATION.yaml --pretty
   ```

   Preserve supported, weakened, and undetermined hypotheses. Missing targets
   remain missing; they are not retroactive support.
15. Use a residual localization overlay, signal-mapping table, same-family follow-up list, project-evidence map, or refinement-path view when it helps explain why a block is suspicious and which data is needed next.
16. Request or export only the next small set of signals/parameters needed by the suspicious block and the live-hypothesis distinction.
17. Refine that block with a lower-level audit template.
18. Repeat until the problem is localized to a subsystem, component, signal chain, parameter, map, unit conversion, or boundary condition. If `bug_family_followups` names gain/sign, unit-conversion, signal-mapping, or balance siblings, inspect the sibling family before declaring the first failed residual fully localized.

Use compare mode only when a solved low-fidelity reference is intentionally useful:

```powershell
python -m physicsguard.cli hierarchy compare AUDIT.yaml OBSERVED.yaml --pretty
```

Before claiming the audit is localized or complete, run the closure helper when
available. A partial, blocked, downgraded, stale, skipped, or mapping-review
closure must downgrade the final claim:

```powershell
python scripts\physicsguard_closure_check.py --ledger <physicsguard-closure-ledger.json> --audit AUDIT.yaml --observed OBSERVED.yaml --json
```

For project-level debugging with evidence registries, test contracts,
validation plans, model libraries, external database-ledger inputs, or reusable handoff
claims, also run or inspect:

```powershell
python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
```

Carry the project closure `closure_status` into the final claim. Do not say the
project is complete, validated, reusable, or localization-ready from an
evidence map alone. For validation-ready claims, closure must consume a passing
native depth receipt; it must not recreate physical residual logic in a
supervisory skill. A prediction claim additionally requires
`claim_scope: prediction_ready`, stateful semantics, and a passing native
predictive-rollout receipt with stability evidence.

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
- Do not leave project-level basics or binding maintenance implicit. Project
  name, run period, location, test-field bindings, physical-parameter bindings,
  and explicit binding exemptions belong in the project evidence registry when
  project evidence work is in scope.
- Do not answer multi-project, historical-test, or database-level questions by
  reading only one project. State that this PhysicsGuard route does not own the
  database ledger and keep the claim scoped to checked project evidence.
- Do not treat `signal_mapping_ledger` as a conversion engine. It records evidence and review state; observed values are still used exactly as supplied.
- Do not claim a plausible parameter is wrong without residual evidence or an explicit design envelope.
- Do not generalize from a hand-picked subset until the native adequacy receipt
  passes for the requested scope. Missing critical signals/parameters,
  temporal gaps, shallow per-signal histories, or mass/template exclusions are
  blockers, not prose caveats.
- Do not count one value as adequate coverage for a time-varying parameter,
  even when the overall series and other signals are deep.
- Do not describe pointwise evaluation as simulation or prediction. Prediction
  requires state propagation and an exact, disjoint future-holdout rollout.
- Do not learn by modifying PhysicsGuard itself during a diagnostic episode.
  Hypotheses, predictions, observations, mismatches, and candidate revisions
  are task-local artifacts. Core thresholds, Guard code, reusable library
  defaults, and installed skills remain unchanged.
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

## Native skill-execution depth receipt gate

Before claiming a broad AI-debugging result, issue the target-owned receipt with
`python -m physicsguard.skill_execution_depth PACKAGE.json --output RECEIPT.json`.
The package must use target `physicsguard-ai-debugging`, owner
`physicsguard.ai-debugging`, and route
`route:physicsguard-ai-debugging:audit`. It must reconcile the complete
declared/discovered/required physical-object universe, provide current evidence
for the visible symptom, boundary, topology, mappings, validation depth,
localization, assumptions, and safe claim, and include one per-object result for
every eligible signal, parameter, component, or artifact. Each time-varying
object is checked against its own full time-point denominator, dynamic sampling
floor, early/middle/late distribution, and maximum gap. A few convenient
scalars, aggregate averages, generic obligations, or a calibration fixture do
not license a real audit claim. PhysicsGuard's current native receipt remains
the audit authority and cannot be replaced by a generic summary.
The package must declare the critical-object denominator explicitly. A critical
or required object cannot be excluded; any other exclusion needs current hashed
evidence plus a closed non-contributing disposition and contributes no claim evidence.

Counts, object-name lists, catalog expansion, whole-receipt hashes, and ordinal
ranges are not per-obligation evidence. Every satisfied physical-object
obligation must retain its exact target-native semantic object, `evidence_ref`,
and lowercase content hash; missing, renamed, overlapping, mechanically generated,
or summary-only mappings block a broad debugging claim.



<!-- BEGIN MANAGED VALIDATED TEMPLATE PACK -->
## Validated Template Pack Routing

- Target families: `physicsguard`; native owner: `physicsguard.purpose-pack-selector.v1`.
- Current catalogs: `physicsguard.purpose-template-packs` revision `1`.
- Resolve the task through this Guard's native router first, then ask the target-owned adapter for a current neutral projection; never infer a template from wording or a skill name.
- Preserve the adapter's complete candidate and rejection accounting. Zero candidates may use only the declared validated base; one candidate gets a read-only preview; many candidates require complete dependencies, pairwise compatibility, one field owner, and target-authored dominance or must block as ambiguous.
- Recompute the projection immediately before applying a preview. A stale request, catalog, route, builder, validator, or content identity blocks all writes.
- Hand the selected preview to the target-declared builder and consume every target-native validator receipt. Template structure is not domain validity, completion, installation, release, or publication evidence.
- Record a harvest disposition after creating or materially deepening a reusable model, and keep no-match evidence visible.
- Declared validated bases: `physicsguard.base.audit-work-package`.
- Template inventory: `physicsguard.base.audit-work-package`, `physicsguard.dataset-validation-basic`, `physicsguard.dataset-validation-comprehensive`, `physicsguard.model-understanding-preflight`, `physicsguard.signal-mapping-core`, `physicsguard.signal-mapping-evidence`.
- Native validator inventory: `physicsguard.template-pack-instance-validator.v1`, `physicsguard.template-pack-manifest-validator.v1`, `physicsguard.template-pack-selection-validator.v1`.
- Claim boundaries: The catalog supports deterministic workflow-pack selection and structural native validation only; physical truth, dataset adequacy, audit_pass, installation, and release require separate current PhysicsGuard evidence.
<!-- END MANAGED VALIDATED TEMPLATE PACK -->

<!-- BEGIN MANAGED PURPOSE AND BLOCKABILITY -->
## PhysicsGuard dynamic model-purpose and family baseline

Family capability baseline purpose: Localize a visible engineering-simulation fault only when current physical boundaries, topology, mappings, residuals, assumptions, and evidence depth support that localization.

Family route bounded claim: This route can license only a low-fidelity, evidence-bounded fault localization. It does not prove high-fidelity model truth or behavior outside the checked operating envelope.

Family baseline proof boundary: This guard-model proof blocks only candidate admission when declared target-native obligation evidence is missing or native-failed. It does not independently detect the underlying physical, mapping, topology, workflow, or evidence defect and does not certify upstream truth.

Shared simulator prerequisite: install the current `physicsguard==0.11.3` package in the active Python environment. Before executing this skill, run `python -c "import physicsguard; print(physicsguard.__version__)"`; a missing package is a visible blocker and there is no bundled fallback.

Issue target-owned execution-depth receipts with `python -m physicsguard.skill_execution_depth PACKAGE.json --output RECEIPT.json`. The package module is the sole editable depth implementation shared by all ten skills.

The bundled `guard-model/` files declare these maintained family baseline regression classes:

- `Candidate is not proven against symptom or residual mislocalized` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the visible symptom, failing subsystem, or residual source is not supported by current native evidence. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against physical boundary or topology violation` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: units, signs, balances, connectivity, or declared physical boundaries are inconsistent. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against signal or parameter mapping is wrong` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: a signal, parameter, revision, conversion, or target variable binding is missing, stale, or inconsistent. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against validation evidence is too shallow` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the available object, signal, parameter, scenario, or time universe is not adequately evaluated. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against assumption or claim scope is overreached` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: an unresolved assumption, access gap, or bounded result is promoted beyond the checked scope. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.

These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.

For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.

Use `python -m physicsguard.guard_model_contract check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.

`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.

`physicsguard.guard_model_contract` is the PhysicsGuard-native verifier. It proves only the declared family baseline and never replaces current task evidence or PhysicsGuard domain judgment.
<!-- END MANAGED PURPOSE AND BLOCKABILITY -->
