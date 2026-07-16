---
name: physicsguard-signal-mapping-review
description: Use when external simulation signals are mapped into PhysicsGuard variables and confidence, unit evidence, review state, or stale conditions need inspection before residuals can support fault claims.
---

# PhysicsGuard Signal Mapping Review

Use this route when external model outputs are mapped into PhysicsGuard observed values.
When the source is a concrete test data file with many fields, use
`physicsguard-test-file-contract-review` first or in parallel so every file
field has a catalog row, role/disposition, and evidence-backed mapping.

## Workflow

1. Create or review an intake file based on templates/external_model_intake.yaml.
2. Run:

   ```powershell
   python -m physicsguard.cli intake review INTAKE.yaml --pretty
   ```

3. If mappings are low confidence, missing conversion notes, review-required, or stale, review signal names, units, sign conventions, timing, and neighboring balance signals before blaming a physical parameter.

For model-dataset validation depth, the current project evidence registry and
named bundle are the consumed mapping review. Every required model input,
validation output, diagnostic check, or redundant measurement must have an
active bundle binding with unit evidence, confidence at or above the declared
threshold, and an accepted reviewer state. Bind the registry by SHA-256.
Missing units, low/unknown confidence, inactive bindings, review-required
status, bundle absence, or a changed registry blocks the broad validation
receipt or confines work to unaffected relations.

For quantitative adequacy, review the entire artifact-derived signal universe,
not only the signals selected by the validation plan. Mark critical signals and
subsystem/declared families, preserve source-row lineage and time alignment,
and ensure each selected signal has enough valid points, distinct timestamps,
span, and gap coverage for the requested scope. A missing signal needs an
explicit project-specific exclusion or remains a blocker; repeating one generic
reason across thousands of signals is not adequate coverage evidence.

Classify model parameters separately from signals. A static parameter needs a
current fact-to-parameter binding and classification source. A time-varying
parameter needs a series mapping and must independently pass per-parameter
point count/ratio, distinct timestamps, span, and maximum-gap floors; one mapped
value is not temporal coverage.

Predictive targets must have exact units, scales, step/time alignment, and
accepted mappings in both generated trajectory and future holdout. Mapping
confidence alone does not make a pointwise relation stateful or predictive.

Intake metadata does not convert or mutate observed values.
Test-file contract mapping edges likewise record evidence only; they must not
invent conversions or silently relabel observed values.

## Native skill-execution depth receipt gate

Before a broad mapping claim, issue
`python -m physicsguard.skill_execution_depth PACKAGE.json --output RECEIPT.json`
for target `physicsguard-signal-mapping-review`, owner
`physicsguard.signal-mapping-review`, and route
`route:physicsguard-signal-mapping-review:review`. Reconcile every governed
mapping and bind unit, conversion, revision, confidence/review, temporal, and
target-variable evidence. Each parameter or signal is classified static or
time-varying. A static parameter needs one exact current binding; each
time-varying parameter uses its own full time-point denominator, square-root
dynamic floor (with early/middle/late strata), and maximum-gap gate. One point
per parameter, a handful of convenient parameters, or aggregate success cannot
license the full mapping universe.
Declare critical mappings, signals, and parameters explicitly. Required or
critical objects cannot be excluded; any other exclusion needs current hashed
evidence and a closed non-contributing disposition with no mapping contribution.

Counts, signal-name lists, catalog expansion, whole-receipt hashes, and ordinal
time ranges are not per-obligation evidence. Every satisfied mapping, unit,
conversion, revision, static-binding, and temporal-depth obligation must retain
its exact target-native semantic object, `evidence_ref`, and lowercase content
hash; missing, renamed, overlapping, mechanically generated, or summary-only
mappings block the broad mapping claim.

<!-- BEGIN SKILLGUARD CONTRACT LAYER -->
## Generic SkillGuard supervision

SkillGuard supervises only the checks declared by `physicsguard-signal-mapping-review`. It freezes the exact check inventory, one execution owner per check, dependency order, governed inputs, immutable terminal receipts, installation projection, and closure. PhysicsGuard remains the sole owner of the physical/evidence purpose, prevented failure classes, native oracles, good/bad proofs, pass/block decisions, residual risk, and bounded claim.

Every declared check is mandatory unless the target contract itself removes it in a new reviewed contract. There is no selectable supervision mode, reduced-depth path, alternate authority, compatibility reader, or generic SkillGuard semantic decision. Reuse is allowed only for a current immutable receipt with the same execution identity and governed inputs. Receipt consumers verify and project; they do not rerun an owner or use `--resume` as a read-only audit. A final full gate runs once after source and tool identities freeze, never through a scheduled task or unattended retry. After timeout or interruption, evidence is invalid until the entire descendant process tree is confirmed stopped.

The only SkillGuard runtime authority is `.skillguard/contract-source.json`, `.skillguard/compiled-contract.json`, and `.skillguard/check-manifest.json`. The bundled PhysicsGuard `guard-model/` assets are family baseline regression inputs. Current model-purpose artifacts remain target-local PhysicsGuard authority and are not duplicated or semantically interpreted in SkillGuard.
The source contract uses one fixed `native-integrated` identity for the declared family baseline checks. Every declared binding is required before that baseline closure, but a baseline receipt cannot be projected as current-model proof. A real task may declare its own PhysicsGuard-native current-purpose checks for SkillGuard supervision; SkillGuard still cannot invent their semantics. Parallel success routes and SkillGuard-owned domain routes are forbidden.
<!-- END SKILLGUARD CONTRACT LAYER -->

<!-- BEGIN MANAGED PURPOSE AND BLOCKABILITY -->
## PhysicsGuard dynamic model-purpose and family baseline

Family capability baseline purpose: Prevent an external signal from being treated as a PhysicsGuard variable unless target identity, unit/conversion, revision, confidence/review, temporal coverage, and mapping evidence are current.

Family route bounded claim: A mapping pass licenses only the exact external signal, target variable, conversion, revision, temporal range, and reviewed confidence in the receipt.

Family baseline proof boundary: This guard-model proof blocks only candidate admission when declared target-native obligation evidence is missing or native-failed. It does not independently detect the underlying physical, mapping, topology, workflow, or evidence defect and does not certify upstream truth.

The bundled `guard-model/` files declare these maintained family baseline regression classes:

- `Candidate is not proven against signal and target variable mismatch` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the governed external signal does not bind to the intended PhysicsGuard variable. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against unit or conversion is invalid` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: unit evidence or conversion semantics are missing, inconsistent, or physically invalid. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against revision or temporal evidence is stale` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: revision identity or temporal coverage no longer matches the source data. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against review or confidence is unresolved` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: required review, evidence, or confidence disposition is incomplete. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.

These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.

For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.

Use `guard-model/verify.py check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.

`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.

`guard-model/verify.py` is the PhysicsGuard-native verifier. SkillGuard remains generic: it only supervises checks declared by a skill or task, owners, dependency order, current immutable receipts, installation projection, and closure; it never chooses what a model prevents.
<!-- END MANAGED PURPOSE AND BLOCKABILITY -->
