---
name: physicsguard-test-file-contract-review
description: Use when a PhysicsGuard project includes concrete testbench/test-data files whose fields, units, timing, testbench version, parameter roles, mapping evidence, and model binding coverage must be checked before AI analysis claims.
---

# PhysicsGuard Test File Contract Review

Use this route only when concrete test data files are in scope: CSV/TSV exports,
database extracts already materialized as files, testbench logs, sensor tables,
command/measurement files, calibration snapshots, or project fixtures that stand
for those files. Do not require it for ordinary model-only PhysicsGuard work.

## Hard Rules

- One concrete test data file needs one resolved `TestFileContract`.
- Field counts, names, row counts, time range, frequency, hashes, and extractor
  identity must come from scripts, not AI narration.
- Every manifest field must appear in the parameter catalog.
- Every catalog entry must have a role/disposition row.
- AI mappings must carry evidence: field name, label, unit, P&ID/topology,
  testbench structure, code reference, datasheet, formula, or human-provided
  evidence.
- If the AI does not know what a field means or how to bind it, mark it
  `review_required`, `planned_child_model`, or leave the contract failing. Do
  not silently mark it `covered`.
- If the file contains a field that the current model cannot represent, record a
  model gap and request a child model/model extension or human evidence.
- A passing contract is coverage evidence only; it does not prove physical
  correctness and does not mutate observed values.
- Before the contract feeds a broad validation-depth claim, preserve exact
  hashes for the concrete data, manifest/field schema, testbench profile and
  version, and parameter-role matrix. Any later content change makes the depth
  receipt stale even if filenames remain unchanged.
- Treat the current manifest row count and field catalog as the available
  point/signal universe for downstream adequacy. Preserve row identities,
  timestamps, operating-mode/event/peak/boundary evidence, and parameter roles;
  do not let a validation plan redefine the universe as only its chosen rows or
  signals.
- Preserve enough evidence to classify every model parameter as static or
  time-varying. Time-varying parameters require their own field/series mapping;
  one catalog or binding row cannot establish temporal depth.
- If a project evidence registry exists, the contract should declare
  `project_evidence_registry` and `registered_artifact_id` so the file contract
  appears in the project map. Covered fields should also have project-level
  binding summaries or explicit binding exemptions in
  `physicsguard-project-evidence-registry`.

## Workflow

1. Confirm this is a test-data workflow. If there is no concrete test data file,
   return to the normal `physicsguard-ai-debugging` route.
2. Generate or refresh the manifest:

   ```powershell
   python -m physicsguard.cli testfile manifest DATA.csv --profile PROFILE.yaml --out MANIFEST.yaml
   ```

3. Create or resolve the file-specific contract using these artifacts:
   manifest, testbench profile, extractor profile, model binding, parameter
   catalog, role matrix, mapping edges, and coverage policy.
4. For each source field, classify its testbench role, physical role, model
   role, owner block, verification role, and coverage status.
5. For each mapping edge, record evidence. Acceptable evidence includes label or
   parameter names, unit agreement, testbench topology, P&ID/topology, code
   references, formulas, datasheets, or human-provided mapping records.
6. Run the contract check:

   ```powershell
   python -m physicsguard.cli testfile contract-check CONTRACT.yaml --pretty
   ```

7. Run coverage-only checks when debugging field coverage:

   ```powershell
   python -m physicsguard.cli coverage check CONTRACT.yaml --pretty
   ```

8. Run project-level checks when multiple files are in scope:

   ```powershell
   python -m physicsguard.cli testfile project-check INDEX.yaml --pretty
   ```

9. When testbench files change, compare contracts:

   ```powershell
   python -m physicsguard.cli testfile diff OLD_CONTRACT.yaml NEW_CONTRACT.yaml --pretty
   ```

10. Do not claim broad AI analysis readiness until contract status is `pass`.
    For `partial` or `fail`, continue filling evidence, ask the user for
    unknown mappings, or extend the PhysicsGuard model under the normal low-
    fidelity module rules.
    Contract pass is necessary but not sufficient for non-snapshot validation:
    hand off the current manifest and roles to the native adequacy gate, which
    checks quantitative selection ratio, temporal spread and gaps, per-signal
    depth, critical/family coverage, and exclusions under a declared sampling
    policy.
11. If project-level evidence is in scope, run:

    ```powershell
    python -m physicsguard.cli evidence gap-check EVIDENCE.yaml --pretty
    python -m physicsguard.cli evidence map EVIDENCE.yaml --pretty
    ```

    Resolve or report missing project profile, file registration, test-field
    binding, physical-parameter binding, and binding-exemption gaps.
12. If the project is listed in an external database ledger, report the current
    field coverage, binding state, and contract gaps as provider evidence only.
    Do not update the ledger from this PhysicsGuard skill.
13. For final analysis-readiness or validation-readiness claims, include the
    passing contract in project closure. A passing file contract is coverage
    evidence only; project closure checks whether the whole project is ready:

    ```powershell
    python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
    ```

## Safe Claim Boundary

- `pass`: scoped AI analysis may proceed inside the contract's model binding and
  known test-file boundary; temporal, predictive, or general model claims still
  require the separate adequacy and, when applicable, stateful rollout gates.
