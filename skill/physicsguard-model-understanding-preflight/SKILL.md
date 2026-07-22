---
name: physicsguard-model-understanding-preflight
description: Use before PhysicsGuard audits of external models to capture visible symptom, physical boundary, subsystem blocks, units, assumptions, uncertain mappings, and stop conditions.
---

# PhysicsGuard Model Understanding Preflight

Use this route before interpreting residuals for a non-trivial external model.
If a concrete testbench data file is part of the work, record the file/bench
boundary and route to `physicsguard-test-file-contract-review` before broad
analysis claims.

## Workflow

1. Create or review a preflight file based on templates/model_understanding_preflight.yaml.
2. Run:

   ```powershell
   python -m physicsguard.cli preflight review PREFLIGHT.yaml --pretty
   ```

3. If missing inputs or uncertain mappings are reported, complete them or route to signal mapping review before fault claims.
4. Before planning validation, name the intended claim scope and model
   semantics (`pointwise` or `stateful_dynamic`). Identify the authoritative
   manifest, role matrix, hierarchy, evidence registry/bundle, available time
   range, operating modes, important events/peaks/boundaries, critical
   signals/parameters, subsystem families, and the project source for
   quantitative adequacy thresholds. Classify each available model parameter
   as static or time-varying from a named source; identify the series mapping
   for every time-varying parameter. Unknowns stay explicit.
5. If prediction is intended, confirm that an official or user-owned execution
   route can preserve initial state and step semantics and produce an exact
   trajectory plus disjoint future holdout. Without that route, stop at bounded
   pointwise validation or a candidate-model blueprint.

Preflight pass is planning evidence only. It is not residual validation.

## Native skill-execution depth receipt gate

Before claiming that the external model is sufficiently understood, issue
`python -m physicsguard.skill_execution_depth PACKAGE.json --output RECEIPT.json`
for target `physicsguard-model-understanding-preflight`, owner
`physicsguard.model-understanding-preflight`, and route
`route:physicsguard-model-understanding-preflight:review`. The package must
cover the visible symptom, physical boundary, complete subsystem/signal/
parameter/assumption inventory, and unresolved access gaps. Every governed
signal and parameter must be classified static or time-varying; each
time-varying object uses its own full denominator, dynamic point floor,
early/middle/late coverage, and maximum-gap gate. A cursory diagram or two
sampled parameters is not model understanding.
Declare the critical-object denominator explicitly. Required or critical
subsystems, signals, parameters, and assumptions cannot be excluded; another
exclusion needs current hashed evidence and a closed non-contributing disposition.

Counts, object-name lists, catalog expansion, whole-receipt hashes, and ordinal
time ranges are not per-obligation evidence. Every satisfied subsystem, signal,
parameter, assumption, and temporal-depth obligation must retain its exact
target-native semantic object, `evidence_ref`, and lowercase content hash;
missing, renamed, overlapping, mechanically generated, or summary-only mappings
block a model-understanding claim.



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

Family capability baseline purpose: Prevent physical audit or modeling work from starting with an unclear symptom, physical boundary, subsystem, signal, parameter, assumption, or access universe.

Family route bounded claim: Preflight licenses only that the declared low-fidelity audit boundary is sufficiently understood to proceed; unresolved access or inventory gaps remain visible blockers.

Family baseline proof boundary: This guard-model proof blocks only candidate admission when declared target-native obligation evidence is missing or native-failed. It does not independently detect the underlying physical, mapping, topology, workflow, or evidence defect and does not certify upstream truth.

Shared simulator prerequisite: install the current `physicsguard==0.11.3` package in the active Python environment. Before executing this skill, run `python -c "import physicsguard; print(physicsguard.__version__)"`; a missing package is a visible blocker and there is no bundled fallback.

Issue target-owned execution-depth receipts with `python -m physicsguard.skill_execution_depth PACKAGE.json --output RECEIPT.json`. The package module is the sole editable depth implementation shared by all ten skills.

The bundled `guard-model/` files declare these maintained family baseline regression classes:

- `Candidate is not proven against symptom or physical boundary is unclear` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the visible symptom, units, operating boundary, or subsystem scope is missing. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against required model inventory is missing` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: required subsystems, signals, or parameters are absent from the discovered universe. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against assumption is hidden` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: a material model or operating assumption is missing or unresolved. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against access gap is suppressed` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: unavailable model, signal, parameter, or evidence access is not reported. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.

These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.

For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.

Use `python -m physicsguard.guard_model_contract check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.

`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.

`physicsguard.guard_model_contract` is the PhysicsGuard-native verifier. It proves only the declared family baseline and never replaces current task evidence or PhysicsGuard domain judgment.
<!-- END MANAGED PURPOSE AND BLOCKABILITY -->
