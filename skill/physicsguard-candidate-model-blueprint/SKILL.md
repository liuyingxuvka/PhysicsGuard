---
name: physicsguard-candidate-model-blueprint
description: Use when turning a validated PhysicsGuard hierarchy into a candidate model blueprint for MATLAB/Simulink or another official target-model interface without claiming recovered commercial-model equivalence.
---

# PhysicsGuard Candidate Model Blueprint

Use this route when the user asks to build a candidate model from PhysicsGuard evidence.

## Workflow

1. Start from a passed model-understanding preflight.
2. Use validated low-fidelity hierarchy blocks, interfaces, units, assumptions, and examples.
3. Generate candidate model artifacts only through official APIs, documented exchange formats, or user-owned editable templates.
4. Run the candidate model and map outputs back into PhysicsGuard observed values.
5. Use residuals, quantitative adequacy, and closure to decide whether the
   blueprint is good enough or needs refinement. Do not validate only a small
   convenient subset when the claim covers a larger time/signal/parameter
   universe. Source-classify every parameter as static or time-varying, and
   require each time-varying parameter's own adequate history.
6. Declare whether the candidate is `pointwise` or `stateful_dynamic`.
   Pointwise relations cannot support simulation or prediction claims. For a
   stateful predictive claim, execute the candidate through the official
   target interface, preserve the initial state, step size, horizon, producer
   receipt, and exact trajectory identity, and validate it against a disjoint
   future holdout with the native predictive-rollout gate.
7. Keep the base task model and candidate model as separate content-addressed
   artifacts. Record the triggering hypothesis mismatch and the exact
   regression and holdout inventory. A stateful candidate additionally
   consumes the existing native predictive-rollout receipt:

   ```powershell
   python -m physicsguard.cli task-model revision CANDIDATE_REVISION.yaml --pretty
   ```

8. Accept the candidate only when every declared check passes. Reject an
   unapplied failed candidate. If an applied candidate fails, roll back only to
   the exact still-current base identity. Never overwrite or delete v1 during
   candidate evaluation.

A candidate model is a new engineering artifact, not a recovered commercial-model copy.
Even a passing predictive rollout is bounded to its checked horizon, signals,
thresholds, initial state, and future-holdout cases.
This loop revises only the current task model. It does not modify PhysicsGuard,
its default thresholds, its reusable model library, or an installed skill.

## Native skill-execution depth receipt gate

Before declaring a candidate blueprint ready, issue
`python runtime/skill_execution_depth.py PACKAGE.json --output RECEIPT.json`
for target `physicsguard-candidate-model-blueprint`, owner
`physicsguard.candidate-model-blueprint`, and route
`route:physicsguard-candidate-model-blueprint:build`. The package must account
for every eligible validated block and interface and bind validated hierarchy,
block readiness, signal/parameter mappings, interface inventory, rollout
boundary, and generation eligibility. A blueprint assembled from a sampled
subset or from unchecked library metadata remains partial. The target-owned
receipt records the decision without delegating physical-model selection.
The package must preserve an explicit critical-object denominator. Required or
critical blocks and interfaces cannot be excluded; all other exclusions need
current hashed evidence and a closed non-contributing disposition.

Counts, block-name lists, catalog expansion, whole-receipt hashes, and ordinal
ranges are not per-obligation evidence. Every satisfied blueprint obligation
must retain its exact target-native semantic object, `evidence_ref`, and
lowercase content hash; missing, renamed, overlapping, mechanically generated,
or summary-only mappings block blueprint readiness.



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

Family capability baseline purpose: Prevent generation of a candidate simulation blueprint until the hierarchy, block readiness, interfaces, signal/parameter mappings, and rollout boundary are validated for the requested bounded use.

Family route bounded claim: Generation eligibility covers only a candidate low-fidelity blueprint for the declared target and interfaces; it is not an implemented or validated high-fidelity model.

Family baseline proof boundary: This guard-model proof blocks only candidate admission when declared target-native obligation evidence is missing or native-failed. It does not independently detect the underlying physical, mapping, topology, workflow, or evidence defect and does not certify upstream truth.

The bundled `guard-model/` files declare these maintained family baseline regression classes:

- `Candidate is not proven against hierarchy or blocks are not ready` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the required hierarchy, component blocks, or physical interfaces are missing or unvalidated. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against interface or mapping inventory is incomplete` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: required signal, parameter, unit, or interface bindings are missing. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against rollout boundary is unclear` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the intended pointwise or stateful semantics and rollout limits are not explicit. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against generation proceeds despite a blocker` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: generation eligibility is asserted while a required readiness condition is blocked. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.

These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.

For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.

Use `guard-model/verify.py check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.

`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.

`guard-model/verify.py` is the PhysicsGuard-native verifier. It proves only the declared family baseline and never replaces current task evidence or PhysicsGuard domain judgment.
<!-- END MANAGED PURPOSE AND BLOCKABILITY -->
