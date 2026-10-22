# PhysicsGuard AI Debugging

## Entry boundary

Accept this route when:

- An engineering-simulation result looks wrong and the fault must be localized: residual audit, coarse-to-fine refinement, competing hypotheses, next signals.
- A candidate low-fidelity model must be built from a validated hierarchy (Workflow B below).

Reject or hand off when:

- External-model boundary and inventory understanding is the whole request. Handoff: the `model-understanding-preflight` route.
- Signal identity, units, conversion, confidence, or temporal mapping is the whole request. Handoff: the `signal-mapping-review` route.
- A concrete test-data file contract is the whole request. Handoff: the `test-file-contract-review` route.
- Exact model/dataset validation is the whole request. Handoff: the `model-dataset-validation` route.

## Minimum workflow

1. If one hand-off listed above owns the complete request, hand off and stop.
2. Write or review the model-understanding preflight.
3. Map the external signals into an observed snapshot; review the intake when mappings are uncertain.
4. Run `python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml`.
5. Read the derived values, checked/unchecked relations, `top_blocks`, `recommended_refinements` and mapping issues; request the next small set of signals and refine one block. Repeat.

## Required outputs

- `localized_findings`
- `next_required_evidence`
- `bounded_claim`

Claim boundary: This route can license only a low-fidelity, evidence-bounded fault localization. It does not prove high-fidelity model truth or behavior outside the checked operating envelope.

## Purpose

Use PhysicsGuard as a transparent audit and blueprint layer for complex engineering simulations. Do not try to reproduce a full Simulink, GT-SUITE, Modelica, FMI, Amesim, MATLAB, Python, or commercial model from hidden internals. Build low-fidelity residual checks, evaluate mapped external results, rank suspicious blocks, ask for the next useful signals, and when requested, use the validated low-fidelity hierarchy as a blueprint for generating a candidate target model through official scripting interfaces.

## Visual Audit Communication

Show one compact Mermaid diagram or table only when it makes the suspicious block, the signal mapping or the next signal request clearer; skip it for short status answers.
Label what the edges mean (heat, mass, power or signal flow, `maps_to`, `refines_to`, `requires_signal`) and never draw it as a recovered high-fidelity or commercial-tool topology.
Diagrams explain the audit; they are not validation evidence. Claims come only from PhysicsGuard command output.

## Workflow A: Audit External Results

1. Clarify the visible failure: wrong final value, unstable response, impossible pressure/flow/power/heat/current/voltage, bad efficiency, or inconsistent control logic.
2. If the user asks about multiple projects, historical tests, database-level
   search, reusable model discovery across projects, or cross-project
   comparison, do not answer from this PhysicsGuard route alone. PhysicsGuard
   can inspect one project's physical evidence, contracts and validation, but
   it does not own database ledger
   intake, lifecycle, freshness, query, or navigation.
3. If the work includes a concrete testbench/test-data file, first route through
   the `test-file-contract-review` route. Generate or inspect the file
   manifest, check the file-specific contract, and do not make broad AI analysis
   claims until the contract passes. If there is no concrete test data file,
   continue with the normal model-only or observed-snapshot route.
4. When a passing test-file contract will be used to validate a model against
   that dataset, route through the `model-dataset-validation` route before
   broad model-data consistency claims. Run direct no-fit residual checks,
   physical envelope checks, redundant-sensor checks, optional conservative
   bounded calibration, holdout validation, and confidence feedback. When the
   claim spans time or scenarios, declare the dataset files, a bounded observed
   series, scenarios/perturbations, and an adequacy policy; PhysicsGuard reports
   temporal spread, per-signal depth, and time-varying parameter coverage
   shortfalls as warnings in `depth_summary`, and every warning narrows the claim.
   Do not treat a few scalar points, a few convenient signals, or optimizer
   convergence as temporal/system understanding. A `pointwise` model may
   support bounded consistency only; prediction requires a declared
   `stateful_dynamic` model and a passing disjoint future-holdout rollout.

