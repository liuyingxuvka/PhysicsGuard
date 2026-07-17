---
name: physicsguard-project-adoption
description: Use when adopting, auditing, upgrading, or checking a target repository's PhysicsGuard workflow records before AI-guided physical simulation debugging.
---

# PhysicsGuard Project Adoption

Use this route before non-trivial PhysicsGuard debugging or model-building work in a repository.

## Workflow

1. Run a read-only audit first:

   ```powershell
   python -m physicsguard.cli project audit --pretty
   ```

2. If the project is not adopted and the user authorized repository setup, run:

   ```powershell
   python -m physicsguard.cli project adopt --pretty
   ```

3. If the installed package version is newer than the record, run:

   ```powershell
   python -m physicsguard.cli project upgrade --pretty
   ```

4. Treat project adoption as workflow evidence only. It does not prove residual behavior, physical correctness, or localization.
   Also distinguish repository source capability from the active installed
   runtime: do not claim adequacy or predictive gates are available on the
   machine until the invoked CLI exposes and executes them. Upgrade through
   the repository's declared adoption route when authorized; do not replace it
   with copied prompt text or a temporary checker.
5. If the project contains test data, source documents, reusable model assets,
   or multi-file evidence, also route through
   `physicsguard-project-evidence-registry` so the AI can inspect the project
   profile, file map, binding expectations, evidence bundles, and open gaps.
6. If the user asks for multi-project history, reusable model discovery,
   database-level maps, or cross-project comparison, do not answer from project
   adoption alone. Project adoption only says the current repository has a
   workflow record; it does not index or maintain a surrounding database.
7. If the user asks whether the project is ready, complete, validated,
   reusable, or safe for handoff, run or inspect project closure:

   ```powershell
   python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
   ```

   Adoption pass only says the workflow record exists; it is not project
   readiness.
8. For non-snapshot validation, require current repository artifacts and the
   native quantitative adequacy receipt. For prediction readiness, require the
   stateful future-rollout route and its native receipt. An older adoption
   record, a generated template, or SkillGuard contract text cannot substitute
   for those runtime checks.

## Claim Boundary

Safe claim: the project has a discoverable PhysicsGuard workflow record.

Unsafe claim: the model is physically correct, the fault is localized, or a commercial model has been reconstructed.

## Native skill-execution depth receipt gate

Before claiming project adoption is current, issue
`python -m physicsguard.skill_execution_depth PACKAGE.json --output RECEIPT.json`
for target `physicsguard-project-adoption`, owner
`physicsguard.project-adoption`, and route
`route:physicsguard-project-adoption:audit`. Bind the current project record,
supported toolchain, complete native artifact inventory, blockers, and required
revalidation. Discovery alone is not adoption, and a fixture cannot close a
scheduled production project. SkillGuard consumes the exact current native
receipt without becoming the PhysicsGuard project auditor.
The project package must declare critical adoption objects explicitly. Required
or critical artifacts cannot be excluded; another exclusion needs current hashed
evidence and a closed non-contributing disposition with no adoption contribution.

Counts, artifact-name lists, catalog expansion, whole-receipt hashes, and ordinal
ranges are not per-obligation evidence. Every satisfied adoption and required-
revalidation obligation must retain its exact target-native semantic object,
`evidence_ref`, and lowercase content hash; missing, renamed, overlapping,
mechanically generated, or summary-only mappings block current adoption.

<!-- BEGIN SKILLGUARD CONTRACT LAYER -->
## Generic SkillGuard supervision

SkillGuard supervises only the checks declared by `physicsguard-project-adoption`. It freezes the exact check inventory, one execution owner per check, dependency order, governed inputs, immutable terminal receipts, installation projection, and closure. PhysicsGuard remains the sole owner of the physical/evidence purpose, prevented failure classes, native oracles, good/bad proofs, pass/block decisions, residual risk, and bounded claim.

Every declared check is mandatory unless the target contract itself removes it in a new reviewed contract. There is no selectable supervision mode, reduced-depth path, alternate authority, compatibility reader, or generic SkillGuard semantic decision. Reuse is allowed only for a current immutable receipt with the same execution identity and governed inputs. Receipt consumers verify and project; they do not rerun an owner or use `--resume` as a read-only audit. A final full gate runs once after source and tool identities freeze, never through a scheduled task or unattended retry. After timeout or interruption, evidence is invalid until the entire descendant process tree is confirmed stopped.

The only SkillGuard runtime authority is `.skillguard/contract-source.json`, `.skillguard/compiled-contract.json`, and `.skillguard/check-manifest.json`. The bundled PhysicsGuard `guard-model/` assets are family baseline regression inputs. Current model-purpose artifacts remain target-local PhysicsGuard authority and are not duplicated or semantically interpreted in SkillGuard.
The source contract uses one fixed `native-integrated` identity for the declared family baseline checks. Every declared binding is required before that baseline closure, but a baseline receipt cannot be projected as current-model proof. A real task may declare its own PhysicsGuard-native current-purpose checks for SkillGuard supervision; SkillGuard still cannot invent their semantics. Parallel success routes and SkillGuard-owned domain routes are forbidden.
<!-- END SKILLGUARD CONTRACT LAYER -->


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

Family capability baseline purpose: Prevent a repository from claiming PhysicsGuard adoption when project records, supported toolchain identity, native artifact inventory, blockers, or required revalidation are absent or stale.

Family route bounded claim: Adoption proves only current workflow records and toolchain/artifact readiness; it never substitutes for model execution, validation, closure, installation, or release evidence.

Family baseline proof boundary: This guard-model proof blocks only candidate admission when declared target-native obligation evidence is missing or native-failed. It does not independently detect the underlying physical, mapping, topology, workflow, or evidence defect and does not certify upstream truth.

The bundled `guard-model/` files declare these maintained family baseline regression classes:

- `Candidate is not proven against adoption record is stale` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: project adoption records do not match the current repository or toolchain. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against toolchain is unsupported` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the real PhysicsGuard/FlowGuard toolchain is missing or incompatible. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against native artifact inventory is incomplete` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: required project models, plans, registries, or receipts are missing. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against blocker or revalidation is omitted` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: known blockers or required affected checks are not preserved. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.

These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.

For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.

Use `guard-model/verify.py check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.

`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.

`guard-model/verify.py` is the PhysicsGuard-native verifier. SkillGuard remains generic: it only supervises checks declared by a skill or task, owners, dependency order, current immutable receipts, installation projection, and closure; it never chooses what a model prevents.
<!-- END MANAGED PURPOSE AND BLOCKABILITY -->
