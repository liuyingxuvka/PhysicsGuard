# Test File Contracts

PhysicsGuard test-file contracts are an optional route for projects that include
concrete testbench data files. They are not required for ordinary model-only
PhysicsGuard work.

The goal is simple: when a file contains hundreds or thousands of fields, the AI
must not silently miss a field or invent a binding. A script extracts file facts,
and a file-specific contract records how every field is classified, disposed,
and mapped to the PhysicsGuard model or explicitly left for review/model
extension.

## File-Level Flow

```text
test data file
  -> extractor script
  -> DataFileManifest
  -> TestFileContract
  -> parameter coverage check
  -> model binding check
  -> pass / partial / fail
  -> hierarchy evaluate only inside the safe claim boundary
```

## Required Artifacts

- `DataFileManifest`: file path, hash, size, format, fields, row/sample counts,
  time range, frequency, continuity, field types, units, and extractor evidence.
- `TestBenchProfile`: bench id/version, expected fields, units, time column, and
  aliases.
- `ExtractorProfile`: extraction script identity, script hash, config hash, and
  format expectations.
- `ModelBinding`: hierarchy/model file, hash, compatible profiles, expected
  variables and parameters, and stale rules.
- `ParameterCatalog`: one stable source id for every manifest field.
- `RoleMatrix`: each field's testbench role, physical role, model role, owner
  block, verification role, and coverage status.
- `MappingEdges`: evidence-backed links from source fields to model variables,
  parameters, blocks, residuals, metadata, or derived quantities.
- `CoveragePolicy`: fail-closed rules for missing fields, review-required
  mappings, stale evidence, duplicate mappings, and missing evidence.

## Commands

Generate a manifest:

```powershell
python -m physicsguard.cli testfile manifest DATA.csv --profile PROFILE.yaml --out MANIFEST.yaml
```

Inspect a contract:

```powershell
python -m physicsguard.cli testfile inspect CONTRACT.yaml --pretty
```

Check one contract:

```powershell
python -m physicsguard.cli testfile contract-check CONTRACT.yaml --pretty
```

Check coverage only:

```powershell
python -m physicsguard.cli coverage check CONTRACT.yaml --pretty
```

Check a project index:

```powershell
python -m physicsguard.cli testfile project-check INDEX.yaml --pretty
```

Compare two file contracts:

```powershell
python -m physicsguard.cli testfile diff OLD_CONTRACT.yaml NEW_CONTRACT.yaml --pretty
```

## Mapping Evidence Rule

Every mapping edge should explain why the binding exists. Valid evidence can
include:

- parameter or field name match;
- label match;
- unit agreement;
- P&ID or physical topology;
- testbench structure;
- code reference;
- datasheet;
- derived formula;
- direct human-provided evidence.

If the AI does not know the field meaning, the target, or the physical relation,
the mapping must stay `review_required`, `planned_child_model`, or fail the
contract. The AI must not mark it `covered` without evidence.

## Model Gaps

Sometimes a test file contains a real field that the current PhysicsGuard model
does not yet cover. That is not a reason to invent a target. Record the gap and
choose one of these actions:

- add a low-fidelity child model when the relation is explicit and authorized;
- ask the user for mapping evidence;
- mark the field as planned child-model work;
- exclude it only with a clear reason and safe claim boundary.

## Claim Boundary

- `pass`: scoped AI analysis may proceed inside the contract's file/model
  boundary.
- `partial`: only limited claims are safe. Review-required mappings, planned
  model gaps, known defects, or stale evidence must be named.
- `fail`: broad analysis is blocked until missing catalog rows, roles,
  evidence, mappings, hashes, or model bindings are fixed.

A passing contract does not prove the physical model is correct. It only proves
that the file fields were accounted for and bound or disposed under explicit
rules. Residual audits, FlowGuard checks, pytest, and closure evidence still
govern physical debugging claims.