5. Create or review a model-understanding preflight (start from `references/templates/model_understanding_preflight.yaml` in this skill's directory) before residual interpretation:

   ```powershell
   python -m physicsguard.cli preflight review PREFLIGHT.yaml
   ```

   The preflight must name the visible symptom, external model source of truth, physical boundary, subsystem blocks, conserved quantities, expected SI units, assumptions, uncertain mappings, first audit level, and stop conditions.
6. Build or choose the coarsest useful PhysicsGuard audit YAML.
7. Map external simulation signals into `ObservedValuesSpec` and, for non-trivial external-model work, review an intake record (start from `references/templates/external_model_intake.yaml`):

   ```powershell
   python -m physicsguard.cli intake review INTAKE.yaml
   ```

   AI may propose mappings, but uncertain mappings must be explicit. For new observed snapshots, prefer per-variable fields such as `external_signal`, `mapping_confidence`, `mapping_status`, `review_required`, `conversion_factor`, `conversion_note`, `mapped_at`, and `stale_when`; older metadata or Assumption Cards must be labeled as lower-confidence evidence. Intake metadata records evidence only; it does not convert or mutate observed values. `stale_when` records when a mapping needs reconfirmation; when a listed condition occurs, set `mapping_status` to `stale`.
8. Prefer direct observed evaluation:

   ```powershell
   python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml
   ```

   The snapshot may omit intermediate variables. Connections can propagate known quantities without overwriting measurements; conflicting measured endpoints remain checks. Supported `equation`, `connection`, `boundary` and `assumption` relations can derive one unknown within finite bounds. Ambiguous, flat, undefined or unsupported cases stay unknown; this bounded search does not prove arbitrary nonlinear uniqueness. `soft_check` and `post_check` never derive values.
   Dependencies belong to each residual's supported value/control sources, including zero-product and flat-branch inputs. Do not substitute numerical probing or a whole-module read union. Unsupported custom dependencies cannot license missing inputs; a custom relation may still be checked when all registered values are actually known. Remaining gaps stay in `missing_required_variables` and `unchecked_residuals`. Producing relations never count as checks, scores or top residuals. With no remaining check, the command stops with `no residual can be evaluated without them`.

9. Inspect `audit_pass`, `derived_variables`, `checked_residuals`, `unchecked_residuals`, `top_blocks`, `top_residuals`, `recommended_refinements`, `signal_mapping_ledger`, `bug_family_followups`, `missing_required_variables`, and `missing_required_parameters`. A derived value records which relation supplied it; it is not another measurement or an independent check of that relation.
   `hierarchy run|plan|evaluate|compare` print a compact summary (only mapping rows that need review); observed evaluation includes derived names and checked/unchecked counts. Add `--json` for each value's derivation, all residual names and gaps, block assignments or the full mapping ledger. CLI evaluation skips and lists still-unresolved values after derivation; the strict library default rejects them. `run` and `compare` retain their reference-solve boundaries.
   When the audit declares `fault_variants`, use model-derived device signatures before inventing fault intervals:

   ```powershell
   python -m physicsguard.cli task-model variants AUDIT.yaml NOMINAL.yaml --pairs --observed OBSERVED.yaml --write-diagnose DIAGNOSE.yaml --json
   python -m physicsguard.cli task-model diagnose DIAGNOSE.yaml
   ```

   Each variant can override `component.parameter` values and change nominal measurements; each change entry permits exactly one of `scale`, `offset`, `set` or `flip_sign`. Values listed in `rederive` are removed and derived under that variant device, then its data is checked by the nominal model. Keep the original model and observed snapshot unchanged. This is another-device evaluation, not time-forward prediction.
   Read each row's `status`, `detected`, `neutral`, `expect_blocks_met`, the `indistinguishable` groups and their `next_signal`, and any `matching_variants`. Signatures use directly checked own failures and their largest checked residual's sign. Keep a direct `thermal` failure even when that block has children; do not count an ancestor whose own checks pass. Unchecked or producing relations are not fault evidence. Identical fault signatures stay indistinguishable; the next signal must be unmeasured and ranked by scale-normalized device-value difference. A matching signature does not prove the physical cause. Variant command exit 0 means its detection/expected-block/benign checks pass; 1 means a check failed or a valid case is `not_evaluable`; 2 means invalid input. An unavailable case keeps its reason, null signature and false check flags, and cannot become a match or distinguishability result. Discrimination may still need another signal.
10. For a non-trivial diagnosis, create a task-local competing-hypothesis plan before requesting new observations (start from `references/templates/hypothesis_plan.yaml` and point `model.path` at the audited hierarchy YAML). Keep at least two live hypotheses unless the current evidence makes only one physically meaningful, and give each hypothesis at least one signal, residual, or timing expectation plus its weakening condition:

   ```powershell
   python -m physicsguard.cli task-model plan HYPOTHESIS_PLAN.yaml
   ```

   Rank the next observation from both residual relevance and the declared
   difference between hypothesis outcomes. Do not choose only the largest
   residual when a lower-residual signal distinguishes the live explanations.
11. Acquire the selected observation only after the plan is frozen, then compare
   it without rewriting the old prediction (start from `references/templates/diagnostic_observation.yaml`):

   ```powershell
   python -m physicsguard.cli task-model observe HYPOTHESIS_PLAN.yaml OBSERVATION.yaml
   ```

   Preserve supported, weakened, and undetermined hypotheses. Missing targets
   remain missing; they are not retroactive support.
12. When measurement, mapping, or low-fidelity model uncertainty is bounded by
   intervals, keep it as an interval. Use `task-model interval-residual` (start from `references/templates/interval_residual.yaml`) and
   report `robust_pass`, `robust_fail`, `indeterminate`, or `not_run`; never
   collapse an interval-crossing result into the ordinary audit pass/fail. The
   command exits 1 only on `robust_fail`.
13. For fault localization, use the existing task-local hypotheses as fault
   signatures and run `task-model diagnose` (start from `references/templates/diagnosability_request.yaml`). Report pairwise
   distinguishability, viable and rejected hypotheses, unresolved pairs, and
   the ranked next signal. The command exits 1 when the declared signatures
   cannot be separated (`indistinguishable`). The result is task-local and does
   not prove that the hypothesis inventory exhausts physical reality.
14. Use a residual localization overlay, signal-mapping table, same-family follow-up list, or refinement-path view when it helps explain why a block is suspicious and which data is needed next.
15. Request or export only the next small set of signals/parameters needed by the suspicious block and the live-hypothesis distinction.
16. Refine that block with a lower-level audit template.
17. Repeat until the problem is localized to a subsystem, component, signal chain, parameter, map, unit conversion, or boundary condition. If `bug_family_followups` names gain/sign, unit-conversion, signal-mapping, or balance siblings, inspect the sibling family before declaring the first failed residual fully localized.

Use compare mode only when a solved low-fidelity reference is intentionally useful:

```powershell
python -m physicsguard.cli hierarchy compare AUDIT.yaml OBSERVED.yaml
```

## Claim Boundary

Base the final debugging claim on the latest `hierarchy evaluate` output:

- Name the suspicious block from `top_blocks` and the residuals that support it; report `audit_pass` exactly as printed.
- Base residual evidence on `checked_residuals`; list derived values and unchecked relations separately. Never count a producing relation as its own successful check.
- List every open `recommended_refinements`, `bug_family_followups`, review-required mapping in `signal_mapping_ledger`, and `missing_required_variables` / `missing_required_parameters` entry as open.
- Never claim high-fidelity or commercial-tool equivalence; pointwise consistency is not prediction.

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
- Do not answer multi-project, historical-test, or database-level questions by
  reading only one project. State that this PhysicsGuard route does not own the
  database ledger and keep the claim scoped to checked project evidence.
- Do not treat `signal_mapping_ledger` as a conversion engine. It records evidence and review state; observed values are still used exactly as supplied.
- Do not claim a plausible parameter is wrong without residual evidence or an explicit design envelope.
- Do not generalize from a hand-picked subset. Report every adequacy warning
  (missing critical signals/parameters, temporal gaps, shallow per-signal
  histories, mass/template exclusions) and narrow the claim to the covered scope.
- Do not count one value as adequate coverage for a time-varying parameter,
  even when the overall series and other signals are deep.
- Do not describe pointwise evaluation as simulation or prediction. Prediction
  requires state propagation and an exact, disjoint future-holdout rollout.
- Do not learn by modifying PhysicsGuard itself during a diagnostic episode.
  Hypotheses, predictions, observations, mismatches, and candidate revisions
  are task-local artifacts. Core thresholds, Guard code, reusable library
  defaults, and installed skills remain unchanged.
- For GT-SUITE, Modelica, Amesim, FMI, or other external tools, use only official, user-provided, or documented interfaces; otherwise stop at the PhysicsGuard audit and explain what interface is missing.


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

Connections express physical identity: keep the tight default scale, or declare a positive finite connection `scale` for a stated small tolerance. If endpoints can physically differ, use an explicit relation module instead.

## Heated-Tank Starting Example

The repository's [heated-tank reference](https://github.com/liuyingxuvka/PhysicsGuard/tree/main/examples/hierarchical/heated_tank)
provides a reproducible non-SI CSV, coarse and six-block coupled models, an explicit
nameplate-efficiency assumption and measured-only snapshots. Use `hierarchy inspect`
to inspect its tree, then `hierarchy evaluate` to propagate connections and derive
supported intermediate values. Place measurement-to-internal components first:
the coupled example puts `heater_el` before `heater_cmd`; the coarse example puts
`inflow_mass` before `through` and the thermal balance last. This preserves the
heater-command or thermal relation as a check rather than using it to produce its
own input. Step 30 is clean; step 70 exposes the coarse thermal fault or the coupled
heater-command mismatch. Inspect the actual report and keep any remaining gaps
visible; do not supply initial guesses or hand-computed intermediate snapshots to
obtain a pass. Observed values and conversion evidence remain unchanged.

Use `python -m physicsguard.cli assumptions inspect MODEL.yaml` for explicit cards
in either a single-system model or the system wrapped by a hierarchical audit.
Inspection preserves the card rules and does not solve the model.
