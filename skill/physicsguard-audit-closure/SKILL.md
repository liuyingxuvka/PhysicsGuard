---
name: physicsguard-audit-closure
description: Use before claiming PhysicsGuard localized a fault or completed an audit; checks audit pass/fail, missing inputs, mapping review, stale evidence, skipped checks, refinements, and same-family follow-ups.
---

# PhysicsGuard Audit Closure

Use this route before final localization or completion claims.

For project-level completion, validation, reuse, or localization claims, prefer
the project closure gate first:

```powershell
python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
```

Do not treat a project evidence map as proof. The map is navigation; the
project closure report decides whether current route evidence supports a
`passed`, `partial`, `downgraded`, or `blocked` claim.

Run:

```powershell
python <physicsguard-ai-debugging skill directory>\scripts\physicsguard_closure_check.py --ledger CLOSURE.json --audit AUDIT.yaml --observed OBSERVED.yaml --json
```

Blocking or downgrading evidence includes failed audit, missing variables or parameters, review-required mappings, stale evidence, skipped checks, open refinements, and same-family follow-ups.
For workflows that include concrete test data files, also treat missing,
partial, stale, or failing test-file contracts as blocking or downgrading
evidence. A residual report cannot make a broad claim from a file whose fields
are not fully cataloged, classified, and evidence-mapped.

For project-level workflows, also read the project evidence map or gap report.
Missing project profile basics, unregistered important files, unresolved
blocking evidence gaps, missing binding summaries, unreviewed physical
parameter bindings, or test-field binding expectations without bindings or
exemptions downgrade or block broad claims.
If a project closure report exists, carry its `closure_status`, `safe_claim`,
`unsafe_claim_boundary`, skipped checks, and next actions into the final answer.
If no report exists for a broad project claim, run it or explicitly downgrade
the claim.

For workflows that validate a model against contracted test data, also read the
model-dataset validation report. Missing, partial, failed, stale, or blocked
validation reports downgrade or block broad model-data consistency claims. Treat
`optimization_success` as numerical optimizer evidence only; it is not
`audit_pass`, holdout pass, or final validation pass. Parameter-at-bound
warnings, low validation confidence, failed physical envelopes, redundant-sensor
mismatches, and review-required confidence updates must remain visible in the
final claim boundary.

For `validation_ready` or `validated_reuse_ready`, require
`required_checks.validation_depth: true`. The validation plan must emit a
passing `physicsguard_validation_depth_receipt` bound to its report type,
status, and SHA-256. Closure consumes that receipt without recomputing physics;
missing/stale/partial/blocked receipts, snapshot overclaim, uncertain mappings,
split overlap, invalid intervals, or hard envelope intervals block the broad
claim.

The native receipt must also contain a passing quantitative adequacy gate for
every non-snapshot claim. Verify that `covered_scope` is compatible with the
requested scope and that the receipt accounts the artifact-derived point,
signal, and parameter universe; temporal strata/gaps; per-signal histories;
source-backed static/time-varying parameter classifications; each time-varying
parameter's own resolved native/project/convergence floor, strata and row-gap
receipt; counterfactual proof that observed values affect executable model
residuals or an exact bounded non-sensitive disposition; critical members and
families; and explicit exclusions. A snapshot or shallow
subset cannot close validation or reuse readiness merely because its evaluated
points passed.

For `prediction_ready`, additionally require
`required_checks.predictive_rollout: true`, `stateful_dynamic` semantics, an
exact training/prediction/future-holdout identity chain, and a passing native
rollout receipt whose stability and error-growth checks pass. A pointwise model
or an in-sample/overlapping holdout blocks prediction closure.

For database-level or cross-project claims, do not answer from this closure
route alone. Missing project registries, stale external summaries, propagated
project evidence blocking gaps, or unknown comparison scope block broad
historical, reuse, or direct-comparison conclusions.

Closure pass supports only a scoped low-fidelity claim inside the checked audit
or project closure boundary.

## Native skill-execution depth receipt gate

Before broad audit closure, issue
`python runtime/skill_execution_depth.py PACKAGE.json --output RECEIPT.json`
for target `physicsguard-audit-closure`, owner
`physicsguard.audit-closure`, and route
`route:physicsguard-audit-closure:close`. The current package must bind the
closure plan, every required native check, the native validation-depth receipt,
blocker reconciliation, stale and skipped evidence, any requested predictive
rollout, and the safe claim boundary. It must reconcile the complete governed
closure-object universe and cannot promote a locally green, stale, skipped, or
fixture-only result. PhysicsGuard verifies the receipt and its current identity
and retains closure authority.
Declare critical closure objects explicitly. Required or critical objects cannot
be excluded, and every other exclusion needs current hashed evidence, a specific
reason, and a closed non-contributing disposition with no claim contribution.

Counts, object-name lists, catalog expansion, whole-receipt hashes, and ordinal
ranges are not per-obligation evidence. Every satisfied closure obligation must
retain its exact target-native semantic object, `evidence_ref`, and lowercase
content hash; missing, renamed, overlapping, mechanically generated, or
summary-only mappings block broad audit closure.



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

Family capability baseline purpose: Prevent an engineering audit from being declared complete while required native checks, current evidence, blockers, predictive conditions, or the bounded claim scope remain unresolved.

Family route bounded claim: Closure proves only the exact requested audit scope represented by current native receipts; skipped, stale, partial, and predictive gaps remain non-pass.

Family baseline proof boundary: This guard-model proof blocks only candidate admission when declared target-native obligation evidence is missing or native-failed. It does not independently detect the underlying physical, mapping, topology, workflow, or evidence defect and does not certify upstream truth.

The bundled `guard-model/` files declare these maintained family baseline regression classes:

- `Candidate is not proven against required native check is missing` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the closure plan omits or lacks a current required PhysicsGuard check. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against stale or skipped evidence is promoted` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: stale, skipped, not-run, or foreign evidence is treated as passed. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against unresolved blocker is suppressed` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: a current native blocker or missing-input condition is absent from closure. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against predictive readiness is overclaimed` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: pointwise or non-predictive evidence is used for a predictive closure request. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against closure scope is overreached` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the final statement exceeds the exact checked evidence and assumptions. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.

These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.

For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.

Use `guard-model/verify.py check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.

`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.

`guard-model/verify.py` is the PhysicsGuard-native verifier. It proves only the declared family baseline and never replaces current task evidence or PhysicsGuard domain judgment.
<!-- END MANAGED PURPOSE AND BLOCKABILITY -->
