---
name: physicsguard-project-evidence-registry
description: Use when a PhysicsGuard project needs a project-level evidence registry, project profile, file map, binding expectations, evidence bundles, project evidence map, or gap scan across test files, physical parameters, model contexts, validation plans, and model-library reuse.
---

# PhysicsGuard Project Evidence Registry

Use this sibling route to maintain the project-level map. It does not replace
per-file test contracts or model-dataset validation. It tells AI agents where
the evidence is, what is known, what is unknown, which fields and facts bind to
the model, and which gaps still need work.

## Hard Rules

- Large test data stays where it is; register paths or external references
  instead of copying raw data into the project.
- Small source documents may have local copies, but the registry must say so.
- Basic project profile facts are maintenance targets: project name, objective,
  run period, locations, and source references. If unknown, write an explicit
  unknown reason instead of inventing values.
- Every important test field, physical parameter, or model target must have a
  binding record, a binding expectation, or an explicit exemption reason.
- Manufacturer names, serial numbers, timestamps, comments, or unrelated
  metadata may be exempt from model binding only when the exemption reason is
  recorded.
- The Project Evidence Map is an onboarding/navigation artifact. It is not
  validation proof.
- Blocking evidence gaps prevent validation pass or validated reuse claims.
- If this project appears in an external database ledger, keep this route scoped
  to the project's physical evidence registry. Do not update or repair the
  external ledger from this PhysicsGuard skill.

## Workflow

1. Locate or create the project evidence registry, usually:

   ```powershell
   python -m physicsguard.cli evidence check evidence/project_evidence_registry.yaml --pretty
   ```

2. Fill or review `project_profile`: project name, objective, run period,
   locations, known unknowns, and source references.
3. Register important files in `artifacts`: test data, test-file contracts,
   logical datasets, source documents, model files, validation plans/reports,
   bounded `observed_series`, signal-mapping reviews, native
   `validation_depth_receipt` files, and model-library indexes.
4. Register engineering facts in `facts`: physical parameters, equipment or
   vendor identity, configuration facts, software versions, derived values,
   calibrated values, and human overrides.
5. Add `evidence_bindings` for project-level links from test fields or facts to
   model targets. The authoritative detailed mapping remains in the test-file
   contract or source document.
6. Add `binding_expectations` for every field/fact/model target that must be
   checked. Use `must_bind`, `unknown`, or `exempt` with a reason.
7. Add `context_cards` for model/testbench/test-object/dataset scope. Model
   contexts should list model parts and required evidence.
8. Add `evidence_bundles` for validation and model-library handoff.
   For validation depth, include the exact observed-series artifact and every
   binding used by the mapping gate. Units, mapping confidence, active status,
   reviewer state, and bundle membership must be current; the validation plan
   binds the registry by SHA-256.
   Treat the manifest, role matrix, hierarchy, and current bindings as coverage
   authorities: they define available signals/parameters and hierarchy-required
   critical members. Record subsystem/family membership, intentional
   exclusions with specific reasons, and source evidence for required events,
   peaks, boundaries, modes, and adequacy thresholds. A validation plan cannot
   shrink this universe merely by omitting members.
   Record a source-backed static/time-varying classification for every
   available model parameter. Static parameters need current fact/binding
   evidence; time-varying parameters need an exact series mapping so their own
   point/time depth can be checked.
   For predictive work, register the exact stateful model, training inputs,
   producer receipt, generated trajectory, future holdout, and native rollout
   receipt. Preserve path/hash/case disjointness evidence.
9. Run:

   ```powershell
   python -m physicsguard.cli evidence gap-check evidence/project_evidence_registry.yaml --pretty
   python -m physicsguard.cli evidence map evidence/project_evidence_registry.yaml --pretty
   ```

10. Before broad claims, resolve blocking gaps. For review/optional gaps, keep
    them visible in the final claim boundary.
