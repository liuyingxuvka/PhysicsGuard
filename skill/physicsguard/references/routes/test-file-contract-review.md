# PhysicsGuard Test File Contract Review

## Entry boundary

Accept this route only when:

- One or more concrete testbench, test-data, log, sensor, command, measurement, calibration, or fixture files are in scope.
- File and field contracts must pass before broad AI analysis or dataset validation.

Reject or hand off when:

- No concrete test-data file is in scope. Handoff: the `ai-debugging` route.
- Current file contracts pass and model/dataset consistency is now the request. Handoff: the `model-dataset-validation` route.

## Minimum workflow

1. Generate deterministic file and field identity before AI mapping judgment.
2. Following the route protocol below, reconcile every field, role, unit, timing, mapping, and model binding.
3. Block broad analysis until the exact contract passes; hand validation to the dataset route afterward.

## Required outputs

- `contract_status`
- `field_dispositions`
- `mapping_gaps`
- `safe_analysis_boundary`

Claim boundary: A pass covers only the exact test files, fields, units, timing, model/testbench versions, signal mappings, and depth represented in the command output.

## Route protocol

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
- The manifest records content hashes of the data file, extraction script and
  configuration; a later content change makes the contract `manifest_stale`
  even if filenames remain unchanged.
- Treat the current manifest row count and field catalog as the available
  point/signal universe for downstream adequacy. Preserve row identities,
  timestamps, operating-mode/event/peak/boundary evidence, and parameter roles;
  do not let a validation plan redefine the universe as only its chosen rows or
  signals.
- Preserve enough evidence to classify every model parameter as static or
  time-varying. Time-varying parameters require their own field/series mapping;
  one catalog or binding row cannot establish temporal depth.

## Workflow

1. Confirm this is a test-data workflow. If there is no concrete test data file,
   return to the normal `ai-debugging` route.
2. Generate or refresh the manifest:

   `--out` stores the source path relative to the manifest directory (absolute across drives when necessary); stdout mode keeps the supplied path. Preserve the generated source hash and size.

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
   python -m physicsguard.cli testfile contract-check CONTRACT.yaml
   ```

7. Run the coverage-only check only when step 6 was not run; step 6 already includes it:

   ```powershell
   python -m physicsguard.cli coverage check CONTRACT.yaml
   ```

8. When several files are in scope, run this once instead of step 6 for each file; it checks every listed contract:

   ```powershell
   python -m physicsguard.cli testfile project-check INDEX.yaml
   ```

9. When testbench files change, compare contracts:

   ```powershell
   python -m physicsguard.cli testfile diff OLD_CONTRACT.yaml NEW_CONTRACT.yaml
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