- `partial`: only limited claims are safe; list review-required mappings,
  planned child models, known defects, or stale evidence.
- `fail`: broad analysis is blocked. Fix missing manifest facts, catalog rows,
  role/disposition gaps, mapping evidence, model targets, stale hashes, or model
  binding errors first.

## Recommended Visual

For non-trivial test-file work, show a compact table or Mermaid map that connects:

```text
test file field -> catalog id -> role/disposition -> evidence -> model target
```

The visual explains coverage; the machine-readable contract check is the
validation evidence.

## Native skill-execution depth receipt gate

Before claiming test-file contract coverage, issue
`python -m physicsguard.skill_execution_depth PACKAGE.json --output RECEIPT.json`
for target `physicsguard-test-file-contract-review`, owner
`physicsguard.test-file-contract-review`, and route
`route:physicsguard-test-file-contract-review:check`. The package must account
for every selected file and field and bind units, timing, testbench/model
relationships, per-signal depth, mapping evidence, and project gaps. Every
eligible field receives a current per-object result; every time-varying field
uses its own full point universe, dynamic floor, distributed strata, and gap
gate. A passing schema check or sampled columns alone remains coverage-only.
Declare critical files and fields explicitly. Required or critical objects
cannot be excluded; any other exclusion needs current hashed evidence and a
closed non-contributing disposition with no contract-coverage contribution.

Counts, file/field-name lists, catalog expansion, whole-receipt hashes, and
ordinal time ranges are not per-obligation evidence. Every satisfied file,
field, mapping, timing, and temporal-depth obligation must retain its exact
target-native semantic object, `evidence_ref`, and lowercase content hash;
missing, renamed, overlapping, mechanically generated, or summary-only mappings
block a complete test-file contract claim.

<!-- BEGIN SKILLGUARD CONTRACT LAYER -->
## Generic SkillGuard supervision

SkillGuard supervises only the checks declared by `physicsguard-test-file-contract-review`. It freezes the exact check inventory, one execution owner per check, dependency order, governed inputs, immutable terminal receipts, installation projection, and closure. PhysicsGuard remains the sole owner of the physical/evidence purpose, prevented failure classes, native oracles, good/bad proofs, pass/block decisions, residual risk, and bounded claim.

Every declared check is mandatory unless the target contract itself removes it in a new reviewed contract. There is no selectable supervision mode, reduced-depth path, alternate authority, compatibility reader, or generic SkillGuard semantic decision. Reuse is allowed only for a current immutable receipt with the same execution identity and governed inputs. Receipt consumers verify and project; they do not rerun an owner or use `--resume` as a read-only audit. A final full gate runs once after source and tool identities freeze, never through a scheduled task or unattended retry. After timeout or interruption, evidence is invalid until the entire descendant process tree is confirmed stopped.

The only SkillGuard runtime authority is `.skillguard/contract-source.json`, `.skillguard/compiled-contract.json`, and `.skillguard/check-manifest.json`. The bundled PhysicsGuard `guard-model/` assets are family baseline regression inputs. Current model-purpose artifacts remain target-local PhysicsGuard authority and are not duplicated or semantically interpreted in SkillGuard.
The source contract uses one fixed `native-integrated` identity for the declared family baseline checks. Every declared binding is required before that baseline closure, but a baseline receipt cannot be projected as current-model proof. A real task may declare its own PhysicsGuard-native current-purpose checks for SkillGuard supervision; SkillGuard still cannot invent their semantics. Parallel success routes and SkillGuard-owned domain routes are forbidden.
<!-- END SKILLGUARD CONTRACT LAYER -->

<!-- BEGIN MANAGED PURPOSE AND BLOCKABILITY -->
## PhysicsGuard dynamic model-purpose and family baseline

Family capability baseline purpose: Prevent a test file from authorizing validation unless file/field identities, units, timing, testbench/model bindings, per-signal depth, mappings, and project gaps are complete and current.

Family route bounded claim: A pass covers only the exact test files, fields, units, timing, model/testbench versions, signal mappings, and depth represented in the receipt.

Family baseline proof boundary: This guard-model proof blocks only candidate admission when declared target-native obligation evidence is missing or native-failed. It does not independently detect the underlying physical, mapping, topology, workflow, or evidence defect and does not certify upstream truth.

The bundled `guard-model/` files declare these maintained family baseline regression classes:

- `Candidate is not proven against file or field identity is missing` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: a governed test file or required field is absent, stale, duplicated, or misidentified. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against unit or timing contract mismatches` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: field units, timestamps, step, duration, or temporal semantics are inconsistent. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against testbench or model binding is wrong` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the file is bound to the wrong testbench, model, version, or interface. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against per-signal evidence is shallow` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: required signal depth or mapping evidence is missing or inadequate. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against project-level gap is hidden` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: a current project evidence gap is omitted from the contract result. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.

These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.

For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.

Use `guard-model/verify.py check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.

`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.

`guard-model/verify.py` is the PhysicsGuard-native verifier. SkillGuard remains generic: it only supervises checks declared by a skill or task, owners, dependency order, current immutable receipts, installation projection, and closure; it never chooses what a model prevents.
<!-- END MANAGED PURPOSE AND BLOCKABILITY -->
