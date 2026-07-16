---
name: physicsguard-model-library
description: Use when indexing reusable PhysicsGuard model assets, validation reports, compatible testbench profiles, known limits, and reuse status without storing raw datasets or overclaiming model validity.
---

# PhysicsGuard Model Library

Use this route after model-dataset validation reports exist. The model library
is an evidence index, not a raw-data database and not proof of universal model
validity.

For cross-project discovery, historical search, or "which projects/models have
we tested before" questions, do not answer from one model library index alone.
Model libraries can provide provider evidence to an external database ledger,
but this PhysicsGuard route does not own database indexes, lifecycle, query, or
freshness gates.

## Workflow

1. Create or update a model library index:

   ```yaml
   library_id: example_model_library
   entries:
     - model_id: pump_loop_low_fidelity_v1
       model_file: path/to/hierarchy.yaml
       evidence_registry: path/to/project_evidence_registry.yaml
       model_context: pump_loop_model_context
       evidence_bundle_id: pump_loop_validation_bundle
       validation_reports:
         - reports/example_validation.yaml
       reuse_status: partial
   ```

2. Check the index:

   ```powershell
   python -m physicsguard.cli model-library check MODEL_LIBRARY.yaml --pretty
   ```

3. Treat missing model files, stale hashes, missing validation reports, or
   invalid report references as blocking for broad reuse claims.
   A `validated` reuse claim additionally requires a current passing native
   validation-depth receipt with exact dataset/mapping/time/scenario/split and
   report identity, compatible `covered_scope`, and a passing quantitative
   adequacy receipt over the artifact-derived universe. A scalar-only,
   snapshot, shallow, scope-incompatible, or partial receipt supports at most
   partial, explicitly bounded reuse.
   The receipt must classify every available parameter and show passing
   per-parameter dynamic floors, strata, row-gap, and executable model-
   contribution depth for each time-varying parameter; one static-looking
   value or a disconnected observation cannot silently stand in for a time
   history.
4. When evidence registry and bundle references exist, run or trust the
   `model-library check` gap gate. Blocking project evidence gaps prevent
   validated reuse; review gaps must remain visible.
5. For `validated` reuse or broad reuse-readiness claims, include the model
   library in a project closure plan and run:

   ```powershell
   python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
   ```

   The closure report must be passed before broad reuse claims. Partial or
   downgraded closure means only limited reuse wording is safe.
6. Record predictive capability only when the entry references a current
   `stateful_dynamic` future-rollout receipt with disjoint training/holdout,
   passing metrics and stability, and an explicit checked horizon. Pointwise
   validation or reuse evidence must never be relabeled predictive.

## Safe Claim Boundary

The library can say where a model has validation evidence and known limits. It
must not store large raw data, invent fit, hide project evidence gaps,
or imply validity outside the referenced validation reports, adequacy universe,
prediction horizon, and evidence bundle.

## Native skill-execution depth receipt gate

Before claiming an asset is reusable, issue
`python -m physicsguard.skill_execution_depth PACKAGE.json --output RECEIPT.json`
for target `physicsguard-model-library`, owner `physicsguard.model-library`, and
route `route:physicsguard-model-library:reuse`. Reconcile the complete selected
asset/profile/testbench universe and provide current evidence for compatibility,
the gap gate, validation receipt, and bounded reuse scope for every eligible
item. Catalog presence or a name match is not compatibility evidence. SkillGuard
may enforce the receipt binding but does not select or validate the model asset.
Declare critical assets and profiles explicitly. Required or critical items
cannot be excluded; any other exclusion needs current hashed evidence and a
closed non-contributing disposition that supplies no reuse evidence.

Counts, asset-name lists, catalog expansion, whole-receipt hashes, and ordinal
ranges are not per-obligation evidence. Every satisfied compatibility or reuse
obligation must retain its exact target-native semantic object, `evidence_ref`,
and lowercase content hash; missing, renamed, overlapping, mechanically generated,
or summary-only mappings block a reuse claim.

<!-- BEGIN SKILLGUARD CONTRACT LAYER -->
## Generic SkillGuard supervision

SkillGuard supervises only the checks declared by `physicsguard-model-library`. It freezes the exact check inventory, one execution owner per check, dependency order, governed inputs, immutable terminal receipts, installation projection, and closure. PhysicsGuard remains the sole owner of the physical/evidence purpose, prevented failure classes, native oracles, good/bad proofs, pass/block decisions, residual risk, and bounded claim.

Every declared check is mandatory unless the target contract itself removes it in a new reviewed contract. There is no selectable supervision mode, reduced-depth path, alternate authority, compatibility reader, or generic SkillGuard semantic decision. Reuse is allowed only for a current immutable receipt with the same execution identity and governed inputs. Receipt consumers verify and project; they do not rerun an owner or use `--resume` as a read-only audit. A final full gate runs once after source and tool identities freeze, never through a scheduled task or unattended retry. After timeout or interruption, evidence is invalid until the entire descendant process tree is confirmed stopped.

The only SkillGuard runtime authority is `.skillguard/contract-source.json`, `.skillguard/compiled-contract.json`, and `.skillguard/check-manifest.json`. The bundled PhysicsGuard `guard-model/` assets are family baseline regression inputs. Current model-purpose artifacts remain target-local PhysicsGuard authority and are not duplicated or semantically interpreted in SkillGuard.
The source contract uses one fixed `native-integrated` identity for the declared family baseline checks. Every declared binding is required before that baseline closure, but a baseline receipt cannot be projected as current-model proof. A real task may declare its own PhysicsGuard-native current-purpose checks for SkillGuard supervision; SkillGuard still cannot invent their semantics. Parallel success routes and SkillGuard-owned domain routes are forbidden.
<!-- END SKILLGUARD CONTRACT LAYER -->

<!-- BEGIN MANAGED PURPOSE AND BLOCKABILITY -->
## PhysicsGuard dynamic model-purpose and family baseline

Family capability baseline purpose: Prevent reuse of a PhysicsGuard model asset unless its profile, testbench, compatibility evidence, gaps, validation receipt, and bounded reuse scope are current for the requested project.

Family route bounded claim: Library readiness licenses only the selected asset/profile/testbench combination and exact bounded reuse scope; it does not validate a new project automatically.

Family baseline proof boundary: This guard-model proof blocks only candidate admission when declared target-native obligation evidence is missing or native-failed. It does not independently detect the underlying physical, mapping, topology, workflow, or evidence defect and does not certify upstream truth.

The bundled `guard-model/` files declare these maintained family baseline regression classes:

- `Candidate is not proven against library inventory is incomplete` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: selected assets, profiles, or testbenches are absent from the current inventory. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against compatibility is not proven` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the selected asset and target testbench/model interfaces are incompatible or unevaluated. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against validation or gap evidence is stale` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the validation receipt is stale, missing, or unresolved gaps are hidden. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against reuse scope is overreached` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the requested reuse exceeds the validated compatibility boundary. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.

These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.

For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.

Use `guard-model/verify.py check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.

`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.

`guard-model/verify.py` is the PhysicsGuard-native verifier. SkillGuard remains generic: it only supervises checks declared by a skill or task, owners, dependency order, current immutable receipts, installation projection, and closure; it never chooses what a model prevents.
<!-- END MANAGED PURPOSE AND BLOCKABILITY -->
