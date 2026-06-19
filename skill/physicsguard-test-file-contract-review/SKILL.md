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
11. If project-level evidence is in scope, run:

    ```powershell
    python -m physicsguard.cli evidence gap-check EVIDENCE.yaml --pretty
    python -m physicsguard.cli evidence map EVIDENCE.yaml --pretty
    ```

    Resolve or report missing project profile, file registration, test-field
    binding, physical-parameter binding, and binding-exemption gaps.
12. If the project is listed in a database catalog or DataBank ledger, refresh
    or flag the ledger through `databank-workflow` after test-file contract
    changes so cross-project searches see current field coverage, binding
    state, freshness, closure status, and AI handoff files.
13. For final analysis-readiness or validation-readiness claims, include the
    passing contract in project closure. A passing file contract is coverage
    evidence only; project closure checks whether the whole project is ready:

    ```powershell
    python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
    ```

## Safe Claim Boundary

- `pass`: scoped AI analysis may proceed inside the contract's model binding and
  known test-file boundary.
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