11. For project completion, validation readiness, validated reuse, or
    localization readiness, hand off to project closure:

    ```powershell
    python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
    ```

    The evidence map remains onboarding/navigation only. The closure report is
    the final claim-readiness gate.

## AI Onboarding Map

When another AI enters the project, show or inspect `evidence map` first. It
should answer:

- What project is this, when and where did it run, and which basics are unknown?
- Which files matter, and where are they?
- Which tests exist and what model targets do they cover?
- Which model parts exist and which are tested?
- Which physical parameters are registered and source-backed?
- What is the available coverage universe, which members are critical, and
  which members were explicitly excluded for a project-specific reason?
- Is the model pointwise or stateful, and is there a disjoint future-rollout
  receipt for any predictive claim?
- Which fields or facts are exempt from model binding and why?
- Which blocking/review/optional gaps remain?

## Commands

```powershell
python -m physicsguard.cli evidence check EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence scan PROJECT_OR_FOLDER --registry EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence gap-check EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence bundle-check EVIDENCE.yaml BUNDLE_ID --pretty
python -m physicsguard.cli evidence map EVIDENCE.yaml --pretty
```

For final project claims, follow with:

```powershell
python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
```

If an external database ledger owns this project, this skill can provide current
project evidence, gap reports, closure inputs, validation status, and model
library evidence. It does not update, refresh, audit, or render the external
ledger itself.

## Native skill-execution depth receipt gate

Before claiming project evidence is complete, issue
`python runtime/skill_execution_depth.py PACKAGE.json --output RECEIPT.json`
for target `physicsguard-project-evidence-registry`, owner
`physicsguard.project-evidence-registry`, and route
`route:physicsguard-project-evidence-registry:check`. The package must reconcile
declared, discovered, required, excluded, and evaluated artifacts; verify every
required binding edge and evidence role; preserve critical gaps and bundle
scope; and include one current result per eligible object. Time-bearing signal
or parameter evidence is evaluated against that object's own complete point
universe and distributed dynamic floor. An enumerated catalog cannot be copied
into an evaluated list without native per-object evidence.
The registry package must declare critical objects explicitly. Required or
critical artifacts cannot be excluded; another exclusion needs current hashed
evidence and a closed non-contributing disposition with no bundle contribution.

Counts, object-name lists, catalog expansion, whole-receipt hashes, and ordinal
ranges are not per-obligation evidence. Every satisfied artifact, binding,
evidence-role, and temporal-depth obligation must retain its exact target-native
semantic object, `evidence_ref`, and lowercase content hash; missing, renamed,
overlapping, mechanically generated, or summary-only mappings block complete
project-evidence closure.



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

Family capability baseline purpose: Prevent a project evidence claim from shrinking or misbinding the declared, discovered, required, excluded, role-bound, and critical file universe.

Family route bounded claim: Registry closure covers only the exact current project evidence bundle and declared roles/bindings; unresolved critical gaps or out-of-scope files remain blocking.

Family baseline proof boundary: This guard-model proof blocks only candidate admission when declared target-native obligation evidence is missing or native-failed. It does not independently detect the underlying physical, mapping, topology, workflow, or evidence defect and does not certify upstream truth.

The bundled `guard-model/` files declare these maintained family baseline regression classes:

- `Candidate is not proven against artifact universe is shrunk` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: declared, discovered, required, or excluded files are not completely reconciled. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against binding or role is missing` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: a required evidence-to-model edge or evidence role has no current proof. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against critical evidence gap is hidden` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: a required or critical artifact is missing, stale, or invalidly excluded. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against evidence bundle scope is overreached` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the claimed project scope exceeds the exact bound bundle. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.

These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.

For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.

Use `guard-model/verify.py check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.

`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.

`guard-model/verify.py` is the PhysicsGuard-native verifier. It proves only the declared family baseline and never replaces current task evidence or PhysicsGuard domain judgment.
<!-- END MANAGED PURPOSE AND BLOCKABILITY -->
